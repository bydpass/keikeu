"""Concrete application service shared by desktop presentation adapters."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
from pathlib import Path
import secrets
from typing import Iterator, Iterable, TypeVar, cast
import unicodedata

from keikeu_bridge.dto import (
    CardPageDto,
    IndexErrorDto,
    LibraryEntryDto,
    LibraryViewDto,
    MigrationIssueDto,
    MigrationPreflightDto,
    MigrationResultDto,
    NameResultDto,
    OperationReportDto,
    OperationReportResultDto,
    OperationReportsResultDto,
    PaperDto,
    PaperEditableDto,
    PaperOpenResultDto,
    PaperReconcileRequestDto,
    PaperReconcileResultDto,
    PaperSaveDto,
    PaperSaveResultDto,
    RepairDto,
    StartupDto,
    VaultPreviewDto,
)
from keikeu_bridge.local_state import claim_daily_card
from keikeu_core.indexer import (
    query_index_v4,
    query_trash_v4,
    rebuild_index_v4,
    verify_index_v4,
)
from keikeu_core.markdown_io import (
    branch_paper_v4,
    parse_paper_v4_bytes,
    read_paper_v4_snapshot,
    render_paper_v4_bytes,
    replace_paper_v4_bytes,
    write_paper_v4,
)
from keikeu_core.migration_v01 import (
    MigrationPreflight,
    MigrationPreflightError,
    inspect_v01_vault,
    is_v01_vault,
    migrate_v01_vault,
)
from keikeu_core.migration_v4 import (
    MigrationCommitUnknown,
    MigrationPreflightV4,
    classify_migration_stage,
    inspect_paper_v4_migration,
    migrate_papers_to_v4,
)
from keikeu_core.models import CardPageV4, PaperV4
from keikeu_core.vault import (
    PathOperationResult,
    VaultSelectionToken,
    capture_vault_selection_token,
    copy_vault_no_follow,
    create_folder,
    get_vault,
    init_vault,
    is_vault,
    list_active_folders,
    list_active_papers,
    list_trashed_folders,
    list_trashed_papers,
    merge_folders,
    move_papers,
    next_paper_code,
    open_directory_no_follow,
    permanently_delete_folder,
    permanently_delete_papers,
    rename_folder,
    require_home_path,
    resolve_active_paper_path,
    restore_folder,
    restore_papers,
    set_vault,
    soft_delete_folder,
    soft_delete_papers,
    validate_regular_tree_no_follow,
    validate_vault_tree_no_follow,
    vault_index_version,
)

__all__ = ["KeikeuService", "ServiceError"]


_SOURCE_V01 = "v0.1"
_SOURCE_PAPER = "paper"
_SCOPE_ALL = "all"
_SCOPE_UNFILED = "unfiled"
_SCOPE_TRASH = "trash"
_FOLDER_PREFIX = "folder:"
_SORT_MODES = {"updated_desc", "name", "created_desc", "created_asc"}


class ServiceError(RuntimeError):
    """One stable application-boundary error with an explicit recovery hint."""

    def __init__(self, code: str, message: str, recovery: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recovery = recovery


def _service_error(error: Exception) -> ServiceError:
    message = str(error) or error.__class__.__name__
    if isinstance(error, MigrationCommitUnknown):
        return ServiceError("commit_unknown", message, "restart_then_reload")
    if isinstance(error, MigrationPreflightError):
        return ServiceError("preflight_blocked", message, "inspect")
    if isinstance(error, FileNotFoundError):
        return ServiceError("not_found", message, "refresh")
    if isinstance(error, FileExistsError):
        return ServiceError("conflict", message, "choose_other")
    if isinstance(error, TypeError):
        return ServiceError("invalid_request", message, "correct_input")
    if isinstance(error, ValueError):
        lowered = message.casefold()
        if "changed externally" in lowered or "changed while" in lowered:
            return ServiceError("stale_snapshot", message, "refresh")
        if "outside current user home" in lowered or "symlink" in lowered:
            return ServiceError("unsafe_path", message, "choose_other")
        return ServiceError("validation_failed", message, "correct_input")
    return ServiceError("operation_failed", message, "retry_after_review")


@contextmanager
def _translated_errors() -> Iterator[None]:
    try:
        yield
    except ServiceError:
        raise
    except (OSError, TypeError, ValueError, UnicodeError) as error:
        raise _service_error(error) from error


@dataclass
class _PaperEditState:
    path: Path | None
    paper: PaperV4 | None
    source_bytes: bytes | None
    code: str
    created: datetime
    target_path: Path


@dataclass(frozen=True)
class _VaultPreviewState:
    path: Path
    kind: str
    source_kind: str = ""


@dataclass(frozen=True)
class _MigrationState:
    path: Path
    root_identity: tuple[int, int]
    kind: str
    preflight_v4: MigrationPreflightV4 | None = None


_TokenState = TypeVar("_TokenState")


class KeikeuService:
    """Own UI-neutral workflow orchestration for one local app process."""

    def __init__(self, *, config_path: Path, state_path: Path) -> None:
        self._config_path = config_path
        self._state_path = state_path
        self._active_vault: Path | None = None
        self._root_identity: tuple[int, int] | None = None
        self._tokens: dict[str, object] = {}

    def reset_transient_handles(self) -> None:
        """Expire previews, edit snapshots, and migration preflights."""
        self._tokens.clear()

    def _put_token(self, value: object) -> str:
        token = secrets.token_urlsafe(24)
        while token in self._tokens:
            token = secrets.token_urlsafe(24)
        self._tokens[token] = value
        return token

    def _get_token(self, token: str, expected: type[_TokenState]) -> _TokenState:
        if not isinstance(token, str) or not token:
            raise ServiceError("invalid_request", "token is required", "restart_action")
        value = self._tokens.get(token)
        if not isinstance(value, expected):
            raise ServiceError(
                "session_expired",
                "token is missing or no longer valid",
                "restart_action",
            )
        return cast(_TokenState, value)

    def _discard_token(self, token: str) -> None:
        self._tokens.pop(token, None)

    def _require_vault(self) -> Path:
        if self._active_vault is None:
            raise ServiceError(
                "validation_failed",
                "no active Vault",
                "choose_vault",
            )
        vault, identity = self._pin_home_vault_root(
            self._active_vault,
            self._root_identity,
        )
        self._active_vault = vault
        self._root_identity = identity
        return vault

    def _locator_for(self, vault: Path, root_identity: tuple[int, int]) -> str:
        material = "\0".join(
            (
                str(self._config_path.expanduser().absolute()),
                str(vault),
                str(root_identity[0]),
                str(root_identity[1]),
            )
        ).encode("utf-8")
        return f"vault-v1:{hashlib.sha256(material).hexdigest()}"

    def _vault_locator(self) -> str:
        if self._active_vault is None or self._root_identity is None:
            raise ServiceError("validation_failed", "no active Vault", "choose_vault")
        return self._locator_for(self._active_vault, self._root_identity)

    def _require_locator(self, locator: str) -> None:
        if not isinstance(locator, str) or locator != self._vault_locator():
            raise ServiceError(
                "stale_snapshot",
                "Vault locator no longer matches the active Vault",
                "reload",
            )

    @staticmethod
    def _index_state(vault: Path) -> str:
        try:
            return "current" if verify_index_v4(vault) else "degraded"
        except (OSError, ValueError, UnicodeError):
            return "degraded"

    @staticmethod
    def _pin_home_vault_root(
        vault: Path,
        expected_identity: tuple[int, int] | None = None,
    ) -> tuple[Path, tuple[int, int]]:
        raw_vault = vault.expanduser().absolute()
        root_fd = open_directory_no_follow(raw_vault)
        try:
            safe_vault = require_home_path(raw_vault)
            safe_fd = open_directory_no_follow(safe_vault)
            try:
                raw_stat = os.fstat(root_fd)
                safe_stat = os.fstat(safe_fd)
                identity = (raw_stat.st_dev, raw_stat.st_ino)
                if identity != (safe_stat.st_dev, safe_stat.st_ino):
                    raise ValueError("Vault root changed during validation")
                if expected_identity is not None and identity != expected_identity:
                    raise ValueError("Vault root changed after selection")
                return safe_vault, identity
            finally:
                os.close(safe_fd)
        finally:
            os.close(root_fd)

    @staticmethod
    def _classify_vault_source_no_follow(source: Path) -> str:
        validate_regular_tree_no_follow(source)
        version = vault_index_version(source)
        if version in {2, 3, 4}:
            if not is_vault(source):
                raise ValueError(f"index v{version} Vault structure is incomplete")
            return _SOURCE_PAPER
        if version == 1:
            if not is_v01_vault(source):
                raise ValueError("index v1 does not match a migratable v0.1 Vault")
            return _SOURCE_V01
        if version is not None:
            raise ValueError(f"unsupported Vault index version: {version}")
        if is_v01_vault(source):
            return _SOURCE_V01
        if is_vault(source):
            return _SOURCE_PAPER
        raise ValueError("folder is not a supported v0.1 or Paper Vault")

    @classmethod
    def _classify_configured_home_vault(cls, source: Path) -> str:
        version = vault_index_version(source)
        if version in {2, 3, 4}:
            if not is_vault(source):
                raise ValueError(f"index v{version} Vault structure is incomplete")
            return _SOURCE_PAPER
        if version is None and is_vault(source):
            return _SOURCE_PAPER
        validate_regular_tree_no_follow(source)
        if version == 1 and is_v01_vault(source):
            return _SOURCE_V01
        if version is not None:
            raise ValueError(f"unsupported Vault index version: {version}")
        if is_v01_vault(source):
            return _SOURCE_V01
        raise ValueError("folder is not a supported v0.1 or Paper Vault")

    @classmethod
    def _validated_v01_selection(cls, vault: Path) -> VaultSelectionToken:
        before = capture_vault_selection_token(vault)
        if cls._classify_vault_source_no_follow(vault) != _SOURCE_V01:
            raise ValueError("v0.1 Vault changed before migration")
        preflight = inspect_v01_vault(vault)
        if not preflight.ready:
            raise MigrationPreflightError(preflight.issues)
        if cls._classify_vault_source_no_follow(vault) != _SOURCE_V01:
            raise ValueError("v0.1 Vault changed during preflight")
        final = capture_vault_selection_token(vault)
        if final != before:
            raise ValueError("v0.1 Vault changed during preflight")
        return final

    def _activate(
        self,
        vault: Path,
        root_identity: tuple[int, int],
        *,
        claim_daily: bool = True,
    ) -> StartupDto:
        self._active_vault = vault
        self._root_identity = root_identity
        show_daily = False
        if claim_daily:
            try:
                show_daily = claim_daily_card(state_path=self._state_path)
            except (OSError, ValueError):
                show_daily = False
        return StartupDto(
            state="ready",
            show_daily_card=show_daily,
            vault_locator=self._vault_locator(),
            index_state=self._index_state(vault),
        )

    def _startup_for_selected(
        self,
        vault: Path,
        root_identity: tuple[int, int],
        *,
        claim_daily: bool = True,
    ) -> StartupDto:
        stage = classify_migration_stage(vault)
        vault, root_identity = self._pin_home_vault_root(vault, root_identity)
        self._active_vault = vault
        self._root_identity = root_identity
        if stage == "v01_to_v3":
            migration = self._migration_preflight_v01(vault, root_identity)
            return StartupDto(
                state="migration",
                migration=migration,
                vault_locator=self._vault_locator(),
            )
        if stage in {"paper_to_v4", "repair_required"}:
            migration = self._migration_preflight_v4(vault, root_identity)
            return StartupDto(
                state="migration",
                migration=migration,
                vault_locator=self._vault_locator(),
            )
        return self._activate(vault, root_identity, claim_daily=claim_daily)

    def startup_load(self) -> StartupDto:
        """Load configured state without exposing a filesystem path to the UI."""
        configured = get_vault(self._config_path)
        if configured is None:
            return StartupDto(state="vault_picker")
        raw_vault = configured.expanduser().absolute()
        if not os.path.lexists(raw_vault):
            return StartupDto(
                state="vault_picker",
                message="configured Vault does not exist",
                configured_path=str(raw_vault),
            )
        try:
            safe_vault, identity = self._pin_home_vault_root(raw_vault)
            return self._startup_for_selected(safe_vault, identity)
        except (OSError, ValueError, UnicodeError) as error:
            self._active_vault = None
            self._root_identity = None
            message = str(error)
            try:
                preview = self.vault_inspect(str(raw_vault))
            except ServiceError as preview_error:
                preview = None
                message = preview_error.message
            if preview is not None and preview.kind != "relocate":
                preview = None
            return StartupDto(
                state="vault_picker",
                message=message,
                configured_path=str(raw_vault),
                preview=preview,
            )

    @staticmethod
    def _directory_is_empty(path: Path) -> bool:
        descriptor = open_directory_no_follow(path)
        try:
            with os.scandir(descriptor) as entries:
                return next(entries, None) is None
        finally:
            os.close(descriptor)

    def vault_inspect(self, raw_path: str) -> VaultPreviewDto:
        """Inspect one candidate read-only and return a confirmation token."""
        with _translated_errors():
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("Vault path is required")
            path = Path(raw_path.strip()).expanduser().absolute()
            if not os.path.lexists(path):
                safe_path = require_home_path(path)
                token = self._put_token(_VaultPreviewState(safe_path, "create"))
                return VaultPreviewDto(token, "create", str(safe_path))
            root_descriptor = open_directory_no_follow(path)
            try:
                try:
                    safe_path = require_home_path(path)
                except ValueError as home_error:
                    source_kind = self._classify_vault_source_no_follow(path)
                    token = self._put_token(
                        _VaultPreviewState(path, "relocate", source_kind)
                    )
                    return VaultPreviewDto(
                        token,
                        "relocate",
                        str(path),
                        source_kind=source_kind,
                        message=str(home_error),
                    )
                safe_descriptor = open_directory_no_follow(safe_path)
                try:
                    raw_stat = os.fstat(root_descriptor)
                    safe_stat = os.fstat(safe_descriptor)
                    if (
                        raw_stat.st_dev,
                        raw_stat.st_ino,
                    ) != (
                        safe_stat.st_dev,
                        safe_stat.st_ino,
                    ):
                        raise ValueError("Vault root changed during inspection")
                    identity = (raw_stat.st_dev, raw_stat.st_ino)
                finally:
                    os.close(safe_descriptor)
            finally:
                os.close(root_descriptor)
            validate_vault_tree_no_follow(safe_path)
            if self._directory_is_empty(safe_path):
                token = self._put_token(_VaultPreviewState(safe_path, "create"))
                return VaultPreviewDto(token, "create", str(safe_path))
            stage = classify_migration_stage(safe_path)
            if stage == "v01_to_v3":
                migration = self._migration_preflight_v01(safe_path, identity)
                return VaultPreviewDto(
                    migration.token,
                    "migration",
                    str(safe_path),
                    source_kind=_SOURCE_V01,
                    migration=migration,
                    candidate_locator=self._locator_for(safe_path, identity),
                )
            if stage in {"paper_to_v4", "repair_required"}:
                migration = self._migration_preflight_v4(safe_path, identity)
                return VaultPreviewDto(
                    migration.token,
                    "migration",
                    str(safe_path),
                    source_kind=_SOURCE_PAPER,
                    migration=migration,
                    candidate_locator=self._locator_for(safe_path, identity),
                )
            token = self._put_token(_VaultPreviewState(safe_path, "paper"))
            return VaultPreviewDto(
                token,
                "paper",
                str(safe_path),
                paper_count=len(query_index_v4(safe_path)["papers"]),
                source_kind=_SOURCE_PAPER,
                candidate_locator=self._locator_for(safe_path, identity),
            )

    def vault_open(self, preview_token: str) -> StartupDto:
        with _translated_errors():
            preview = self._get_token(preview_token, _VaultPreviewState)
            if preview.kind != "paper":
                raise ValueError("preview does not describe an existing Paper Vault")
            selection = capture_vault_selection_token(preview.path)
            if classify_migration_stage(preview.path) != "ready":
                raise ValueError("Vault changed after inspection")
            set_vault(preview.path, self._config_path, selection)
            self._discard_token(preview_token)
            return self._startup_for_selected(preview.path, selection.root_identity)

    def vault_initialize(self, preview_token: str) -> StartupDto:
        with _translated_errors():
            preview = self._get_token(preview_token, _VaultPreviewState)
            if preview.kind != "create":
                raise ValueError("preview does not describe an empty Vault location")
            path = preview.path
            if os.path.lexists(path):
                validate_vault_tree_no_follow(path)
                if not self._directory_is_empty(path):
                    raise ValueError("target is no longer empty")
            else:
                require_home_path(path)
            init_vault(path)
            safe_vault = require_home_path(path)
            rebuild_index_v4(safe_vault)
            selection = capture_vault_selection_token(safe_vault)
            set_vault(safe_vault, self._config_path, selection)
            self._discard_token(preview_token)
            return self._startup_for_selected(safe_vault, selection.root_identity)

    def vault_relocate(
        self,
        preview_token: str,
        destination_path: str,
    ) -> StartupDto:
        preview = self._get_token(preview_token, _VaultPreviewState)
        if preview.kind != "relocate":
            raise ServiceError(
                "validation_failed",
                "preview does not describe a relocatable Vault",
                "inspect",
            )
        copied: Path | None = None
        try:
            current_kind = self._classify_vault_source_no_follow(preview.path)
            if current_kind != preview.source_kind:
                raise ValueError("source Vault type changed after preview")
            destination = Path(destination_path).expanduser().absolute()
            copied = copy_vault_no_follow(preview.path, destination)
            copied = require_home_path(copied)
            validate_vault_tree_no_follow(copied)
            if self._classify_vault_source_no_follow(copied) != preview.source_kind:
                raise ValueError("copied Vault type differs from the source")
            stage = classify_migration_stage(copied)
            if preview.source_kind == _SOURCE_V01 and stage != "v01_to_v3":
                raise ValueError("copied v0.1 Vault changed during validation")
            if preview.source_kind == _SOURCE_PAPER and stage == "v01_to_v3":
                raise ValueError("copied Paper Vault changed during validation")
            selection = capture_vault_selection_token(copied)
            set_vault(copied, self._config_path, selection)
            result = self._startup_for_selected(copied, selection.root_identity)
            self._discard_token(preview_token)
            return result
        except (OSError, TypeError, ValueError, UnicodeError) as error:
            message = str(error)
            if copied is not None:
                message = f"{message}; verified copy retained at {copied}"
            translated = _service_error(error)
            raise ServiceError(translated.code, message, translated.recovery) from error

    def _migration_preflight_v01(
        self,
        vault: Path,
        root_identity: tuple[int, int],
    ) -> MigrationPreflightDto:
        preflight = inspect_v01_vault(vault)
        token = self._put_token(_MigrationState(vault, root_identity, "v01_to_v3"))
        return self._migration_v01_dto(
            preflight,
            token,
            self._locator_for(vault, root_identity),
        )

    @staticmethod
    def _migration_v01_dto(
        preflight: MigrationPreflight,
        token: str,
        vault_locator: str,
    ) -> MigrationPreflightDto:
        return MigrationPreflightDto(
            token=token,
            kind="v01_to_v3",
            ready=preflight.ready,
            vault_locator=vault_locator,
            backup_path=str(preflight.vault.resolve().parent / "keikeu-backups"),
            cache_count=preflight.cache_count,
            trash_cache_count=preflight.trash_cache_count,
            outline_count=preflight.outline_count,
            trash_outline_count=preflight.trash_outline_count,
            issues=tuple(
                MigrationIssueDto(
                    path=str(issue.path.relative_to(preflight.vault)),
                    message=issue.message,
                )
                for issue in preflight.issues
            ),
        )

    def _migration_preflight_v4(
        self,
        vault: Path,
        root_identity: tuple[int, int],
    ) -> MigrationPreflightDto:
        preflight = inspect_paper_v4_migration(vault)
        token = self._put_token(
            _MigrationState(vault, root_identity, "paper_to_v4", preflight)
        )
        active_count = sum(item.path.parts[0] == "cache" for item in preflight.candidates)
        trash_count = len(preflight.candidates) - active_count
        return MigrationPreflightDto(
            token=token,
            kind="paper_to_v4",
            ready=preflight.ready,
            vault_locator=self._locator_for(vault, root_identity),
            backup_path=str(vault.parent / "keikeu-v4-backups"),
            cache_count=active_count,
            trash_cache_count=trash_count,
            outline_count=0,
            trash_outline_count=0,
            issues=tuple(
                MigrationIssueDto(path=str(issue.path), message=issue.reason)
                for issue in preflight.issues
            ),
        )

    def migration_preflight(self) -> MigrationPreflightDto:
        with _translated_errors():
            vault = self._require_vault()
            _vault, identity = self._pin_home_vault_root(
                vault,
                self._root_identity,
            )
            stage = classify_migration_stage(vault)
            if stage == "v01_to_v3":
                return self._migration_preflight_v01(vault, identity)
            if stage in {"paper_to_v4", "repair_required"}:
                return self._migration_preflight_v4(vault, identity)
            raise ValueError("active Vault does not require migration")

    def migration_run(self, preflight_token: str) -> MigrationResultDto:
        with _translated_errors():
            state = self._get_token(preflight_token, _MigrationState)
            if state.kind == "v01_to_v3":
                result = migrate_v01_vault(
                    state.path,
                    expected_root_identity=state.root_identity,
                )
                selection = capture_vault_selection_token(state.path)
                migration_result = MigrationResultDto(
                    kind=state.kind,
                    converted_count=result.converted_count,
                    backup_path=str(result.backup_path),
                    report_path=str(result.report_path),
                    paper_paths=tuple(
                        str(path.relative_to(state.path)) for path in result.paper_paths
                    ),
                )
            else:
                if state.preflight_v4 is None:
                    raise ValueError("Paper migration preflight is unavailable")
                result_v4 = migrate_papers_to_v4(state.path, state.preflight_v4)
                selection = capture_vault_selection_token(state.path)
                migration_result = MigrationResultDto(
                    kind=state.kind,
                    converted_count=result_v4.converted_count,
                    backup_path=str(result_v4.backup_path),
                    report_path=str(result_v4.report_path),
                    warnings=result_v4.warnings,
                )
            set_vault(state.path, self._config_path, selection)
            self._active_vault = state.path
            self._root_identity = selection.root_identity
            self._discard_token(preflight_token)
            return migration_result

    @staticmethod
    def _editable_from_paper(paper: PaperV4) -> PaperEditableDto:
        return PaperEditableDto(
            display_name=paper.display_name,
            tags=tuple(paper.tags),
            pages=tuple(
                CardPageDto(page.name, page.content, page.type) for page in paper.pages
            ),
        )

    def _paper_dto(
        self,
        token: str,
        state: _PaperEditState,
        editable: PaperEditableDto | None = None,
    ) -> PaperDto:
        paper = state.paper
        projection = editable or (
            self._editable_from_paper(paper)
            if paper is not None
            else PaperEditableDto(None, (), (CardPageDto(None, "", None),))
        )
        updated = paper.updated if paper is not None else state.created
        return PaperDto(
            path=str(state.path) if state.path is not None else None,
            edit_token=token,
            code=state.code,
            display_name=projection.display_name,
            tags=projection.tags,
            pages=projection.pages,
            created=state.created.isoformat(),
            updated=updated.isoformat(),
            vault_locator=self._vault_locator(),
            target_path=str(state.target_path),
            source_digest=(
                hashlib.sha256(state.source_bytes).hexdigest()
                if state.source_bytes is not None
                else None
            ),
        )

    @staticmethod
    def _paper_from_editable(
        state: _PaperEditState,
        editable: PaperEditableDto,
        *,
        updated: datetime,
    ) -> PaperV4:
        existing = state.paper
        return PaperV4(
            code=state.code,
            display_name=editable.display_name,
            tags=list(editable.tags),
            pages=[
                CardPageV4(name=page.name, content=page.content, type=page.type)
                for page in editable.pages
            ],
            created=state.created,
            updated=updated,
            legacy_title=existing.legacy_title if existing is not None else None,
            extra_frontmatter=(
                existing.extra_frontmatter.copy() if existing is not None else {}
            ),
        )

    def paper_create_draft(self) -> PaperDto:
        with _translated_errors():
            vault = self._require_vault()
            created = datetime.now()
            code = next_paper_code(vault, created)
            state = _PaperEditState(
                path=None,
                paper=None,
                source_bytes=None,
                code=code,
                created=created,
                target_path=Path("cache") / f"{code}.md",
            )
            token = self._put_token(state)
            return self._paper_dto(token, state)

    def paper_open(self, relative_path: str) -> PaperOpenResultDto:
        with _translated_errors():
            vault = self._require_vault()
            path = resolve_active_paper_path(vault, relative_path)
            relative = path.relative_to(vault)
            try:
                paper, source_bytes = read_paper_v4_snapshot(path)
                if relative.name != f"{paper.code}.md":
                    raise ValueError("Paper filename and frontmatter code do not match")
            except (ValueError, UnicodeError) as error:
                return PaperOpenResultDto(
                    state="repair_required",
                    repair=RepairDto("open", str(relative), str(error)),
                )
            state = _PaperEditState(
                path=relative,
                paper=paper,
                source_bytes=source_bytes,
                code=paper.code,
                created=paper.created,
                target_path=relative,
            )
            token = self._put_token(state)
            return PaperOpenResultDto(state="opened", paper=self._paper_dto(token, state))

    def paper_save(self, request: PaperSaveDto) -> PaperSaveResultDto:
        if not isinstance(request, PaperSaveDto):
            raise ServiceError(
                "invalid_request",
                "paper save requires PaperSaveDto",
                "correct_input",
            )
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(request.vault_locator)
            state = self._get_token(request.edit_token, _PaperEditState)
            editable = PaperEditableDto(
                request.display_name,
                request.tags,
                request.pages,
            )
            paper = self._paper_from_editable(state, editable, updated=datetime.now())
            if state.path is None:
                resolve_active_paper_path(vault, state.target_path, must_exist=False)
                path = write_paper_v4(vault, paper, destination=state.target_path)
            else:
                path = resolve_active_paper_path(vault, state.path)
                if state.source_bytes is None:
                    raise ValueError("Paper source snapshot is unavailable")
                try:
                    replace_paper_v4_bytes(
                        vault,
                        state.path,
                        render_paper_v4_bytes(paper),
                        expected_source_bytes=state.source_bytes,
                    )
                except ValueError as error:
                    if "Paper changed externally; update refused" in str(error):
                        raise ServiceError(
                            "stale_snapshot",
                            str(error),
                            "reopen",
                        ) from error
                    raise
            try:
                stored, source_bytes = read_paper_v4_snapshot(path)
            except (OSError, ValueError, UnicodeError) as error:
                raise ServiceError(
                    "commit_unknown",
                    f"saved Paper could not be verified: {error}",
                    "restart_then_reconcile",
                ) from error
            state.path = path.relative_to(vault)
            state.target_path = state.path
            state.paper = stored
            state.source_bytes = source_bytes
            warnings: tuple[str, ...] = ()
            try:
                rebuild_index_v4(vault)
            except (OSError, ValueError, UnicodeError):
                warnings = ("index_degraded",)
            return PaperSaveResultDto(self._paper_dto(request.edit_token, state), warnings)

    @staticmethod
    def _entry_paths_for_code(vault: Path, code: str) -> set[str]:
        paths: set[str] = set()
        for result in (query_index_v4(vault), query_trash_v4(vault)):
            for entry in result["papers"]:
                if isinstance(entry, dict) and entry.get("code") == code:
                    path = entry.get("path")
                    if isinstance(path, str):
                        paths.add(path)
        return paths

    def paper_reconcile_save(
        self,
        request: PaperReconcileRequestDto,
    ) -> PaperReconcileResultDto:
        if not isinstance(request, PaperReconcileRequestDto):
            raise ServiceError(
                "invalid_request",
                "paper reconcile requires PaperReconcileRequestDto",
                "correct_input",
            )
        with _translated_errors():
            vault = self._require_vault()
            if request.vault_locator != self._vault_locator():
                return PaperReconcileResultDto(
                    state="stale",
                    stale_reason="vault_changed",
                    index_state="not_checked",
                )
            if (request.source_digest is None) != (request.baseline is None):
                raise ValueError("baseline and source_digest must both be null or non-null")
            try:
                created = datetime.fromisoformat(request.created)
            except ValueError:
                raise ValueError("created must be an ISO datetime") from None
            target = resolve_active_paper_path(
                vault,
                request.target_path,
                must_exist=False,
            )
            relative = target.relative_to(vault)
            if relative.name != f"{request.code}.md":
                raise ValueError("target_path filename must match code")
            index_state = self._index_state(vault)
            if not os.path.lexists(target):
                if request.source_digest is not None:
                    return PaperReconcileResultDto(
                        state="stale",
                        stale_reason="missing_existing",
                        index_state=index_state,
                    )
                if self._entry_paths_for_code(vault, request.code):
                    return PaperReconcileResultDto(
                        state="stale",
                        stale_reason="duplicate_code",
                        index_state=index_state,
                    )
                state = _PaperEditState(
                    path=None,
                    paper=None,
                    source_bytes=None,
                    code=request.code,
                    created=created,
                    target_path=relative,
                )
                token = self._put_token(state)
                return PaperReconcileResultDto(
                    state="not_committed",
                    paper=self._paper_dto(token, state, request.submitted),
                    index_state=index_state,
                )
            try:
                disk_paper, disk_bytes = read_paper_v4_snapshot(target)
            except (OSError, ValueError, UnicodeError) as error:
                return PaperReconcileResultDto(
                    state="repair_required",
                    repair=RepairDto(
                        "unknown_save",
                        str(relative),
                        str(error),
                    ),
                    index_state=index_state,
                )
            if disk_paper.code != request.code or disk_paper.created != created:
                return PaperReconcileResultDto(
                    state="stale",
                    stale_reason="identity_changed",
                    index_state=index_state,
                )
            code_paths = self._entry_paths_for_code(vault, request.code)
            if code_paths - {str(relative)}:
                return PaperReconcileResultDto(
                    state="stale",
                    stale_reason="duplicate_code",
                    index_state=index_state,
                )
            disk_digest = hashlib.sha256(disk_bytes).hexdigest()
            if request.source_digest == disk_digest:
                state = _PaperEditState(
                    path=relative,
                    paper=disk_paper,
                    source_bytes=disk_bytes,
                    code=disk_paper.code,
                    created=disk_paper.created,
                    target_path=relative,
                )
                token = self._put_token(state)
                return PaperReconcileResultDto(
                    state="not_committed",
                    paper=self._paper_dto(token, state, request.submitted),
                    index_state=index_state,
                )
            state = _PaperEditState(
                path=relative,
                paper=disk_paper,
                source_bytes=disk_bytes,
                code=disk_paper.code,
                created=disk_paper.created,
                target_path=relative,
            )
            try:
                submitted = self._editable_from_paper(
                    self._paper_from_editable(
                        state,
                        request.submitted,
                        updated=disk_paper.updated,
                    )
                )
            except ValueError:
                return PaperReconcileResultDto(
                    state="stale",
                    stale_reason="submitted_invalid",
                    index_state=index_state,
                )
            if submitted != self._editable_from_paper(disk_paper):
                return PaperReconcileResultDto(
                    state="stale",
                    stale_reason="third_content",
                    index_state=index_state,
                )
            token = self._put_token(state)
            return PaperReconcileResultDto(
                state="committed",
                paper=self._paper_dto(token, state),
                index_state=index_state,
            )

    def paper_soft_delete(
        self,
        edit_token: str,
        vault_locator: str,
    ) -> OperationReportResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            state = self._get_token(edit_token, _PaperEditState)
            if state.path is None:
                raise ValueError("unsaved Paper cannot be deleted")
            reports = soft_delete_papers(vault, [state.path])
            report = self._operation_dto(reports[0])
            if report.succeeded:
                self._discard_token(edit_token)
            warnings: tuple[str, ...] = ()
            try:
                rebuild_index_v4(vault)
            except (OSError, ValueError, UnicodeError):
                warnings = ("index_degraded",)
            return OperationReportResultDto(report, warnings)

    @staticmethod
    def _text_key(value: str) -> str:
        return unicodedata.normalize("NFC", value).casefold()

    @classmethod
    def _entry_from_index(
        cls,
        entry: dict[str, object],
        *,
        trashed: bool = False,
    ) -> LibraryEntryDto:
        path = entry.get("path")
        code = entry.get("code")
        if not isinstance(path, str) or not isinstance(code, str):
            raise ValueError("index Paper entry is malformed")
        display_name = entry.get("display_name")
        folder = entry.get("folder")
        return LibraryEntryDto(
            path=path,
            code=code,
            display_name=display_name if isinstance(display_name, str) else None,
            folder=folder if isinstance(folder, str) else None,
            tags=tuple(
                item for item in entry.get("tags", []) if isinstance(item, str)
            ),
            preview=str(entry.get("preview", "")),
            page_count=(
                entry["page_count"] if type(entry.get("page_count")) is int else 0
            ),
            page_names=tuple(
                item
                for item in entry.get("page_names", [])
                if isinstance(item, str)
            ),
            created=(entry["created"] if isinstance(entry.get("created"), str) else None),
            updated=(entry["updated"] if isinstance(entry.get("updated"), str) else None),
            trashed=trashed,
            repair_reason=(
                entry["repair_reason"]
                if isinstance(entry.get("repair_reason"), str)
                else None
            ),
        )

    @classmethod
    def _sort_entries(
        cls,
        entries: Iterable[LibraryEntryDto],
        mode: str,
    ) -> list[LibraryEntryDto]:
        records = list(entries)
        if mode == "name":
            return sorted(
                records,
                key=lambda entry: (
                    cls._text_key(entry.display_name or entry.code),
                    entry.code,
                    entry.path,
                ),
            )
        if mode == "created_asc":
            return sorted(records, key=lambda entry: (entry.created or "", entry.path))
        field = "created" if mode == "created_desc" else "updated"
        return sorted(
            records,
            key=lambda entry: (getattr(entry, field) or "", entry.path),
            reverse=True,
        )

    def library_query(
        self,
        *,
        scope: str = _SCOPE_ALL,
        search: str = "",
        sort: str = "updated_desc",
        verify_index: bool = False,
    ) -> LibraryViewDto:
        with _translated_errors():
            vault = self._require_vault()
            if sort not in _SORT_MODES:
                raise ValueError(f"unsupported Library sort: {sort}")
            folders = tuple(list_active_folders(vault))
            trash_folders = tuple(list_trashed_folders(vault))
            if scope.startswith(_FOLDER_PREFIX):
                requested_folder = scope[len(_FOLDER_PREFIX) :]
                if requested_folder not in folders:
                    scope = _SCOPE_ALL
            elif scope not in {_SCOPE_ALL, _SCOPE_UNFILED, _SCOPE_TRASH}:
                raise ValueError(f"unsupported Library scope: {scope}")
            if scope == _SCOPE_TRASH:
                projection = query_trash_v4(vault, search)
            elif scope == _SCOPE_UNFILED:
                projection = query_index_v4(vault, search)
            elif scope.startswith(_FOLDER_PREFIX):
                projection = query_index_v4(vault, search)
            else:
                projection = query_index_v4(vault, search)
            scoped = [
                self._entry_from_index(entry, trashed=scope == _SCOPE_TRASH)
                for entry in projection["papers"]
                if isinstance(entry, dict)
            ]
            if scope == _SCOPE_UNFILED:
                scoped = [entry for entry in scoped if entry.folder is None]
            elif scope.startswith(_FOLDER_PREFIX):
                folder = scope[len(_FOLDER_PREFIX) :]
                scoped = [entry for entry in scoped if entry.folder == folder]
            errors = tuple(
                IndexErrorDto(
                    path=str(error.get("path", "")),
                    reason=str(error.get("reason", "")),
                )
                for error in projection["errors"]
                if isinstance(error, dict)
            )
            index_state = self._index_state(vault)
            if verify_index and index_state == "current" and not verify_index_v4(vault):
                index_state = "degraded"
            return LibraryViewDto(
                scope=scope,
                entries=tuple(self._sort_entries(scoped, sort)),
                folders=folders,
                trash_folders=trash_folders,
                trash_count=len(query_trash_v4(vault)["papers"]),
                errors=errors,
                vault_locator=self._vault_locator(),
                index_state=index_state,
            )

    def library_rebuild(self, vault_locator: str) -> LibraryViewDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            rebuild_index_v4(vault)
            if not verify_index_v4(vault):
                raise ValueError("Index v4 verification failed after rebuild")
            return self.library_query(verify_index=True)

    @staticmethod
    def _operation_dto(result: PathOperationResult) -> OperationReportDto:
        return OperationReportDto(
            source=str(result.source),
            destination=(
                str(result.destination) if result.destination is not None else None
            ),
            error=result.error,
        )

    @staticmethod
    def _index_warnings_after_mutation(vault: Path) -> tuple[str, ...]:
        try:
            rebuild_index_v4(vault)
        except (OSError, ValueError, UnicodeError):
            return ("index_degraded",)
        return ()

    def _reports_after_rebuild(
        self,
        vault: Path,
        reports: Iterable[PathOperationResult],
    ) -> OperationReportsResultDto:
        records = tuple(self._operation_dto(report) for report in reports)
        return OperationReportsResultDto(
            records,
            self._index_warnings_after_mutation(vault),
        )

    def library_move(
        self,
        paths: Iterable[str],
        destination_folder: str | None,
        vault_locator: str,
    ) -> OperationReportsResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            return self._reports_after_rebuild(
                vault,
                move_papers(vault, list(paths), destination_folder),
            )

    def library_branch(
        self,
        relative_path: str,
        vault_locator: str,
    ) -> OperationReportResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            source = resolve_active_paper_path(vault, relative_path)
            _paper, source_bytes = read_paper_v4_snapshot(source)
            code = next_paper_code(vault)
            destination = source.relative_to(vault).parent / f"{code}.md"
            branch_paper_v4(
                vault,
                source.relative_to(vault),
                destination,
                code,
                expected_source_bytes=source_bytes,
            )
            return OperationReportResultDto(
                OperationReportDto(
                    source=str(source.relative_to(vault)),
                    destination=str(destination),
                    error=None,
                ),
                self._index_warnings_after_mutation(vault),
            )

    def library_soft_delete(
        self,
        paths: Iterable[str],
        vault_locator: str,
    ) -> OperationReportsResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            return self._reports_after_rebuild(
                vault,
                soft_delete_papers(vault, list(paths)),
            )

    def library_restore(
        self,
        paths: Iterable[str],
        vault_locator: str,
    ) -> OperationReportsResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            return self._reports_after_rebuild(
                vault,
                restore_papers(vault, [Path(path) for path in paths]),
            )

    def library_permanently_delete(
        self,
        paths: Iterable[str],
        vault_locator: str,
    ) -> OperationReportsResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            return self._reports_after_rebuild(
                vault,
                permanently_delete_papers(vault, [Path(path) for path in paths]),
            )

    def library_create_folder(self, name: str, vault_locator: str) -> NameResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            created = create_folder(vault, name)
            return NameResultDto(
                created.name,
                self._index_warnings_after_mutation(vault),
            )

    def library_rename_folder(
        self,
        folder: str,
        new_name: str,
        vault_locator: str,
    ) -> NameResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            renamed = rename_folder(vault, folder, new_name)
            return NameResultDto(
                renamed.name,
                self._index_warnings_after_mutation(vault),
            )

    def library_merge_folders(
        self,
        source: str,
        destination: str,
        vault_locator: str,
    ) -> OperationReportsResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            return self._reports_after_rebuild(
                vault,
                merge_folders(vault, source, destination),
            )

    def library_soft_delete_folder(
        self,
        folder: str,
        vault_locator: str,
    ) -> OperationReportsResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            return self._reports_after_rebuild(
                vault,
                soft_delete_folder(vault, folder),
            )

    def library_restore_folder(
        self,
        folder: str,
        vault_locator: str,
    ) -> OperationReportsResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            return self._reports_after_rebuild(
                vault,
                restore_folder(vault, folder),
            )

    def library_permanently_delete_folder(
        self,
        folder: str,
        vault_locator: str,
    ) -> OperationReportResultDto:
        with _translated_errors():
            vault = self._require_vault()
            self._require_locator(vault_locator)
            result = permanently_delete_folder(vault, folder)
            return OperationReportResultDto(
                self._operation_dto(result),
                self._index_warnings_after_mutation(vault),
            )

    def resolve_system_target(self, action: str, relative_target: str) -> Path:
        """Return one Python-validated absolute path for immediate Rust use."""
        with _translated_errors():
            if action not in {"open", "reveal"}:
                raise ValueError(f"unsupported system action: {action}")
            vault = self._require_vault()
            if relative_target == ".":
                validate_vault_tree_no_follow(vault)
                return vault
            return resolve_active_paper_path(vault, relative_target)
