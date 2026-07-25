"""Transport-neutral values returned by the keikeu application service."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "FlashcardDeckDto",
    "FlashcardDto",
    "HighlightDto",
    "IndexErrorDto",
    "LibraryEntryDto",
    "LibraryViewDto",
    "MigrationIssueDto",
    "MigrationPreflightDto",
    "MigrationResultDto",
    "OperationReportDto",
    "PaperDto",
    "PaperOptionDto",
    "PaperSaveDto",
    "StartupDto",
    "VaultPreviewDto",
]


@dataclass(frozen=True)
class HighlightDto:
    display_name: str | None
    content: str


@dataclass(frozen=True)
class PaperDto:
    path: str | None
    edit_token: str
    code: str
    display_name: str | None
    initial_summary: str
    summary: str
    highlights: tuple[HighlightDto, ...]
    tags: tuple[str, ...]
    created: str
    updated: str


@dataclass(frozen=True)
class PaperSaveDto:
    edit_token: str
    summary: str
    display_name: str | None = None
    highlights: tuple[HighlightDto, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PaperOptionDto:
    path: str
    code: str
    display_name: str | None
    label: str


@dataclass(frozen=True)
class FlashcardDto:
    title: str
    content: str


@dataclass(frozen=True)
class FlashcardDeckDto:
    path: str
    paper_label: str
    cards: tuple[FlashcardDto, ...]
    options: tuple[PaperOptionDto, ...]


@dataclass(frozen=True)
class LibraryEntryDto:
    path: str
    code: str
    display_name: str | None
    folder: str | None
    summary: str
    tags: tuple[str, ...]
    highlight_names: tuple[str, ...]
    created: str
    updated: str
    trashed: bool = False


@dataclass(frozen=True)
class IndexErrorDto:
    path: str
    reason: str


@dataclass(frozen=True)
class LibraryViewDto:
    scope: str
    entries: tuple[LibraryEntryDto, ...]
    folders: tuple[str, ...]
    trash_folders: tuple[str, ...]
    trash_count: int
    errors: tuple[IndexErrorDto, ...]


@dataclass(frozen=True)
class OperationReportDto:
    source: str
    destination: str | None
    error: str | None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class MigrationIssueDto:
    path: str
    message: str


@dataclass(frozen=True)
class MigrationPreflightDto:
    token: str
    ready: bool
    cache_count: int
    trash_cache_count: int
    outline_count: int
    trash_outline_count: int
    issues: tuple[MigrationIssueDto, ...]


@dataclass(frozen=True)
class MigrationResultDto:
    converted_count: int
    backup_path: str
    report_path: str
    paper_paths: tuple[str, ...]


@dataclass(frozen=True)
class StartupDto:
    state: str
    show_daily_card: bool = False
    message: str = ""
    migration: MigrationPreflightDto | None = None


@dataclass(frozen=True)
class VaultPreviewDto:
    token: str
    kind: str
    display_path: str
    paper_count: int = 0
    source_kind: str = ""
    message: str = ""
    migration: MigrationPreflightDto | None = None
