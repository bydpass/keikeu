"""Concrete application service shared by desktop presentation adapters."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import secrets
from typing import Iterator, Iterable, TypeVar, cast
import unicodedata

from keikeu_bridge.dto import (
    FlashcardDeckDto,
    FlashcardDto,
    HighlightDto,
    IndexErrorDto,
    LibraryEntryDto,
    LibraryViewDto,
    MigrationIssueDto,
    MigrationPreflightDto,
    MigrationResultDto,
    OperationReportDto,
    PaperDto,
    PaperOptionDto,
    PaperSaveDto,
    StartupDto,
    VaultPreviewDto,
)
from keikeu_bridge.local_state import claim_daily_card
from keikeu_core.indexer import list_index_errors, list_papers, rebuild_index
from keikeu_core.markdown_io import (
    branch_paper,
    read_paper_snapshot,
    update_paper,
    write_paper,
)
from keikeu_core.migration_v01 import (
    MigrationPreflight,
    MigrationPreflightError,
    inspect_v01_vault,
    is_v01_vault,
    migrate_v01_vault,
)
from keikeu_core.models import Highlight, Paper
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
    validate_vault_papers,
    validate_vault_tree_no_follow,
    vault_index_version,
)

__all__ = ["KeikeuService", "ServiceError"]


_SOURCE_V01 = "v0.1"
_SOURCE_PAPER = "Paper v2/v3"
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
    paper: Paper | None
    source_bytes: bytes | None
    code: str
    created: datetime


@dataclass(frozen=True)
class _VaultPreviewState:
    path: Path
    kind: str
    source_kind: str = ""


@dataclass(frozen=True)
class _MigrationState:
    path: Path
    root_identity: tuple[int, int]


_TokenState = TypeVar("_TokenState")


class KeikeuService:
    """Own UI-neutral workflow orchestration for one local app process."""

    def __init__(self, *, config_path: Path, state_path: Path) -> None:
        self._config_path = config_path
        self._state_path = state_path
        self._active_vault: Path | None = None
        self._root_identity: tuple[int, int] | None = None
        self._tokens: dict[str, object] = {}

    @property
    def active_vault(self) -> Path | None:
        """Return the active path for the in-process Flet adapter only."""
        return self._active_vault

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
        if version in {2, 3}:
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
        raise ValueError("folder is not a supported v0.1 or Paper v2/v3 Vault")

    @classmethod
    def _classify_configured_home_vault(cls, source: Path) -> str:
        version = vault_index_version(source)
        if version in {2, 3}:
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
        raise ValueError("folder is not a supported v0.1 or Paper v2/v3 Vault")

    @classmethod
    def _validated_rebuild(
        cls,
        vault: Path,
        *,
        require_clean_papers: bool = True,
    ) -> VaultSelectionToken:
        before = capture_vault_selection_token(vault)
        if cls._classify_vault_source_no_follow(vault) != _SOURCE_PAPER:
            raise ValueError("Vault changed before confirmation")
        validate_vault_tree_no_follow(vault)
        if require_clean_papers:
            validate_vault_papers(vault)
        index = rebuild_index(vault)
        errors = index.get("errors")
        if not isinstance(errors, list):
            raise ValueError("index rebuild did not return an errors list")
        if errors and require_clean_papers:
            raise ValueError(f"Vault has {len(errors)} invalid Papers")
        if cls._classify_vault_source_no_follow(vault) != _SOURCE_PAPER:
            raise ValueError("Vault changed during index rebuild")
        final = capture_vault_selection_token(vault)
        if final.path != before.path or final.root_identity != before.root_identity:
            raise ValueError("Vault root changed during validation")
        return final

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
        return StartupDto(state="ready", show_daily_card=show_daily)

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
            source_kind = self._classify_configured_home_vault(safe_vault)
            safe_vault, identity = self._pin_home_vault_root(
                safe_vault,
                identity,
            )
            if source_kind == _SOURCE_V01:
                self._active_vault = safe_vault
                self._root_identity = identity
                migration = self._migration_preflight(safe_vault, identity)
                return StartupDto(state="migration", migration=migration)
            return self._activate(safe_vault, identity)
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

    def activate_existing_vault(
        self,
        vault: Path,
        *,
        expected_root_identity: tuple[int, int] | None = None,
        claim_daily: bool = False,
        require_clean_papers: bool = False,
    ) -> StartupDto:
        """Attach the accepted Flet adapter to one selected Paper Vault."""
        with _translated_errors():
            safe_vault, identity = self._pin_home_vault_root(
                vault,
                expected_root_identity,
            )
            if require_clean_papers:
                selection = self._validated_rebuild(safe_vault)
                identity = selection.root_identity
            elif self._classify_configured_home_vault(safe_vault) != _SOURCE_PAPER:
                raise ValueError("selected Vault is not a Paper v2/v3 Vault")
            return self._activate(
                safe_vault,
                identity,
                claim_daily=claim_daily,
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
            source_kind = self._classify_vault_source_no_follow(safe_path)
            if source_kind == _SOURCE_V01:
                migration = self._migration_preflight(safe_path, identity)
                return VaultPreviewDto(
                    migration.token,
                    "migration",
                    str(safe_path),
                    source_kind=source_kind,
                    migration=migration,
                )
            token = self._put_token(_VaultPreviewState(safe_path, "paper"))
            return VaultPreviewDto(
                token,
                "paper",
                str(safe_path),
                paper_count=len(list_active_papers(safe_path)),
                source_kind=source_kind,
            )

    def vault_open(self, preview_token: str) -> StartupDto:
        with _translated_errors():
            preview = self._get_token(preview_token, _VaultPreviewState)
            if preview.kind != "paper":
                raise ValueError("preview does not describe an existing Paper Vault")
            selection = self._validated_rebuild(
                preview.path,
                require_clean_papers=False,
            )
            set_vault(preview.path, self._config_path, selection)
            self._discard_token(preview_token)
            return self._activate(preview.path, selection.root_identity)

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
            selection = self._validated_rebuild(safe_vault)
            set_vault(safe_vault, self._config_path, selection)
            self._discard_token(preview_token)
            return self._activate(safe_vault, selection.root_identity)

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
            if preview.source_kind == _SOURCE_V01:
                selection = self._validated_v01_selection(copied)
                set_vault(copied, self._config_path, selection)
                self._active_vault = copied
                self._root_identity = selection.root_identity
                migration = self._migration_preflight(
                    copied,
                    selection.root_identity,
                )
                result = StartupDto(state="migration", migration=migration)
            else:
                selection = self._validated_rebuild(copied)
                set_vault(copied, self._config_path, selection)
                result = self._activate(copied, selection.root_identity)
            self._discard_token(preview_token)
            return result
        except (OSError, TypeError, ValueError, UnicodeError) as error:
            message = str(error)
            if copied is not None:
                message = f"{message}; verified copy retained at {copied}"
            translated = _service_error(error)
            raise ServiceError(translated.code, message, translated.recovery) from error

    def _migration_preflight(
        self,
        vault: Path,
        root_identity: tuple[int, int],
    ) -> MigrationPreflightDto:
        preflight = inspect_v01_vault(vault)
        token = self._put_token(_MigrationState(vault, root_identity))
        return self._migration_dto(preflight, token)

    @staticmethod
    def _migration_dto(
        preflight: MigrationPreflight,
        token: str,
    ) -> MigrationPreflightDto:
        return MigrationPreflightDto(
            token=token,
            ready=preflight.ready,
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

    def migration_preflight(self) -> MigrationPreflightDto:
        with _translated_errors():
            vault = self._require_vault()
            if self._classify_vault_source_no_follow(vault) != _SOURCE_V01:
                raise ValueError("active Vault is not a v0.1 migration source")
            _vault, identity = self._pin_home_vault_root(
                vault,
                self._root_identity,
            )
            return self._migration_preflight(vault, identity)

    def migration_run(self, preflight_token: str) -> MigrationResultDto:
        with _translated_errors():
            state = self._get_token(preflight_token, _MigrationState)
            result = migrate_v01_vault(
                state.path,
                expected_root_identity=state.root_identity,
            )
            selection = self._validated_rebuild(state.path)
            set_vault(state.path, self._config_path, selection)
            self._active_vault = state.path
            self._root_identity = selection.root_identity
            self._discard_token(preflight_token)
            return MigrationResultDto(
                converted_count=result.converted_count,
                backup_path=str(result.backup_path),
                report_path=str(result.report_path),
                paper_paths=tuple(
                    str(path.relative_to(state.path)) for path in result.paper_paths
                ),
            )

    @staticmethod
    def _paper_dto(token: str, state: _PaperEditState) -> PaperDto:
        paper = state.paper
        if paper is None:
            return PaperDto(
                path=None,
                edit_token=token,
                code=state.code,
                display_name=None,
                initial_summary="",
                summary="",
                highlights=(),
                tags=(),
                created=state.created.isoformat(),
                updated=state.created.isoformat(),
            )
        return PaperDto(
            path=str(state.path) if state.path is not None else None,
            edit_token=token,
            code=paper.code,
            display_name=paper.display_name,
            initial_summary=paper.initial_summary,
            summary=paper.summary,
            highlights=tuple(
                HighlightDto(highlight.display_name, highlight.content)
                for highlight in paper.highlights
            ),
            tags=tuple(paper.tags),
            created=paper.created.isoformat(),
            updated=paper.updated.isoformat(),
        )

    def paper_create_draft(self) -> PaperDto:
        with _translated_errors():
            vault = self._require_vault()
            created = datetime.now()
            state = _PaperEditState(
                path=None,
                paper=None,
                source_bytes=None,
                code=next_paper_code(vault, created),
                created=created,
            )
            token = self._put_token(state)
            return self._paper_dto(token, state)

    def paper_open(self, relative_path: str) -> PaperDto:
        with _translated_errors():
            vault = self._require_vault()
            path = resolve_active_paper_path(vault, relative_path)
            paper, source_bytes = read_paper_snapshot(path)
            state = _PaperEditState(
                path=path.relative_to(vault),
                paper=paper,
                source_bytes=source_bytes,
                code=paper.code,
                created=paper.created,
            )
            token = self._put_token(state)
            return self._paper_dto(token, state)

    def paper_save(self, request: PaperSaveDto) -> PaperDto:
        if not isinstance(request, PaperSaveDto):
            raise ServiceError(
                "invalid_request",
                "paper save requires PaperSaveDto",
                "correct_input",
            )
        with _translated_errors():
            vault = self._require_vault()
            state = self._get_token(request.edit_token, _PaperEditState)
            if not request.summary.strip():
                raise ValueError("Summary must not be blank")
            existing = state.paper
            paper = Paper(
                code=state.code,
                initial_summary=existing.initial_summary if existing is not None else "",
                summary=request.summary,
                display_name=request.display_name,
                highlights=[
                    Highlight(item.content, item.display_name)
                    for item in request.highlights
                ],
                tags=list(request.tags),
                created=existing.created if existing is not None else state.created,
                updated=datetime.now(),
                legacy_title=existing.legacy_title if existing is not None else None,
                extra_frontmatter=(
                    existing.extra_frontmatter.copy() if existing is not None else {}
                ),
            )
            if state.path is None:
                destination = Path("cache") / f"{paper.code}.md"
                resolve_active_paper_path(vault, destination, must_exist=False)
                path = write_paper(vault, paper, destination=destination)
            else:
                path = resolve_active_paper_path(vault, state.path)
                if state.source_bytes is None:
                    raise ValueError("Paper source snapshot is unavailable")
                try:
                    update_paper(
                        vault,
                        state.path,
                        paper,
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
            stored, source_bytes = read_paper_snapshot(path)
            state.path = path.relative_to(vault)
            state.paper = stored
            state.source_bytes = source_bytes
            rebuild_index(vault)
            return self._paper_dto(request.edit_token, state)

    def paper_soft_delete(self, edit_token: str) -> OperationReportDto:
        with _translated_errors():
            vault = self._require_vault()
            state = self._get_token(edit_token, _PaperEditState)
            if state.path is None:
                raise ValueError("unsaved Paper cannot be deleted")
            reports = soft_delete_papers(vault, [state.path])
            rebuild_index(vault)
            report = self._operation_dto(reports[0])
            if report.succeeded:
                self._discard_token(edit_token)
            return report

    def flashcard_open(self, relative_path: str | None = None) -> FlashcardDeckDto:
        with _translated_errors():
            vault = self._require_vault()
            raw_entries = rebuild_index(vault).get("papers")
            entries = raw_entries if isinstance(raw_entries, list) else []
            if relative_path is None:
                if not entries:
                    raise FileNotFoundError("Vault has no readable Paper")
                first_path = entries[0].get("path")
                if not isinstance(first_path, str):
                    raise FileNotFoundError("Vault has no readable Paper")
                relative_path = first_path
            path = resolve_active_paper_path(vault, relative_path)
            paper, _source_bytes = read_paper_snapshot(path)
            if path.stem != paper.code:
                raise ValueError("Paper filename and frontmatter code do not match")
            options = sorted(
                (
                    self._paper_option(entry)
                    for entry in entries
                    if isinstance(entry, dict)
                ),
                key=lambda option: (
                    self._text_key(option.label),
                    option.path,
                ),
            )
            titles = (
                "Summary",
                *(
                    highlight.display_name or f"Highlight {index}"
                    for index, highlight in enumerate(paper.highlights, start=1)
                ),
            )
            contents = (paper.summary, *(item.content for item in paper.highlights))
            return FlashcardDeckDto(
                path=str(path.relative_to(vault)),
                paper_label=self._paper_label(paper),
                cards=tuple(
                    FlashcardDto(title, content)
                    for title, content in zip(titles, contents, strict=True)
                ),
                options=tuple(options),
            )

    @staticmethod
    def _paper_label(paper: Paper) -> str:
        if paper.display_name is None:
            return paper.code
        return f"{paper.display_name} ({paper.code})"

    @staticmethod
    def _paper_option(entry: dict[str, object]) -> PaperOptionDto:
        path = entry.get("path")
        code = entry.get("code")
        if not isinstance(path, str) or not isinstance(code, str):
            raise ValueError("index Paper option is malformed")
        display_name = entry.get("display_name")
        name = display_name if isinstance(display_name, str) and display_name else None
        label = f"{name} ({code})" if name is not None else code
        return PaperOptionDto(path, code, name, label)

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
            summary=str(entry.get("summary", "")),
            tags=tuple(
                item for item in entry.get("tags", []) if isinstance(item, str)
            ),
            highlight_names=tuple(
                item
                for item in entry.get("highlight_names", [])
                if isinstance(item, str)
            ),
            created=str(entry.get("created", "")),
            updated=str(entry.get("updated", "")),
            trashed=trashed,
        )

    @classmethod
    def _trash_entry(cls, vault: Path, path: Path) -> LibraryEntryDto:
        try:
            paper, _source_bytes = read_paper_snapshot(vault / path)
        except (OSError, ValueError, UnicodeError):
            return LibraryEntryDto(
                path=str(path),
                code=path.stem,
                display_name=None,
                folder=path.parts[2] if len(path.parts) == 4 else None,
                summary="",
                tags=(),
                highlight_names=(),
                created="",
                updated="",
                trashed=True,
            )
        return LibraryEntryDto(
            path=str(path),
            code=paper.code,
            display_name=paper.display_name,
            folder=path.parts[2] if len(path.parts) == 4 else None,
            summary=paper.summary,
            tags=tuple(paper.tags),
            highlight_names=tuple(
                item.display_name
                for item in paper.highlights
                if item.display_name is not None
            ),
            created=paper.created.isoformat(),
            updated=paper.updated.isoformat(),
            trashed=True,
        )

    @classmethod
    def _entry_search_text(cls, entry: LibraryEntryDto) -> str:
        return cls._text_key(
            " ".join(
                (
                    entry.display_name or "",
                    entry.code,
                    entry.summary,
                    *entry.tags,
                    *entry.highlight_names,
                )
            )
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
            return sorted(records, key=lambda entry: (entry.created, entry.path))
        field = "created" if mode == "created_desc" else "updated"
        return sorted(
            records,
            key=lambda entry: (getattr(entry, field), entry.path),
            reverse=True,
        )

    def library_query(
        self,
        *,
        scope: str = _SCOPE_ALL,
        search: str = "",
        sort: str = "updated_desc",
        rebuild: bool = False,
    ) -> LibraryViewDto:
        with _translated_errors():
            vault = self._require_vault()
            if sort not in _SORT_MODES:
                raise ValueError(f"unsupported Library sort: {sort}")
            if rebuild:
                rebuild_index(vault)
            entries = tuple(
                self._entry_from_index(entry)
                for entry in list_papers(vault)
                if isinstance(entry, dict)
            )
            folders = tuple(list_active_folders(vault))
            trash_paths = tuple(list_trashed_papers(vault))
            trash_folders = tuple(list_trashed_folders(vault))
            if scope.startswith(_FOLDER_PREFIX):
                requested_folder = scope[len(_FOLDER_PREFIX) :]
                if requested_folder not in folders:
                    scope = _SCOPE_ALL
            elif scope not in {_SCOPE_ALL, _SCOPE_UNFILED, _SCOPE_TRASH}:
                raise ValueError(f"unsupported Library scope: {scope}")
            if scope == _SCOPE_TRASH:
                scoped = [self._trash_entry(vault, path) for path in trash_paths]
            elif scope == _SCOPE_UNFILED:
                scoped = [entry for entry in entries if entry.folder is None]
            elif scope.startswith(_FOLDER_PREFIX):
                folder = scope[len(_FOLDER_PREFIX) :]
                scoped = [entry for entry in entries if entry.folder == folder]
            else:
                scoped = list(entries)
            query = self._text_key(search.strip())
            if query:
                scoped = [
                    entry
                    for entry in scoped
                    if query in self._entry_search_text(entry)
                ]
            errors = tuple(
                IndexErrorDto(
                    path=str(error.get("path", "")),
                    reason=str(error.get("reason", "")),
                )
                for error in list_index_errors(vault)
                if isinstance(error, dict)
            )
            return LibraryViewDto(
                scope=scope,
                entries=tuple(self._sort_entries(scoped, sort)),
                folders=folders,
                trash_folders=trash_folders,
                trash_count=len(trash_paths),
                errors=errors,
            )

    @staticmethod
    def _operation_dto(result: PathOperationResult) -> OperationReportDto:
        return OperationReportDto(
            source=str(result.source),
            destination=(
                str(result.destination) if result.destination is not None else None
            ),
            error=result.error,
        )

    def _reports_after_rebuild(
        self,
        vault: Path,
        reports: Iterable[PathOperationResult],
    ) -> tuple[OperationReportDto, ...]:
        records = tuple(self._operation_dto(report) for report in reports)
        rebuild_index(vault)
        return records

    def library_move(
        self,
        paths: Iterable[str],
        destination_folder: str | None,
    ) -> tuple[OperationReportDto, ...]:
        with _translated_errors():
            vault = self._require_vault()
            return self._reports_after_rebuild(
                vault,
                move_papers(vault, list(paths), destination_folder),
            )

    def library_branch(self, relative_path: str) -> OperationReportDto:
        with _translated_errors():
            vault = self._require_vault()
            source = resolve_active_paper_path(vault, relative_path)
            _paper, source_bytes = read_paper_snapshot(source)
            code = next_paper_code(vault)
            destination = source.relative_to(vault).parent / f"{code}.md"
            branch_paper(
                vault,
                source.relative_to(vault),
                destination,
                code,
                expected_source_bytes=source_bytes,
            )
            rebuild_index(vault)
            return OperationReportDto(
                source=str(source.relative_to(vault)),
                destination=str(destination),
                error=None,
            )

    def library_soft_delete(
        self,
        paths: Iterable[str],
    ) -> tuple[OperationReportDto, ...]:
        with _translated_errors():
            vault = self._require_vault()
            return self._reports_after_rebuild(
                vault,
                soft_delete_papers(vault, list(paths)),
            )

    def library_restore(
        self,
        paths: Iterable[str],
    ) -> tuple[OperationReportDto, ...]:
        with _translated_errors():
            vault = self._require_vault()
            return self._reports_after_rebuild(
                vault,
                restore_papers(vault, [Path(path) for path in paths]),
            )

    def library_permanently_delete(
        self,
        paths: Iterable[str],
    ) -> tuple[OperationReportDto, ...]:
        with _translated_errors():
            vault = self._require_vault()
            return self._reports_after_rebuild(
                vault,
                permanently_delete_papers(vault, [Path(path) for path in paths]),
            )

    def library_create_folder(self, name: str) -> str:
        with _translated_errors():
            vault = self._require_vault()
            created = create_folder(vault, name)
            rebuild_index(vault)
            return created.name

    def library_rename_folder(self, folder: str, new_name: str) -> str:
        with _translated_errors():
            vault = self._require_vault()
            renamed = rename_folder(vault, folder, new_name)
            rebuild_index(vault)
            return renamed.name

    def library_merge_folders(
        self,
        source: str,
        destination: str,
    ) -> tuple[OperationReportDto, ...]:
        with _translated_errors():
            vault = self._require_vault()
            return self._reports_after_rebuild(
                vault,
                merge_folders(vault, source, destination),
            )

    def library_soft_delete_folder(
        self,
        folder: str,
    ) -> tuple[OperationReportDto, ...]:
        with _translated_errors():
            vault = self._require_vault()
            return self._reports_after_rebuild(
                vault,
                soft_delete_folder(vault, folder),
            )

    def library_restore_folder(
        self,
        folder: str,
    ) -> tuple[OperationReportDto, ...]:
        with _translated_errors():
            vault = self._require_vault()
            return self._reports_after_rebuild(
                vault,
                restore_folder(vault, folder),
            )

    def library_permanently_delete_folder(
        self,
        folder: str,
    ) -> OperationReportDto:
        with _translated_errors():
            vault = self._require_vault()
            result = permanently_delete_folder(vault, folder)
            rebuild_index(vault)
            return self._operation_dto(result)

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
