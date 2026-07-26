"""Versioned JSONL adapter for the transport-neutral application service."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import secrets
from typing import Any, TextIO

from keikeu_bridge.dto import HighlightDto, PaperSaveDto
from keikeu_bridge.service import KeikeuService, ServiceError

__all__ = [
    "APP_VERSION",
    "CORE_VERSION",
    "METHODS",
    "MUTATION_METHODS",
    "PROTOCOL_VERSION",
    "JsonlDispatcher",
    "run_jsonl",
]

PROTOCOL_VERSION = 1
CORE_VERSION = "paper-v3/index-v3"

try:
    APP_VERSION = version("keikeu")
except PackageNotFoundError:
    APP_VERSION = "0.1.0"

_SESSION_METHODS = {
    "startup.load",
    "vault.inspect",
    "vault.open",
    "vault.initialize",
    "vault.relocate",
    "migration.preflight",
    "migration.run",
    "paper.create_draft",
    "paper.open",
    "paper.save",
    "paper.soft_delete",
    "flashcard.open",
    "library.query",
    "library.rebuild",
    "library.move",
    "library.branch",
    "library.soft_delete",
    "library.restore",
    "library.permanently_delete",
    "library.create_folder",
    "library.rename_folder",
    "library.merge_folders",
    "library.soft_delete_folder",
    "library.restore_folder",
    "library.permanently_delete_folder",
    "system.resolve_target",
}
METHODS = frozenset({"system.hello", *_SESSION_METHODS})

MUTATION_METHODS = frozenset(
    {
        "startup.load",
        "vault.open",
        "vault.initialize",
        "vault.relocate",
        "migration.run",
        "paper.save",
        "paper.soft_delete",
        "library.rebuild",
        "library.move",
        "library.branch",
        "library.soft_delete",
        "library.restore",
        "library.permanently_delete",
        "library.create_folder",
        "library.rename_folder",
        "library.merge_folders",
        "library.soft_delete_folder",
        "library.restore_folder",
        "library.permanently_delete_folder",
    }
)


class _ProtocolError(Exception):
    def __init__(self, code: str, message: str, recovery: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recovery = recovery


def _expect_keys(
    params: dict[str, object],
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    if any(not isinstance(key, str) for key in params):
        raise _ProtocolError(
            "invalid_request",
            "param names must be strings",
            "correct_input",
        )
    optional = set() if optional is None else optional
    missing = required - params.keys()
    unexpected = params.keys() - required - optional
    if missing:
        raise _ProtocolError(
            "invalid_request",
            f"missing params: {', '.join(sorted(missing))}",
            "correct_input",
        )
    if unexpected:
        raise _ProtocolError(
            "invalid_request",
            f"unexpected params: {', '.join(sorted(unexpected))}",
            "correct_input",
        )


def _string(params: dict[str, object], name: str) -> str:
    value = params.get(name)
    if not isinstance(value, str):
        raise _ProtocolError(
            "invalid_request",
            f"{name} must be a string",
            "correct_input",
        )
    return value


def _nullable_string(params: dict[str, object], name: str) -> str | None:
    value = params.get(name)
    if value is not None and not isinstance(value, str):
        raise _ProtocolError(
            "invalid_request",
            f"{name} must be a string or null",
            "correct_input",
        )
    return value


def _strings(params: dict[str, object], name: str) -> list[str]:
    value = params.get(name)
    if not isinstance(value, list) or any(
        not isinstance(item, str) for item in value
    ):
        raise _ProtocolError(
            "invalid_request",
            f"{name} must be an array of strings",
            "correct_input",
        )
    return value


def _json_value(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported protocol result type: {type(value).__name__}")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON field: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


class JsonlDispatcher:
    """Validate one request at a time and call one application service."""

    def __init__(self, service: KeikeuService) -> None:
        self._service = service
        self._session_id: str | None = None

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def handle_line(self, line: str) -> dict[str, object]:
        try:
            request = json.loads(
                line,
                object_pairs_hook=_strict_object,
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, UnicodeError, ValueError):
            return self._error(
                None,
                "invalid_request",
                "request must be one UTF-8 JSON object",
                "correct_input",
                "jsonl_transport",
            )
        return self.handle(request)

    def handle(self, request: object) -> dict[str, object]:
        request_id: int | None = None
        try:
            if not isinstance(request, dict):
                raise _ProtocolError(
                    "invalid_request",
                    "request must be a JSON object",
                    "correct_input",
                )
            if any(not isinstance(key, str) for key in request):
                raise _ProtocolError(
                    "invalid_request",
                    "request field names must be strings",
                    "correct_input",
                )
            request_id = request.get("id")  # type: ignore[assignment]
            if type(request_id) is not int or request_id < 0:
                request_id = None
                raise _ProtocolError(
                    "invalid_request",
                    "id must be a non-negative integer",
                    "correct_input",
                )
            allowed = {"v", "id", "method", "params", "session_id"}
            unexpected = request.keys() - allowed
            if unexpected:
                raise _ProtocolError(
                    "invalid_request",
                    f"unexpected request fields: {', '.join(sorted(unexpected))}",
                    "correct_input",
                )
            protocol_version = request.get("v")
            if type(protocol_version) is not int:
                raise _ProtocolError(
                    "invalid_request",
                    "v must be an integer",
                    "correct_input",
                )
            if protocol_version != PROTOCOL_VERSION:
                raise _ProtocolError(
                    "protocol_mismatch",
                    f"protocol v{protocol_version} is not supported",
                    "restart_sidecar",
                )
            method = request.get("method")
            if not isinstance(method, str) or not method:
                raise _ProtocolError(
                    "invalid_request",
                    "method must be a non-empty string",
                    "correct_input",
                )
            params = request.get("params")
            if not isinstance(params, dict):
                raise _ProtocolError(
                    "invalid_request",
                    "params must be an object",
                    "correct_input",
                )
            if method == "system.hello":
                _expect_keys(params, set())
                if "session_id" in request:
                    raise _ProtocolError(
                        "invalid_request",
                        "system.hello must not include session_id",
                        "correct_input",
                    )
                return self._hello(request_id)
            if method not in _SESSION_METHODS:
                raise _ProtocolError(
                    "invalid_request",
                    f"unknown method: {method}",
                    "correct_input",
                )
            session_id = request.get("session_id")
            if (
                not isinstance(session_id, str)
                or self._session_id is None
                or not secrets.compare_digest(session_id, self._session_id)
            ):
                raise _ProtocolError(
                    "session_expired",
                    "system.hello is required for the current sidecar session",
                    "hello",
                )
            result = self._dispatch(method, params)
            return {
                "v": PROTOCOL_VERSION,
                "id": request_id,
                "ok": True,
                "result": _json_value(result),
            }
        except _ProtocolError as error:
            return self._error(
                request_id,
                error.code,
                error.message,
                error.recovery,
                "jsonl_transport",
            )
        except ServiceError as error:
            return self._error(
                request_id,
                error.code,
                error.message,
                error.recovery,
                "application_service",
            )
        except Exception:
            return self._error(
                request_id,
                "operation_failed",
                "unexpected Python sidecar failure",
                "restart_sidecar",
                "python_sidecar",
            )

    def _hello(self, request_id: int) -> dict[str, object]:
        self._service.reset_transient_handles()
        self._session_id = secrets.token_urlsafe(24)
        return {
            "v": PROTOCOL_VERSION,
            "id": request_id,
            "ok": True,
            "result": {
                "protocol_version": PROTOCOL_VERSION,
                "session_id": self._session_id,
                "app_version": APP_VERSION,
                "core_version": CORE_VERSION,
            },
        }

    @staticmethod
    def _error(
        request_id: int | None,
        code: str,
        message: str,
        recovery: str,
        layer: str,
    ) -> dict[str, object]:
        return {
            "v": PROTOCOL_VERSION,
            "id": request_id,
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "recovery": recovery,
                "layer": layer,
            },
        }

    def _dispatch(self, method: str, params: dict[str, object]) -> object:
        if method == "startup.load":
            _expect_keys(params, set())
            return self._service.startup_load()
        if method == "vault.inspect":
            _expect_keys(params, {"path"})
            return self._service.vault_inspect(_string(params, "path"))
        if method == "vault.open":
            _expect_keys(params, {"preview_token"})
            return self._service.vault_open(_string(params, "preview_token"))
        if method == "vault.initialize":
            _expect_keys(params, {"preview_token"})
            return self._service.vault_initialize(
                _string(params, "preview_token")
            )
        if method == "vault.relocate":
            _expect_keys(params, {"preview_token", "destination_path"})
            return self._service.vault_relocate(
                _string(params, "preview_token"),
                _string(params, "destination_path"),
            )
        if method == "migration.preflight":
            _expect_keys(params, set())
            return self._service.migration_preflight()
        if method == "migration.run":
            _expect_keys(params, {"preflight_token"})
            return self._service.migration_run(
                _string(params, "preflight_token")
            )
        if method == "paper.create_draft":
            _expect_keys(params, set())
            return self._service.paper_create_draft()
        if method == "paper.open":
            _expect_keys(params, {"path"})
            return self._service.paper_open(_string(params, "path"))
        if method == "paper.save":
            return self._paper_save(params)
        if method == "paper.soft_delete":
            _expect_keys(params, {"edit_token"})
            return self._service.paper_soft_delete(
                _string(params, "edit_token")
            )
        if method == "flashcard.open":
            _expect_keys(params, set(), {"path"})
            return self._service.flashcard_open(
                _nullable_string(params, "path")
            )
        if method in {"library.query", "library.rebuild"}:
            _expect_keys(params, set(), {"scope", "search", "sort"})
            return self._service.library_query(
                scope=_string(params, "scope") if "scope" in params else "all",
                search=_string(params, "search") if "search" in params else "",
                sort=(
                    _string(params, "sort")
                    if "sort" in params
                    else "updated_desc"
                ),
                rebuild=method == "library.rebuild",
            )
        if method == "library.move":
            _expect_keys(params, {"paths", "destination_folder"})
            return self._service.library_move(
                _strings(params, "paths"),
                _nullable_string(params, "destination_folder"),
            )
        if method == "library.branch":
            _expect_keys(params, {"path"})
            return self._service.library_branch(_string(params, "path"))
        if method in {
            "library.soft_delete",
            "library.restore",
            "library.permanently_delete",
        }:
            _expect_keys(params, {"paths"})
            paths = _strings(params, "paths")
            if method == "library.soft_delete":
                return self._service.library_soft_delete(paths)
            if method == "library.restore":
                return self._service.library_restore(paths)
            return self._service.library_permanently_delete(paths)
        if method == "library.create_folder":
            _expect_keys(params, {"name"})
            return self._service.library_create_folder(_string(params, "name"))
        if method == "library.rename_folder":
            _expect_keys(params, {"folder", "new_name"})
            return self._service.library_rename_folder(
                _string(params, "folder"),
                _string(params, "new_name"),
            )
        if method == "library.merge_folders":
            _expect_keys(params, {"source", "destination"})
            return self._service.library_merge_folders(
                _string(params, "source"),
                _string(params, "destination"),
            )
        if method in {
            "library.soft_delete_folder",
            "library.restore_folder",
            "library.permanently_delete_folder",
        }:
            _expect_keys(params, {"folder"})
            folder = _string(params, "folder")
            if method == "library.soft_delete_folder":
                return self._service.library_soft_delete_folder(folder)
            if method == "library.restore_folder":
                return self._service.library_restore_folder(folder)
            return self._service.library_permanently_delete_folder(folder)
        if method == "system.resolve_target":
            _expect_keys(params, {"action", "relative_target"})
            return {
                "path": str(
                    self._service.resolve_system_target(
                        _string(params, "action"),
                        _string(params, "relative_target"),
                    )
                )
            }
        raise _ProtocolError(
            "invalid_request",
            f"unknown method: {method}",
            "correct_input",
        )

    def _paper_save(self, params: dict[str, object]) -> object:
        _expect_keys(
            params,
            {"edit_token", "summary", "display_name", "highlights", "tags"},
        )
        highlights = params.get("highlights")
        if not isinstance(highlights, list):
            raise _ProtocolError(
                "invalid_request",
                "highlights must be an array",
                "correct_input",
            )
        parsed_highlights: list[HighlightDto] = []
        for index, item in enumerate(highlights):
            if not isinstance(item, dict):
                raise _ProtocolError(
                    "invalid_request",
                    f"highlights[{index}] must be an object",
                    "correct_input",
                )
            _expect_keys(item, {"display_name", "content"})
            parsed_highlights.append(
                HighlightDto(
                    _nullable_string(item, "display_name"),
                    _string(item, "content"),
                )
            )
        return self._service.paper_save(
            PaperSaveDto(
                edit_token=_string(params, "edit_token"),
                summary=_string(params, "summary"),
                display_name=_nullable_string(params, "display_name"),
                highlights=tuple(parsed_highlights),
                tags=tuple(_strings(params, "tags")),
            )
        )


def run_jsonl(
    dispatcher: JsonlDispatcher,
    input_stream: TextIO,
    output_stream: TextIO,
) -> int:
    """Read until EOF and emit exactly one compact response per input line."""
    for line in input_stream:
        response = dispatcher.handle_line(line)
        output_stream.write(
            json.dumps(
                response,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        )
        output_stream.flush()
    return 0
