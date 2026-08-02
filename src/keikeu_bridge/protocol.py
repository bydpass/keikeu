"""Versioned JSONL adapter for the transport-neutral application service."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from importlib.metadata import PackageNotFoundError, version
import json
import math
from pathlib import Path
import secrets
from typing import Any, TextIO

from keikeu_bridge.dto import (
    CardPageDto,
    PaperEditableDto,
    PaperReconcileRequestDto,
    PaperSaveDto,
)
from keikeu_bridge.service import KeikeuService, ServiceError

__all__ = [
    "APP_VERSION",
    "CORE_VERSION",
    "METHOD_CLASSIFICATIONS",
    "METHODS",
    "MUTATION_METHODS",
    "PROTOCOL_VERSION",
    "JsonlDispatcher",
    "run_jsonl",
]

PROTOCOL_VERSION = 2
CORE_VERSION = "paper-v4/index-v4"

try:
    APP_VERSION = version("keikeu")
except PackageNotFoundError:
    APP_VERSION = "0.1.0"

METHOD_CLASSIFICATIONS = {
    "system.hello": "readonly_session",
    "vault.inspect": "readonly_session",
    "migration.preflight": "readonly_session",
    "paper.create_draft": "readonly_session",
    "paper.open": "readonly_session",
    "paper.reconcile_save": "readonly_session",
    "library.query": "readonly_session",
    "system.resolve_target": "readonly_session",
    "startup.load": "replay_safe_local_state",
    "vault.open": "vault_durable",
    "vault.initialize": "vault_durable",
    "vault.relocate": "vault_durable",
    "migration.run": "migration_durable",
    "paper.save": "paper_durable",
    "paper.soft_delete": "paper_durable",
    "library.move": "library_path_durable",
    "library.branch": "library_path_durable",
    "library.soft_delete": "library_path_durable",
    "library.restore": "library_path_durable",
    "library.permanently_delete": "library_path_durable",
    "library.create_folder": "library_path_durable",
    "library.rename_folder": "library_path_durable",
    "library.merge_folders": "library_path_durable",
    "library.soft_delete_folder": "library_path_durable",
    "library.restore_folder": "library_path_durable",
    "library.permanently_delete_folder": "library_path_durable",
    "library.rebuild": "index_durable",
}
METHODS = frozenset(METHOD_CLASSIFICATIONS)
_SESSION_METHODS = METHODS - {"system.hello"}

MUTATION_METHODS = frozenset(
    method
    for method, category in METHOD_CLASSIFICATIONS.items()
    if category.endswith("_durable")
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


def _boolean(params: dict[str, object], name: str) -> bool:
    value = params.get(name)
    if type(value) is not bool:
        raise _ProtocolError(
            "invalid_request",
            f"{name} must be a boolean",
            "correct_input",
        )
    return value


def _pages(value: object, field_name: str = "pages") -> tuple[CardPageDto, ...]:
    if not isinstance(value, list):
        raise _ProtocolError(
            "invalid_request",
            f"{field_name} must be an array",
            "correct_input",
        )
    pages: list[CardPageDto] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise _ProtocolError(
                "invalid_request",
                f"{field_name}[{index}] must be an object",
                "correct_input",
            )
        _expect_keys(item, {"name", "content", "type"})
        page_type = _nullable_string(item, "type")
        if page_type not in {None, "summary", "snapshot", "whisper"}:
            raise _ProtocolError(
                "invalid_request",
                f"{field_name}[{index}].type is invalid",
                "correct_input",
            )
        pages.append(
            CardPageDto(
                _nullable_string(item, "name"),
                _string(item, "content"),
                page_type,
            )
        )
    return tuple(pages)


def _editable(value: object, field_name: str) -> PaperEditableDto:
    if not isinstance(value, dict):
        raise _ProtocolError(
            "invalid_request",
            f"{field_name} must be an object",
            "correct_input",
        )
    _expect_keys(value, {"display_name", "tags", "pages"})
    return PaperEditableDto(
        _nullable_string(value, "display_name"),
        tuple(_strings(value, "tags")),
        _pages(value.get("pages"), f"{field_name}.pages"),
    )


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
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("protocol result contains a non-finite number")
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
            try:
                serialized = _json_value(result)
            except Exception as error:
                if method in MUTATION_METHODS:
                    raise ServiceError(
                        "commit_unknown",
                        "durable operation completed but its response could not be serialized",
                        "restart_then_reload",
                    ) from error
                raise
            return {
                "v": PROTOCOL_VERSION,
                "id": request_id,
                "ok": True,
                "result": serialized,
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
        if method == "paper.reconcile_save":
            return self._paper_reconcile_save(params)
        if method == "paper.soft_delete":
            _expect_keys(params, {"edit_token", "vault_locator"})
            return self._service.paper_soft_delete(
                _string(params, "edit_token"),
                _string(params, "vault_locator"),
            )
        if method == "library.query":
            _expect_keys(
                params,
                set(),
                {"scope", "search", "sort", "verify_index"},
            )
            return self._service.library_query(
                scope=_string(params, "scope") if "scope" in params else "all",
                search=_string(params, "search") if "search" in params else "",
                sort=(
                    _string(params, "sort")
                    if "sort" in params
                    else "updated_desc"
                ),
                verify_index=(
                    _boolean(params, "verify_index")
                    if "verify_index" in params
                    else False
                ),
            )
        if method == "library.rebuild":
            _expect_keys(params, {"vault_locator"})
            return self._service.library_rebuild(_string(params, "vault_locator"))
        if method == "library.move":
            _expect_keys(params, {"paths", "destination_folder", "vault_locator"})
            return self._service.library_move(
                _strings(params, "paths"),
                _nullable_string(params, "destination_folder"),
                _string(params, "vault_locator"),
            )
        if method == "library.branch":
            _expect_keys(params, {"path", "vault_locator"})
            return self._service.library_branch(
                _string(params, "path"),
                _string(params, "vault_locator"),
            )
        if method in {
            "library.soft_delete",
            "library.restore",
            "library.permanently_delete",
        }:
            _expect_keys(params, {"paths", "vault_locator"})
            paths = _strings(params, "paths")
            locator = _string(params, "vault_locator")
            if method == "library.soft_delete":
                return self._service.library_soft_delete(paths, locator)
            if method == "library.restore":
                return self._service.library_restore(paths, locator)
            return self._service.library_permanently_delete(paths, locator)
        if method == "library.create_folder":
            _expect_keys(params, {"name", "vault_locator"})
            return self._service.library_create_folder(
                _string(params, "name"),
                _string(params, "vault_locator"),
            )
        if method == "library.rename_folder":
            _expect_keys(params, {"folder", "new_name", "vault_locator"})
            return self._service.library_rename_folder(
                _string(params, "folder"),
                _string(params, "new_name"),
                _string(params, "vault_locator"),
            )
        if method == "library.merge_folders":
            _expect_keys(params, {"source", "destination", "vault_locator"})
            return self._service.library_merge_folders(
                _string(params, "source"),
                _string(params, "destination"),
                _string(params, "vault_locator"),
            )
        if method in {
            "library.soft_delete_folder",
            "library.restore_folder",
            "library.permanently_delete_folder",
        }:
            _expect_keys(params, {"folder", "vault_locator"})
            folder = _string(params, "folder")
            locator = _string(params, "vault_locator")
            if method == "library.soft_delete_folder":
                return self._service.library_soft_delete_folder(folder, locator)
            if method == "library.restore_folder":
                return self._service.library_restore_folder(folder, locator)
            return self._service.library_permanently_delete_folder(folder, locator)
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
            {"edit_token", "vault_locator", "display_name", "tags", "pages"},
        )
        return self._service.paper_save(
            PaperSaveDto(
                edit_token=_string(params, "edit_token"),
                vault_locator=_string(params, "vault_locator"),
                display_name=_nullable_string(params, "display_name"),
                tags=tuple(_strings(params, "tags")),
                pages=_pages(params.get("pages")),
            )
        )

    def _paper_reconcile_save(self, params: dict[str, object]) -> object:
        _expect_keys(
            params,
            {
                "vault_locator",
                "target_path",
                "code",
                "created",
                "source_digest",
                "baseline",
                "submitted",
            },
        )
        baseline_value = params.get("baseline")
        baseline = (
            None
            if baseline_value is None
            else _editable(baseline_value, "baseline")
        )
        return self._service.paper_reconcile_save(
            PaperReconcileRequestDto(
                vault_locator=_string(params, "vault_locator"),
                target_path=_string(params, "target_path"),
                code=_string(params, "code"),
                created=_string(params, "created"),
                source_digest=_nullable_string(params, "source_digest"),
                baseline=baseline,
                submitted=_editable(params.get("submitted"), "submitted"),
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
