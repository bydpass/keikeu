"""JSONL contracts for the Python sidecar boundary."""

from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import subprocess
import sys

import pytest

from keikeu_bridge.protocol import (
    METHODS,
    MUTATION_METHODS,
    PROTOCOL_VERSION,
    JsonlDispatcher,
    run_jsonl,
)
from keikeu_bridge.service import KeikeuService, ServiceError
from keikeu_core.vault import init_vault


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
    assert response["id"] == request_id
    result = response["result"]
    assert isinstance(result, dict)
    session_id = result["session_id"]
    assert isinstance(session_id, str)
    return session_id


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


def _open_vault(
    dispatcher: JsonlDispatcher,
    session_id: str,
    vault: Path,
) -> None:
    preview = _request(
        dispatcher,
        session_id,
        "vault.inspect",
        {"path": str(vault)},
    )
    assert preview["ok"] is True
    token = preview["result"]["token"]  # type: ignore[index]
    opened = _request(
        dispatcher,
        session_id,
        "vault.open",
        {"preview_token": token},
    )
    assert opened["ok"] is True


def test_hello_returns_versions_and_requires_no_session(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))

    session_id = _hello(dispatcher, 41)
    result = dispatcher.handle(
        {
            "v": 1,
            "id": 42,
            "method": "system.hello",
            "params": {},
            "session_id": session_id,
        }
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert result["error"]["layer"] == "jsonl_transport"  # type: ignore[index]


def test_non_hello_requires_the_current_session(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    current = _hello(dispatcher)

    missing = dispatcher.handle(
        {
            "v": 1,
            "id": 2,
            "method": "startup.load",
            "params": {},
        }
    )
    stale = _request(dispatcher, current + "-stale", "startup.load", {})

    assert missing["error"]["code"] == "session_expired"  # type: ignore[index]
    assert stale["error"]["code"] == "session_expired"  # type: ignore[index]


def test_new_hello_expires_old_session_and_opaque_handles(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    dispatcher = JsonlDispatcher(_service(tmp_path))
    first_session = _hello(dispatcher)
    _open_vault(dispatcher, first_session, vault)
    draft = _request(
        dispatcher,
        first_session,
        "paper.create_draft",
        {},
    )
    edit_token = draft["result"]["edit_token"]  # type: ignore[index]

    second_session = _hello(dispatcher, 5)
    old_session = _request(
        dispatcher,
        first_session,
        "paper.soft_delete",
        {"edit_token": edit_token},
    )
    old_handle = _request(
        dispatcher,
        second_session,
        "paper.save",
        {
            "edit_token": edit_token,
            "summary": "Must not save",
            "display_name": None,
            "highlights": [],
            "tags": [],
        },
    )

    assert first_session != second_session
    assert old_session["error"]["code"] == "session_expired"  # type: ignore[index]
    assert old_handle["error"]["code"] == "session_expired"  # type: ignore[index]
    assert list((vault / "cache").glob("*.md")) == []


def test_paper_save_maps_nested_json_to_dtos(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    dispatcher = JsonlDispatcher(_service(tmp_path))
    session_id = _hello(dispatcher)
    _open_vault(dispatcher, session_id, vault)
    draft = _request(dispatcher, session_id, "paper.create_draft", {})
    token = draft["result"]["edit_token"]  # type: ignore[index]

    saved = _request(
        dispatcher,
        session_id,
        "paper.save",
        {
            "edit_token": token,
            "summary": "Protocol summary",
            "display_name": "Protocol Paper",
            "highlights": [
                {"display_name": "Anchor", "content": "Keep this point."}
            ],
            "tags": ["jsonl"],
        },
    )

    assert saved["ok"] is True
    assert saved["result"]["summary"] == "Protocol summary"  # type: ignore[index]
    assert saved["result"]["highlights"] == [  # type: ignore[index]
        {"display_name": "Anchor", "content": "Keep this point."}
    ]
    assert len(list((vault / "cache").glob("*.md"))) == 1


def test_malformed_json_and_wrong_protocol_are_structured_errors(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))

    malformed = dispatcher.handle_line("{broken")
    duplicate = dispatcher.handle_line(
        '{"v":1,"v":1,"id":2,"method":"system.hello","params":{}}'
    )
    non_finite = dispatcher.handle_line(
        '{"v":1,"id":2,"method":"system.hello","params":{"value":NaN}}'
    )
    mismatch = dispatcher.handle(
        {"v": 99, "id": 7, "method": "system.hello", "params": {}}
    )

    assert malformed["id"] is None
    assert malformed["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert duplicate["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert non_finite["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert mismatch["id"] == 7
    assert mismatch["error"]["code"] == "protocol_mismatch"  # type: ignore[index]


def test_request_shape_and_params_are_strict(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    session_id = _hello(dispatcher)

    bad_id = dispatcher.handle(
        {"v": 1, "id": True, "method": "system.hello", "params": {}}
    )
    bad_params = _request(
        dispatcher,
        session_id,
        "vault.inspect",
        {"path": 42},
    )
    unknown = _request(dispatcher, session_id, "paper.unknown", {})

    assert bad_id["id"] is None
    assert bad_id["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert bad_params["error"]["code"] == "invalid_request"  # type: ignore[index]
    assert unknown["error"]["code"] == "invalid_request"  # type: ignore[index]


class _OneShotService:
    def __init__(self) -> None:
        self.calls = 0

    def reset_transient_handles(self) -> None:
        pass

    def library_create_folder(self, _name: str) -> str:
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
        {"name": "Ideas"},
    )

    assert service.calls == 1
    assert response["error"]["code"] == "operation_failed"  # type: ignore[index]
    assert "library.create_folder" in MUTATION_METHODS
    assert "paper.save" in MUTATION_METHODS
    assert "library.query" not in MUTATION_METHODS


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


@pytest.mark.parametrize(
    ("method", "params", "service_method"),
    [
        ("startup.load", {}, "startup_load"),
        ("vault.inspect", {"path": "/tmp/vault"}, "vault_inspect"),
        ("vault.open", {"preview_token": "p"}, "vault_open"),
        ("vault.initialize", {"preview_token": "p"}, "vault_initialize"),
        (
            "vault.relocate",
            {"preview_token": "p", "destination_path": "/tmp/new"},
            "vault_relocate",
        ),
        ("migration.preflight", {}, "migration_preflight"),
        ("migration.run", {"preflight_token": "m"}, "migration_run"),
        ("paper.create_draft", {}, "paper_create_draft"),
        ("paper.open", {"path": "cache/K.md"}, "paper_open"),
        (
            "paper.save",
            {
                "edit_token": "e",
                "summary": "Summary",
                "display_name": None,
                "highlights": [],
                "tags": [],
            },
            "paper_save",
        ),
        ("paper.soft_delete", {"edit_token": "e"}, "paper_soft_delete"),
        ("flashcard.open", {"path": None}, "flashcard_open"),
        ("library.query", {}, "library_query"),
        ("library.rebuild", {}, "library_query"),
        (
            "library.move",
            {"paths": ["cache/K.md"], "destination_folder": None},
            "library_move",
        ),
        ("library.branch", {"path": "cache/K.md"}, "library_branch"),
        (
            "library.soft_delete",
            {"paths": ["cache/K.md"]},
            "library_soft_delete",
        ),
        (
            "library.restore",
            {"paths": [".trash/cache/K.md"]},
            "library_restore",
        ),
        (
            "library.permanently_delete",
            {"paths": [".trash/cache/K.md"]},
            "library_permanently_delete",
        ),
        ("library.create_folder", {"name": "Ideas"}, "library_create_folder"),
        (
            "library.rename_folder",
            {"folder": "Ideas", "new_name": "Drafts"},
            "library_rename_folder",
        ),
        (
            "library.merge_folders",
            {"source": "Ideas", "destination": "Drafts"},
            "library_merge_folders",
        ),
        (
            "library.soft_delete_folder",
            {"folder": "Ideas"},
            "library_soft_delete_folder",
        ),
        (
            "library.restore_folder",
            {"folder": "Ideas"},
            "library_restore_folder",
        ),
        (
            "library.permanently_delete_folder",
            {"folder": "Ideas"},
            "library_permanently_delete_folder",
        ),
        (
            "system.resolve_target",
            {"action": "open", "relative_target": "cache/K.md"},
            "resolve_system_target",
        ),
    ],
)
def test_every_session_method_has_an_explicit_service_mapping(
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
    assert method in METHODS


def test_run_jsonl_emits_one_compact_line_per_input_until_eof(tmp_path):
    dispatcher = JsonlDispatcher(_service(tmp_path))
    source = StringIO(
        '{"v":1,"id":1,"method":"system.hello","params":{}}\n'
        "not-json\n"
    )
    output = StringIO()

    result = run_jsonl(dispatcher, source, output)
    lines = output.getvalue().splitlines()

    assert result == 0
    assert len(lines) == 2
    assert all(line.startswith('{"v":1,') for line in lines)
    assert json.loads(lines[0])["ok"] is True
    assert json.loads(lines[1])["error"]["code"] == "invalid_request"


def test_module_sidecar_stdout_contains_only_the_hello_response():
    completed = subprocess.run(
        [sys.executable, "-m", "keikeu_bridge.sidecar"],
        input='{"v":1,"id":9,"method":"system.hello","params":{}}\n',
        text=True,
        capture_output=True,
        check=False,
    )

    lines = completed.stdout.splitlines()
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == 9
