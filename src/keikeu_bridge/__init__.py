"""GUI-independent application boundary for keikeu desktop adapters."""

from keikeu_bridge.dto import (
    IndexErrorDto,
    LibraryEntryDto,
    LibraryViewDto,
    MigrationIssueDto,
    MigrationPreflightDto,
    MigrationResultDto,
    OperationReportDto,
    PaperDto,
    PaperSaveDto,
    StartupDto,
    VaultPreviewDto,
)
from keikeu_bridge.service import KeikeuService, ServiceError

__all__ = [
    "IndexErrorDto",
    "KeikeuService",
    "LibraryEntryDto",
    "LibraryViewDto",
    "MigrationIssueDto",
    "MigrationPreflightDto",
    "MigrationResultDto",
    "OperationReportDto",
    "PaperDto",
    "PaperSaveDto",
    "ServiceError",
    "StartupDto",
    "VaultPreviewDto",
]
