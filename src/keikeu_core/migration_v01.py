"""Explicit, one-shot migration from a v0.1 Cache/Outline vault to Paper v2.

This module is deliberately isolated from the normal vault path. It only reads
the v0.1 parser while preparing a complete staged vault, creates a byte-copy
backup outside the active vault, and replaces the whole vault only after every
Paper has been verified. It never parses or converts old Outlines.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile
from typing import Callable

from keikeu_core.legacy_v01 import LegacyCache, read_v01_cache
from keikeu_core.markdown_io import next_paper_code, read_paper, write_paper
from keikeu_core.models import Paper

__all__ = [
    "MigrationIssue",
    "MigrationPreflight",
    "MigrationPreflightError",
    "MigrationResult",
    "is_v01_vault",
    "inspect_v01_vault",
    "migrate_v01_vault",
]


_REPORT_NAME = "keikeu_migration_report.json"
_MACOS_METADATA_NAMES = {".DS_Store"}


@dataclass(frozen=True)
class MigrationIssue:
    """One source path that makes a v0.1 vault unsafe to migrate."""

    path: Path
    message: str


@dataclass(frozen=True)
class _LegacyCache:
    path: Path
    cache: LegacyCache
    trashed: bool


@dataclass(frozen=True)
class MigrationPreflight:
    """Read-only v0.1 inventory and all blocking Cache conversion issues."""

    vault: Path
    legacy_caches: tuple[_LegacyCache, ...]
    issues: tuple[MigrationIssue, ...]
    active_outline_paths: tuple[Path, ...]
    trash_outline_paths: tuple[Path, ...]

    @property
    def ready(self) -> bool:
        return not self.issues

    @property
    def cache_count(self) -> int:
        return sum(1 for legacy in self.legacy_caches if not legacy.trashed) + sum(
            1 for issue in self.issues if issue.path.parent == self.vault / "cache"
        )

    @property
    def trash_cache_count(self) -> int:
        trash_cache = self.vault / ".trash" / "cache"
        return sum(1 for legacy in self.legacy_caches if legacy.trashed) + sum(
            1 for issue in self.issues if issue.path.parent == trash_cache
        )

    @property
    def outline_count(self) -> int:
        return len(self.active_outline_paths)

    @property
    def trash_outline_count(self) -> int:
        return len(self.trash_outline_paths)


class MigrationPreflightError(ValueError):
    """Raised before any write when a vault cannot safely be migrated."""

    def __init__(self, issues: tuple[MigrationIssue, ...]) -> None:
        self.issues = issues
        detail = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"v0.1 vault cannot be migrated: {detail}")


@dataclass(frozen=True)
class MigrationResult:
    """Locations and counts from one completed migration."""

    backup_path: Path
    report_path: Path
    converted_count: int
    paper_paths: tuple[Path, ...]


def _read_index_version(vault: Path) -> int | None:
    try:
        with (vault / "keikeu_index.json").open(encoding="utf-8") as handle:
            index = json.load(handle)
    except (OSError, ValueError):
        return None
    version = index.get("version") if isinstance(index, dict) else None
    return version if isinstance(version, int) else None


def _contains_legacy_cache_marker(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "\ntype: cache\n" in f"\n{text}"


def is_v01_vault(vault: Path) -> bool:
    """Return whether ``vault`` carries any v0.1 marker without changing it."""
    if not vault.is_dir():
        return False
    if (vault / "outlines").is_dir() or _read_index_version(vault) == 1:
        return True
    cache_dir = vault / "cache"
    return cache_dir.is_dir() and any(
        _contains_legacy_cache_marker(path) for path in cache_dir.glob("*.md")
    )


def _files_under(directory: Path) -> tuple[Path, ...]:
    if not directory.is_dir():
        return ()
    return tuple(
        path
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name not in _MACOS_METADATA_NAMES
    )


def _inspect_cache_directory(
    directory: Path,
    *,
    trashed: bool,
    issues: list[MigrationIssue],
    legacy_caches: list[_LegacyCache],
) -> None:
    if not directory.is_dir():
        return
    for path in sorted(directory.iterdir()):
        if path.name in _MACOS_METADATA_NAMES:
            continue
        if not path.is_file() or path.suffix != ".md":
            issues.append(
                MigrationIssue(path, "unsupported entry in v0.1 cache directory")
            )
            continue
        try:
            cache = read_v01_cache(path)
        except (OSError, ValueError, KeyError) as exc:
            issues.append(MigrationIssue(path, str(exc)))
            continue
        if not cache.raw.strip():
            issues.append(
                MigrationIssue(
                    path,
                    "empty raw inspiration must be completed or deleted in v0.1",
                )
            )
            continue
        legacy_caches.append(_LegacyCache(path, cache, trashed))


def inspect_v01_vault(vault: Path) -> MigrationPreflight:
    """Read all active v0.1 Caches and return a no-write migration preflight."""
    vault = vault.resolve()
    issues: list[MigrationIssue] = []
    legacy_caches: list[_LegacyCache] = []
    cache_dir = vault / "cache"

    if not is_v01_vault(vault):
        issues.append(MigrationIssue(vault, "not a v0.1 vault"))
    elif not cache_dir.is_dir():
        issues.append(MigrationIssue(cache_dir, "v0.1 cache directory is missing"))
    else:
        _inspect_cache_directory(
            cache_dir,
            trashed=False,
            issues=issues,
            legacy_caches=legacy_caches,
        )
        _inspect_cache_directory(
            vault / ".trash" / "cache",
            trashed=True,
            issues=issues,
            legacy_caches=legacy_caches,
        )

    return MigrationPreflight(
        vault=vault,
        legacy_caches=tuple(legacy_caches),
        issues=tuple(issues),
        active_outline_paths=_files_under(vault / "outlines"),
        trash_outline_paths=_files_under(vault / ".trash" / "outlines"),
    )


def _checkpoint(hook: Callable[[str], None] | None, point: str) -> None:
    if hook is not None:
        hook(point)


def _ensure_external_root(vault: Path, root: Path) -> Path:
    vault_resolved = vault.resolve()
    root_resolved = root.resolve()
    if root_resolved == vault_resolved or vault_resolved in root_resolved.parents:
        raise ValueError("backup_root must be outside the active vault")
    return root_resolved


def _unique_backup_path(backup_root: Path, vault: Path, now: datetime) -> Path:
    stamp = now.strftime("%Y%m%d-%H%M%S")
    candidate = backup_root / f"{vault.name}-v01-backup-{stamp}"
    suffix = 1
    while candidate.exists():
        candidate = backup_root / f"{vault.name}-v01-backup-{stamp}-{suffix}"
        suffix += 1
    return candidate


def _copy_full_vault(source: Path, destination: Path) -> None:
    """Copy all vault files without letting auxiliary metadata define content."""
    shutil.copytree(source, destination, copy_function=shutil.copy2, symlinks=True)


def _paper_index_entry(vault: Path, path: Path, paper: Paper) -> dict[str, object]:
    return {
        "code": paper.code,
        "path": str(path.relative_to(vault)),
        "summary": paper.summary,
        "tags": paper.tags,
        "created": paper.created.isoformat(),
        "updated": paper.updated.isoformat(),
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _convert_to_staged_vault(
    stage: Path,
    preflight: MigrationPreflight,
    migration_time: datetime,
    backup_path: Path,
) -> tuple[dict[str, object], tuple[Path, ...]]:
    """Build and verify an isolated v2 replacement vault without touching live data."""
    staged_cache = stage / "cache"
    shutil.rmtree(staged_cache)
    staged_cache.mkdir(parents=True)
    staged_trash_cache = stage / ".trash" / "cache"
    shutil.rmtree(staged_trash_cache, ignore_errors=True)
    staged_trash_cache.mkdir(parents=True)

    paper_records: list[dict[str, object]] = []
    paper_paths: list[Path] = []
    index_entries: list[dict[str, object]] = []
    pending_trash_moves: list[tuple[Path, Path]] = []
    for legacy in preflight.legacy_caches:
        code = next_paper_code(stage, migration_time)
        cache = legacy.cache
        paper = Paper(
            code=code,
            initial_summary=cache.raw,
            summary=cache.raw,
            highlights=[cache.notes] if cache.notes != "" else [],
            tags=[],
            created=cache.created,
            updated=cache.updated,
            legacy_title=cache.title,
        )
        destination = write_paper(stage, paper)
        verified = read_paper(destination)
        expected_highlights = [cache.notes] if cache.notes != "" else []
        if (
            verified.initial_summary != cache.raw
            or verified.summary != cache.raw
            or verified.highlights != expected_highlights
            or verified.tags != []
            or verified.created != cache.created
            or verified.updated != cache.updated
            or verified.legacy_title != cache.title
        ):
            raise ValueError(f"Paper verification failed for {legacy.path}")
        final_destination = destination
        if legacy.trashed:
            final_destination = staged_trash_cache / destination.name
            pending_trash_moves.append((destination, final_destination))
        else:
            index_entries.append(_paper_index_entry(stage, destination, verified))
        paper_records.append(
            {
                "source": str(legacy.path.relative_to(preflight.vault)),
                "destination": str(final_destination.relative_to(stage)),
                "code": verified.code,
                "trashed": legacy.trashed,
                "legacy_title": cache.title,
                "legacy_status": cache.status.value,
                "linked_outline": cache.linked_outline,
            }
        )

    for source, destination in pending_trash_moves:
        os.replace(source, destination)
    paper_paths = sorted((stage / "cache").glob("*.md")) + [
        destination for _, destination in pending_trash_moves
    ]

    # Every old Outline is removed as part of the isolated replacement, never
    # parsed or converted. The backup remains the sole rollback source.
    shutil.rmtree(stage / "outlines", ignore_errors=True)
    shutil.rmtree(stage / ".trash" / "outlines", ignore_errors=True)
    _write_json(stage / "keikeu_index.json", {"version": 2, "papers": index_entries, "errors": []})

    report: dict[str, object] = {
        "type": "keikeu-v01-migration-report",
        "schema_version": 1,
        "migrated_at": migration_time.isoformat(),
        "source_vault": str(preflight.vault),
        "backup_path": str(backup_path),
        "converted_count": len(paper_records),
        "papers": paper_records,
        "removed_active_outlines": [
            str(path.relative_to(preflight.vault))
            for path in preflight.active_outline_paths
        ],
        "removed_trash_outlines": [
            str(path.relative_to(preflight.vault))
            for path in preflight.trash_outline_paths
        ],
        "failures": [],
    }
    _write_json(stage / _REPORT_NAME, report)
    return report, tuple(paper_paths)


def _swap_staged_vault(
    vault: Path,
    stage: Path,
    failure_hook: Callable[[str], None] | None,
) -> None:
    """Replace the full active vault, restoring old data for any caught failure."""
    rollback = vault.parent / f".{vault.name}.v01-rollback-{secrets.token_hex(4)}"
    original_moved = False
    staged_moved = False
    try:
        os.replace(vault, rollback)
        original_moved = True
        _checkpoint(failure_hook, "after_original_renamed")
        os.replace(stage, vault)
        staged_moved = True
        _checkpoint(failure_hook, "after_switch")
    except Exception:
        if staged_moved and vault.exists():
            os.replace(vault, stage)
            staged_moved = False
        if original_moved and rollback.exists() and not vault.exists():
            os.replace(rollback, vault)
            original_moved = False
        raise
    finally:
        if staged_moved and rollback.exists():
            shutil.rmtree(rollback, ignore_errors=True)


def migrate_v01_vault(
    vault: Path,
    *,
    backup_root: Path | None = None,
    now: datetime | None = None,
    failure_hook: Callable[[str], None] | None = None,
) -> MigrationResult:
    """Explicitly migrate a preflight-clean v0.1 vault to Paper v2.

    This is intentionally not called from normal vault I/O. A UI must show the
    preflight and irreversible Outline removal before asking the user to invoke
    it. ``failure_hook`` exists only to make every destructive boundary
    testable; a hook that raises is treated like any other I/O failure.
    """
    vault = vault.resolve()
    preflight = inspect_v01_vault(vault)
    if not preflight.ready:
        raise MigrationPreflightError(preflight.issues)

    migration_time = now or datetime.now()
    backup_root = _ensure_external_root(
        vault, backup_root if backup_root is not None else vault.parent / "keikeu-backups"
    )
    _checkpoint(failure_hook, "before_backup")
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = _unique_backup_path(backup_root, vault, migration_time)
    _copy_full_vault(vault, backup_path)
    _checkpoint(failure_hook, "after_backup")

    workspace = Path(
        tempfile.mkdtemp(prefix=f".{vault.name}.v01-stage-", dir=vault.parent)
    )
    stage = workspace / vault.name
    try:
        _copy_full_vault(vault, stage)
        _, staged_papers = _convert_to_staged_vault(
            stage, preflight, migration_time, backup_path
        )
        # The staged output must still contain exactly the verified Papers.
        staged_paper_count = len(tuple((stage / "cache").glob("*.md"))) + len(
            tuple((stage / ".trash" / "cache").glob("*.md"))
        )
        if staged_paper_count != len(staged_papers):
            raise ValueError("staged Paper count does not match converted Cache count")
        _checkpoint(failure_hook, "before_switch")
        _swap_staged_vault(vault, stage, failure_hook)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    paper_paths = tuple(vault / path.relative_to(stage) for path in staged_papers)
    return MigrationResult(
        backup_path=backup_path,
        report_path=vault / _REPORT_NAME,
        converted_count=len(paper_paths),
        paper_paths=paper_paths,
    )
