"""JSONL protocol-v2 contracts for the Python sidecar boundary."""

from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import subprocess
import sys

import pytest

from keikeu_bridge.protocol import (
    METHOD_CLASSIFICATIONS,
    METHODS,
    MUTATION_METHODS,
    PROTOCOL_VERSION,
    JsonlDispatcher,
    run_jsonl,
)
from keikeu_bridge.service import KeikeuService, ServiceError
from keikeu_core import vault as vault_module


def _service(tmp_path: Path) -> KeikeuService:
    return KeikeuService(
        config_path=tmp_path / "config.json",
        state_path=tmp_path / "state.json",
    )


def _hello(dispatcher: JsonlDispatcher, request_id: int = 1) -> str:
    response = dispatcher.handle(
        {
            "v": PROTOCOL_VERSION,
            "id": request_id,
            "method": "system.hello",
            "params": {},
        }
    )
    assert response["ok"] is True
    assert response["result"]["protocol_version"] == 2  # type: ignore[index]
    assert response["result"]["core_version"] == "paper-v4/index-v4"  # type: ignore[index]
    return response["result"]["session_id"]  # type: ignore[index,return-value]


def _request(
    dispatcher: JsonlDispatcher,
    session_id: str,
    method: str,
    params: dict[str, object],
    *,
    request_id: int = 2,
) -> dict[str, object]:
    return dispatcher.handle(
        {
            "v": PROTOCOL_VERSION,
            "id": request_id,
            "session_id": session_id,
            "method": method,
            "params": params,
        }
    )


def _initialize_vault(
    dispatcher: JsonlDispatcher,
    session_id: str,
    vault: Path,
) -> dict[str, object]:
    preview = _request(
        dispatcher,
        session_id,
        "vault.inspect",
        {"path": str(vault)},
    )
    assert preview["ok"] is True
    opened = _request(
        dispatcher,
        session_id,
        "vault.initialize",
        {"preview_token": preview["result"]["token"]},  # type: ignore[index]
    )
    assert opened["ok"] is True
    return opened["result"]  # type: ignore[return-value]


def test_hello_is_v2_and_v1_fails_closed(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    session_id = _hello(dispatcher, 41)

    stale = dispatcher.handle(
        {"v": 1, "id": 42, "method": "system.hello", "params": {}}
    )
    repeated = dispatcher.handle(
        {
            "v": 2,
            "id": 43,
            "method": "system.hello",
            "params": {},
            "session_id": session_id,
        }
    )

    assert stale["error"]["code"] == "protocol_mismatch"  # type: ignore[index]
    assert repeated["error"]["code"] == "invalid_request"  # type: ignore[index]


def test_non_hello_requires_current_session(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    current = _hello(dispatcher)

    missing = dispatcher.handle(
        {"v": 2, "id": 2, "method": "startup.load", "params": {}}
    )
    stale = _request(dispatcher, current + "-stale", "startup.load", {})

    assert missing["error"]["code"] == "session_expired"  # type: ignore[index]
    assert stale["error"]["code"] == "session_expired"  # type: ignore[index]


def test_new_hello_expires_old_session_and_edit_token(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    vault = tmp_path / "vault"
    dispatcher = JsonlDispatcher(_service(tmp_path))
    first_session = _hello(dispatcher)
    startup = _initialize_vault(dispatcher, first_session, vault)
    draft = _request(dispatcher, first_session, "paper.create_draft", {})
    token = draft["result"]["edit_token"]  # type: ignore[index]
    locator = startup["vault_locator"]

    second_session = _hello(dispatcher, 5)
    old_session = _request(dispatcher, first_session, "startup.load", {})
    old_handle = _request(
        dispatcher,
        second_session,
        "paper.save",
        {
            "edit_token": token,
            "vault_locator": locator,
            "display_name": None,
            "tags": [],
            "pages": [{"name": None, "content": "No", "type": None}],
        },
    )

    assert first_session != second_session
    assert old_session["error"]["code"] == "session_expired"  # type: ignore[index]
    assert old_handle["error"]["code"] == "session_expired"  # type: ignore[index]
    assert list((vault / "cache").glob("*.md")) == []


def test_paper_save_maps_whole_v4_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    vault = tmp_path / "vault"
    dispatcher = JsonlDispatcher(_service(tmp_path))
    session_id = _hello(dispatcher)
    startup = _initialize_vault(dispatcher, session_id, vault)
    draft = _request(dispatcher, session_id, "paper.create_draft", {})

    saved = _request(
        dispatcher,
        session_id,
        "paper.save",
        {
            "edit_token": draft["result"]["edit_token"],  # type: ignore[index]
            "vault_locator": startup["vault_locator"],
            "display_name": "Protocol Paper",
            "tags": ["jsonl"],
            "pages": [
                {"name": "First", "content": "Protocol body", "type": "summary"},
                {"name": None, "content": "Aside", "type": "whisper"},
            ],
        },
    )

    assert saved["ok"] is True
    paper = saved["result"]["paper"]  # type: ignore[index]
    assert [page["type"] for page in paper["pages"]] == ["summary", "whisper"]
    assert paper["vault_locator"] == startup["vault_locator"]
    assert len(list((vault / "cache").glob("*.md"))) == 1


def test_reconcile_shape_is_strict_and_never_accepts_ui_handles(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    session_id = _hello(dispatcher)
    params = {
        "vault_locator": "vault-v1:test",
        "target_path": "cache/K-20260802-001.md",
        "code": "K-20260802-001",
        "created": "2026-08-02T12:00:00",
        "source_digest": None,
        "baseline": None,
        "submitted": {
            "display_name": None,
            "tags": [],
            "pages": [{"name": None, "content": "body", "type": None}],
        },
        "edit_token": "must-not-cross-restart",
    }

    result = _request(dispatcher, session_id, "paper.reconcile_save", params)

    assert result["error"]["code"] == "invalid_request"  # type: ignore[index]


def test_malformed_json_and_request_shapes_are_structured_errors(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    malformed = dispatcher.handle_line("{broken")
    duplicate = dispatcher.handle_line(
        '{"v":2,"v":2,"id":2,"method":"system.hello","params":{}}'
    )
    non_finite = dispatcher.handle_line(
        '{"v":2,"id":2,"method":"system.hello","params":{"value":NaN}}'
    )
    bad_id = dispatcher.handle(
        {"v": 2, "id": True, "method": "system.hello", "params": {}}
    )
    session_id = _hello(dispatcher)
    bad_params = _request(dispatcher, session_id, "vault.inspect", {"path": 42})
    unknown = _request(dispatcher, session_id, "flashcard.open", {})

    assert malformed["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert duplicate["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert non_finite["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert bad_id["id"] is None
    assert bad_params["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert unknown["error"]["code"] == "invalid_request"  # type: ignore[index]


class _OneShotService:
    def __init__(self) -> None:
        self.calls = 0

    def reset_transient_handles(self) -> None:
        pass

    def library_create_folder(self, _name: str, _locator: str) -> str:
        self.calls += 1
        raise ServiceError("operation_failed", "injected failure", "review")


def test_dispatcher_never_retries_a_mutation():
    service = _OneShotService()
    dispatcher = JsonlDispatcher(service)  # type: ignore[arg-type]
    session_id = _hello(dispatcher)

    response = _request(
        dispatcher,
        session_id,
        "library.create_folder",
        {"name": "Ideas", "vault_locator": "vault-v1:test"},
    )

    assert service.calls == 1
    assert response["error"]["code"] == "operation_failed"  # type: ignore[index]


class _RecordingService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def reset_transient_handles(self) -> None:
        pass

    def __getattr__(self, name: str):
        def record(*_args: object, **_kwargs: object) -> object:
            self.calls.append(name)
            if name == "resolve_system_target":
                return Path("/tmp/validated-paper.md")
            return {"service_method": name}

        return record


MAPPED_METHODS = [
    ("startup.load", {}, "startup_load"),
    ("vault.inspect", {"path": "/tmp/vault"}, "vault_inspect"),
    ("vault.open", {"preview_token": "p"}, "vault_open"),
    ("vault.initialize", {"preview_token": "p"}, "vault_initialize"),
    ("vault.relocate", {"preview_token": "p", "destination_path": "/tmp/new"}, "vault_relocate"),
    ("migration.preflight", {}, "migration_preflight"),
    ("migration.run", {"preflight_token": "m"}, "migration_run"),
    ("paper.create_draft", {}, "paper_create_draft"),
    ("paper.open", {"path": "cache/K.md"}, "paper_open"),
    ("paper.save", {"edit_token": "e", "vault_locator": "l", "display_name": None, "tags": [], "pages": [{"name": None, "content": "body", "type": None}]}, "paper_save"),
    ("paper.reconcile_save", {"vault_locator": "l", "target_path": "cache/K.md", "code": "K", "created": "now", "source_digest": None, "baseline": None, "submitted": {"display_name": None, "tags": [], "pages": [{"name": None, "content": "body", "type": None}]}}, "paper_reconcile_save"),
    ("paper.soft_delete", {"edit_token": "e", "vault_locator": "l"}, "paper_soft_delete"),
    ("library.query", {"verify_index": True}, "library_query"),
    ("library.rebuild", {"vault_locator": "l"}, "library_rebuild"),
    ("library.move", {"paths": ["cache/K.md"], "destination_folder": None, "vault_locator": "l"}, "library_move"),
    ("library.branch", {"path": "cache/K.md", "vault_locator": "l"}, "library_branch"),
    ("library.soft_delete", {"paths": ["cache/K.md"], "vault_locator": "l"}, "library_soft_delete"),
    ("library.restore", {"paths": [".trash/cache/K.md"], "vault_locator": "l"}, "library_restore"),
    ("library.permanently_delete", {"paths": [".trash/cache/K.md"], "vault_locator": "l"}, "library_permanently_delete"),
    ("library.create_folder", {"name": "Ideas", "vault_locator": "l"}, "library_create_folder"),
    ("library.rename_folder", {"folder": "Ideas", "new_name": "Drafts", "vault_locator": "l"}, "library_rename_folder"),
    ("library.merge_folders", {"source": "Ideas", "destination": "Drafts", "vault_locator": "l"}, "library_merge_folders"),
    ("library.soft_delete_folder", {"folder": "Ideas", "vault_locator": "l"}, "library_soft_delete_folder"),
    ("library.restore_folder", {"folder": "Ideas", "vault_locator": "l"}, "library_restore_folder"),
    ("library.permanently_delete_folder", {"folder": "Ideas", "vault_locator": "l"}, "library_permanently_delete_folder"),
    ("system.resolve_target", {"action": "open", "relative_target": "cache/K.md"}, "resolve_system_target"),
]


@pytest.mark.parametrize(("method", "params", "service_method"), MAPPED_METHODS)
def test_every_session_method_has_one_explicit_service_mapping(
    method: str,
    params: dict[str, object],
    service_method: str,
):
    service = _RecordingService()
    dispatcher = JsonlDispatcher(service)  # type: ignore[arg-type]
    session_id = _hello(dispatcher)

    response = _request(dispatcher, session_id, method, params)

    assert response["ok"] is True
    assert service.calls == [service_method]


def test_method_registry_has_exact_classification_and_no_flashcard_route():
    mapped = {method for method, _params, _service in MAPPED_METHODS}

    assert METHODS == frozenset(METHOD_CLASSIFICATIONS)
    assert mapped == METHODS - {"system.hello"}
    assert "flashcard.open" not in METHODS
    assert all(METHOD_CLASSIFICATIONS.values())
    assert MUTATION_METHODS == frozenset(
        method
        for method, category in METHOD_CLASSIFICATIONS.items()
        if category.endswith("_durable")
    )
    assert "paper.reconcile_save" not in MUTATION_METHODS
    assert "startup.load" not in MUTATION_METHODS


def test_run_jsonl_emits_one_v2_line_per_input_until_eof(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    source = StringIO(
        '{"v":2,"id":1,"method":"system.hello","params":{}}\n'
        "not-json\n"
    )
    output = StringIO()

    assert run_jsonl(dispatcher, source, output) == 0
    lines = output.getvalue().splitlines()
    assert len(lines) == 2
    assert all(line.startswith('{"v":2,') for line in lines)
    assert json.loads(lines[0])["ok"] is True
    assert json.loads(lines[1])["error"]["code"] == "invalid_request"


def test_module_sidecar_stdout_contains_only_v2_hello_response():
    completed = subprocess.run(
        [sys.executable, "-m", "keikeu_bridge.sidecar"],
        input='{"v":2,"id":9,"method":"system.hello","params":{}}\n',
        text=True,
        capture_output=True,
        check=False,
    )

    lines = completed.stdout.splitlines()
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert len(lines) == 1
    assert json.loads(lines[0]) == {
        **json.loads(lines[0]),
        "v": 2,
        "id": 9,
        "ok": True,
    }
