"""Transport-neutral protocol-v2 values returned by the application service."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CardPageDto",
    "IndexErrorDto",
    "LibraryEntryDto",
    "LibraryViewDto",
    "MigrationIssueDto",
    "MigrationPreflightDto",
    "MigrationResultDto",
    "NameResultDto",
    "OperationReportDto",
    "OperationReportResultDto",
    "OperationReportsResultDto",
    "PaperDto",
    "PaperEditableDto",
    "PaperOpenResultDto",
    "PaperReconcileRequestDto",
    "PaperReconcileResultDto",
    "PaperSaveDto",
    "PaperSaveResultDto",
    "RepairDto",
    "StartupDto",
    "VaultPreviewDto",
]


@dataclass(frozen=True)
class CardPageDto:
    name: str | None
    content: str
    type: str | None


@dataclass(frozen=True)
class PaperEditableDto:
    display_name: str | None
    tags: tuple[str, ...]
    pages: tuple[CardPageDto, ...]


@dataclass(frozen=True)
class PaperDto:
    path: str | None
    edit_token: str
    code: str
    display_name: str | None
    tags: tuple[str, ...]
    pages: tuple[CardPageDto, ...]
    created: str
    updated: str
    vault_locator: str
    target_path: str
    source_digest: str | None


@dataclass(frozen=True)
class PaperSaveDto:
    edit_token: str
    vault_locator: str
    display_name: str | None
    tags: tuple[str, ...]
    pages: tuple[CardPageDto, ...]


@dataclass(frozen=True)
class PaperSaveResultDto:
    paper: PaperDto
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepairDto:
    origin: str
    path: str
    reason: str
    page_number: int | None = None


@dataclass(frozen=True)
class PaperOpenResultDto:
    state: str
    paper: PaperDto | None = None
    repair: RepairDto | None = None


@dataclass(frozen=True)
class PaperReconcileRequestDto:
    vault_locator: str
    target_path: str
    code: str
    created: str
    source_digest: str | None
    baseline: PaperEditableDto | None
    submitted: PaperEditableDto


@dataclass(frozen=True)
class PaperReconcileResultDto:
    state: str
    paper: PaperDto | None = None
    stale_reason: str | None = None
    repair: RepairDto | None = None
    index_state: str = "not_checked"


@dataclass(frozen=True)
class IndexErrorDto:
    path: str
    reason: str


@dataclass(frozen=True)
class LibraryEntryDto:
    path: str
    code: str
    display_name: str | None
    folder: str | None
    tags: tuple[str, ...]
    preview: str
    page_count: int
    page_names: tuple[str, ...]
    created: str | None
    updated: str | None
    trashed: bool = False
    repair_reason: str | None = None


@dataclass(frozen=True)
class LibraryViewDto:
    scope: str
    entries: tuple[LibraryEntryDto, ...]
    folders: tuple[str, ...]
    trash_folders: tuple[str, ...]
    trash_count: int
    errors: tuple[IndexErrorDto, ...]
    vault_locator: str
    index_state: str


@dataclass(frozen=True)
class OperationReportDto:
    source: str
    destination: str | None
    error: str | None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class OperationReportResultDto:
    report: OperationReportDto
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperationReportsResultDto:
    reports: tuple[OperationReportDto, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class NameResultDto:
    name: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MigrationIssueDto:
    path: str
    message: str


@dataclass(frozen=True)
class MigrationPreflightDto:
    token: str
    kind: str
    ready: bool
    vault_locator: str
    backup_path: str
    cache_count: int
    trash_cache_count: int
    outline_count: int
    trash_outline_count: int
    issues: tuple[MigrationIssueDto, ...]


@dataclass(frozen=True)
class MigrationResultDto:
    kind: str
    converted_count: int
    backup_path: str
    report_path: str
    paper_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class StartupDto:
    state: str
    show_daily_card: bool = False
    message: str = ""
    configured_path: str = ""
    migration: MigrationPreflightDto | None = None
    preview: VaultPreviewDto | None = None
    vault_locator: str | None = None
    index_state: str = "not_checked"


@dataclass(frozen=True)
class VaultPreviewDto:
    token: str
    kind: str
    display_path: str
    paper_count: int = 0
    source_kind: str = ""
    message: str = ""
    migration: MigrationPreflightDto | None = None
    candidate_locator: str | None = None
