"""Explicit, one-shot migration from a v0.1 Cache/Outline vault to Paper v2.

This module is deliberately isolated from the normal vault path. It only reads
the v0.1 parser while preparing a complete staged vault, moves the untouched
original to a visible backup, and activates the stage only after every Paper
has been verified. It never parses or converts old Outlines.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import errno
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
from typing import Callable

from keikeu_core.legacy_v01 import LegacyCache, read_v01_cache
from keikeu_core.markdown_io import parse_paper_bytes, render_paper_bytes
from keikeu_core.models import Paper
from keikeu_core.vault import (
    atomic_exchange_at_no_follow,
    copy_vault_no_follow,
    open_directory_no_follow,
    require_atomic_exchange,
    require_home_path,
    snapshot_regular_tree_no_follow,
    validate_vault_tree_no_follow,
)

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
_SAFE_RMTREE_AVAILABLE = shutil.rmtree.avoids_symlink_attacks

_TreeSnapshot = tuple[tuple[Path, ...], tuple[tuple[Path, str], ...]]


class _MigrationRecoveryError(RuntimeError):
    """A failed rollback preserved both trees but needs manual recovery."""

    def __init__(
        self,
        *,
        active_path: Path,
        original_path: Path,
        preserve_workspace: bool,
    ) -> None:
        self.active_path = active_path
        self.original_path = original_path
        self.preserve_workspace = preserve_workspace
        super().__init__(
            "migration rollback failed; active Vault remains at "
            f"{active_path}; untouched original remains at {original_path}"
        )


class _StageOwnershipError(ValueError):
    """A generated workspace entry no longer names the directory we created."""


class _PinnedPathError(_StageOwnershipError):
    """A retained Home path no longer resolves through its original entries."""


@dataclass(frozen=True)
class _PinnedDirectoryLink:
    """One retained parent/name identity in a Home-contained directory chain."""

    parent_fd: int
    name: str
    identity: tuple[int, int]
    display_path: Path


@dataclass(frozen=True)
class _PinnedHomeDirectory:
    """A Home directory plus every descriptor needed to revalidate its path."""

    path: Path
    descriptor: int
    identity: tuple[int, int]
    links: tuple[_PinnedDirectoryLink, ...]


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


def _directory_identity(descriptor: int, display_path: Path) -> tuple[int, int]:
    entry_stat = os.fstat(descriptor)
    if not stat.S_ISDIR(entry_stat.st_mode):
        raise _StageOwnershipError(f"directory changed identity: {display_path}")
    return entry_stat.st_dev, entry_stat.st_ino


def _entry_directory_identity(
    parent_fd: int,
    name: str,
    display_path: Path,
) -> tuple[int, int]:
    try:
        entry_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise _StageOwnershipError(f"generated directory disappeared: {display_path}") from exc
    if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISDIR(entry_stat.st_mode):
        raise _StageOwnershipError(f"generated directory was replaced: {display_path}")
    return entry_stat.st_dev, entry_stat.st_ino


def _require_owned_directory(
    parent_fd: int,
    name: str,
    expected_identity: tuple[int, int],
    display_path: Path,
) -> None:
    if _entry_directory_identity(parent_fd, name, display_path) != expected_identity:
        raise _StageOwnershipError(f"generated directory was replaced: {display_path}")


def _open_child_directory(
    parent_fd: int,
    name: str,
    display_path: Path,
) -> int:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise _StageOwnershipError(
                f"generated directory was replaced: {display_path}"
            ) from exc
        raise
    try:
        _directory_identity(descriptor, display_path)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _remove_directory_at(
    parent_fd: int,
    name: str,
    display_path: Path,
    *,
    missing_ok: bool,
) -> None:
    try:
        _entry_directory_identity(parent_fd, name, display_path)
    except _StageOwnershipError:
        if missing_ok:
            try:
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return
        raise
    if not _SAFE_RMTREE_AVAILABLE:
        raise RuntimeError("safe fd-relative recursive cleanup is unavailable")
    try:
        shutil.rmtree(name, dir_fd=parent_fd)
    except OSError as exc:
        raise _StageOwnershipError(
            f"generated directory changed during cleanup: {display_path}"
        ) from exc


def _create_directory_at(parent_fd: int, name: str, display_path: Path) -> int:
    try:
        os.mkdir(name, dir_fd=parent_fd)
    except OSError as exc:
        raise _StageOwnershipError(
            f"could not create owned stage directory: {display_path}"
        ) from exc
    return _open_child_directory(parent_fd, name, display_path)


def _unlink_owned_regular_at(
    directory_fd: int,
    name: str,
    identity: tuple[int, int],
) -> None:
    try:
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == identity:
        os.unlink(name, dir_fd=directory_fd)


def _write_new_bytes_at(
    directory_fd: int,
    name: str,
    data: bytes,
) -> tuple[int, int]:
    descriptor = os.open(
        name,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=directory_fd,
    )
    entry_stat = os.fstat(descriptor)
    identity = (entry_stat.st_dev, entry_stat.st_ino)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        _unlink_owned_regular_at(directory_fd, name, identity)
        raise
    finally:
        os.close(descriptor)
    return identity


def _read_regular_bytes_at(directory_fd: int, name: str) -> bytes:
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _StageOwnershipError(f"generated Paper is not regular: {name}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read()
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if before_identity != after_identity:
        raise _StageOwnershipError(f"generated Paper changed while reading: {name}")
    return data


def _replace_bytes_at(directory_fd: int, name: str, data: bytes) -> None:
    while True:
        temporary_name = f".{name}.{secrets.token_hex(8)}.tmp"
        try:
            identity = _write_new_bytes_at(directory_fd, temporary_name, data)
        except FileExistsError:
            continue
        break
    try:
        os.replace(
            temporary_name,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        _unlink_owned_regular_at(directory_fd, temporary_name, identity)


def _move_regular_no_overwrite_at(
    source_fd: int,
    destination_fd: int,
    name: str,
) -> None:
    source_stat = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
    if stat.S_ISLNK(source_stat.st_mode) or not stat.S_ISREG(source_stat.st_mode):
        raise _StageOwnershipError(f"generated Paper is not regular: {name}")
    identity = (source_stat.st_dev, source_stat.st_ino)
    os.link(
        name,
        name,
        src_dir_fd=source_fd,
        dst_dir_fd=destination_fd,
        follow_symlinks=False,
    )
    try:
        linked_stat = os.stat(name, dir_fd=destination_fd, follow_symlinks=False)
        if (linked_stat.st_dev, linked_stat.st_ino) != identity:
            raise _StageOwnershipError(f"generated Paper move changed identity: {name}")
        os.unlink(name, dir_fd=source_fd)
    except Exception:
        _unlink_owned_regular_at(destination_fd, name, identity)
        raise


def _count_regular_markdown_files(directory_fd: int) -> int:
    count = 0
    for name in os.listdir(directory_fd):
        entry_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            stat.S_ISLNK(entry_stat.st_mode)
            or not stat.S_ISREG(entry_stat.st_mode)
            or not name.endswith(".md")
        ):
            raise _StageOwnershipError(f"unexpected generated cache entry: {name}")
        count += 1
    return count


def _close_descriptor_quietly(descriptor: int | None) -> None:
    if descriptor is None:
        return
    try:
        os.close(descriptor)
    except OSError:
        pass


def _cleanup_owned_workspace(
    parent_fd: int,
    name: str,
    identity: tuple[int, int],
    display_path: Path,
) -> None:
    try:
        _require_owned_directory(parent_fd, name, identity, display_path)
    except _StageOwnershipError:
        return
    if not _SAFE_RMTREE_AVAILABLE:
        return
    try:
        shutil.rmtree(name, dir_fd=parent_fd)
    except OSError:
        pass


def _require_owned_stage_tree(
    *,
    vault: Path,
    workspace: Path,
    stage: Path,
    vault_parent_fd: int,
    workspace_fd: int,
    stage_fd: int,
    vault_identity: tuple[int, int],
    workspace_identity: tuple[int, int],
    stage_identity: tuple[int, int],
) -> None:
    _require_owned_directory(
        vault_parent_fd,
        vault.name,
        vault_identity,
        vault,
    )
    _require_owned_directory(
        vault_parent_fd,
        workspace.name,
        workspace_identity,
        workspace,
    )
    _require_owned_directory(
        workspace_fd,
        stage.name,
        stage_identity,
        stage,
    )
    if _directory_identity(workspace_fd, workspace) != workspace_identity:
        raise _StageOwnershipError(f"generated directory was replaced: {workspace}")
    if _directory_identity(stage_fd, stage) != stage_identity:
        raise _StageOwnershipError(f"generated directory was replaced: {stage}")


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _pin_home_directory_no_follow(
    path: Path,
    *,
    create: bool,
) -> _PinnedHomeDirectory:
    """Open a Home directory through retained, revalidatable descriptors."""
    raw_path = _absolute_path(path)
    resolved_path = require_home_path(raw_path)
    home = Path.home().resolve()
    try:
        relative = raw_path.relative_to(home)
    except ValueError as exc:
        raise ValueError(
            f"path must be lexically inside current user Home: {path}"
        ) from exc

    if resolved_path != raw_path:
        raise ValueError(f"path contains a symlink ancestor: {path}")

    descriptors: list[int] = [open_directory_no_follow(home)]
    links: list[_PinnedDirectoryLink] = []
    current = home
    try:
        for part in relative.parts:
            parent_fd = descriptors[-1]
            current /= part
            try:
                entry_stat = os.stat(
                    part,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o700, dir_fd=parent_fd)
                entry_stat = os.stat(
                    part,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISDIR(
                entry_stat.st_mode
            ):
                raise ValueError(
                    f"path component is not an ordinary directory: {current}"
                )
            child_fd = _open_child_directory(parent_fd, part, current)
            child_identity = _directory_identity(child_fd, current)
            entry_identity = (entry_stat.st_dev, entry_stat.st_ino)
            if child_identity != entry_identity:
                os.close(child_fd)
                raise _StageOwnershipError(
                    f"directory changed while opening: {current}"
                )
            links.append(
                _PinnedDirectoryLink(
                    parent_fd=parent_fd,
                    name=part,
                    identity=child_identity,
                    display_path=current,
                )
            )
            descriptors.append(child_fd)

        pinned = _PinnedHomeDirectory(
            path=raw_path,
            descriptor=descriptors[-1],
            identity=_directory_identity(descriptors[-1], raw_path),
            links=tuple(links),
        )
        _require_pinned_directory(pinned)
        return pinned
    except Exception:
        for descriptor in reversed(descriptors):
            _close_descriptor_quietly(descriptor)
        raise


def _require_pinned_directory(directory: _PinnedHomeDirectory) -> None:
    try:
        for link in directory.links:
            _require_owned_directory(
                link.parent_fd,
                link.name,
                link.identity,
                link.display_path,
            )
        if (
            _directory_identity(directory.descriptor, directory.path)
            != directory.identity
        ):
            raise _StageOwnershipError(
                f"generated directory was replaced: {directory.path}"
            )
    except _StageOwnershipError as exc:
        raise _PinnedPathError(str(exc)) from exc


def _close_pinned_directory(directory: _PinnedHomeDirectory | None) -> None:
    if directory is None:
        return
    descriptors = [link.parent_fd for link in directory.links]
    descriptors.append(directory.descriptor)
    for descriptor in reversed(descriptors):
        _close_descriptor_quietly(descriptor)


def _require_home_directory_no_follow(path: Path, *, create: bool) -> Path:
    """Return a Home directory after rejecting symlink/special ancestors."""
    pinned = _pin_home_directory_no_follow(path, create=create)
    try:
        return pinned.path
    finally:
        _close_pinned_directory(pinned)


def _require_migration_source(vault: Path) -> Path:
    raw_vault = _require_home_directory_no_follow(vault, create=False)
    validate_vault_tree_no_follow(raw_vault)
    return require_home_path(raw_vault)


def _prepare_external_root(vault: Path, root: Path) -> _PinnedHomeDirectory:
    raw_root = _absolute_path(root)
    canonical_root = require_home_path(raw_root)
    if canonical_root == vault or vault in canonical_root.parents:
        raise ValueError("backup_root must be outside the active vault")
    return _pin_home_directory_no_follow(raw_root, create=True)


def _unique_backup_path(
    backup_root: _PinnedHomeDirectory,
    vault: Path,
    now: datetime,
) -> Path:
    stamp = now.strftime("%Y%m%d-%H%M%S")
    candidate = backup_root.path / f"{vault.name}-v01-backup-{stamp}"
    suffix = 1
    while True:
        try:
            candidate_stat = os.stat(
                candidate.name,
                dir_fd=backup_root.descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return candidate
        if stat.S_ISLNK(candidate_stat.st_mode) or not (
            stat.S_ISDIR(candidate_stat.st_mode)
            or stat.S_ISREG(candidate_stat.st_mode)
        ):
            raise ValueError(f"unsupported existing backup target: {candidate}")
        candidate = (
            backup_root.path / f"{vault.name}-v01-backup-{stamp}-{suffix}"
        )
        suffix += 1


def _create_workspace_at(
    vault_parent: _PinnedHomeDirectory,
    vault_name: str,
) -> tuple[Path, int, tuple[int, int]]:
    prefix = f".{vault_name}.v01-stage-"
    for _attempt in range(100):
        name = f"{prefix}{secrets.token_hex(4)}"
        workspace = vault_parent.path / name
        try:
            os.mkdir(name, mode=0o700, dir_fd=vault_parent.descriptor)
        except FileExistsError:
            continue
        identity = _entry_directory_identity(
            vault_parent.descriptor,
            name,
            workspace,
        )
        try:
            descriptor = _open_child_directory(
                vault_parent.descriptor,
                name,
                workspace,
            )
            if _directory_identity(descriptor, workspace) != identity:
                os.close(descriptor)
                raise _StageOwnershipError(
                    f"generated directory was replaced: {workspace}"
                )
        except Exception:
            try:
                _require_owned_directory(
                    vault_parent.descriptor,
                    name,
                    identity,
                    workspace,
                )
                os.rmdir(name, dir_fd=vault_parent.descriptor)
            except (OSError, _StageOwnershipError):
                pass
            raise
        return workspace, descriptor, identity
    raise FileExistsError("could not allocate a unique migration workspace")


def _copy_full_vault(source: Path, destination: Path) -> None:
    """Copy and byte-verify a generated stage without following source links."""
    copy_vault_no_follow(source, destination)


def _paper_index_entry(vault: Path, path: Path, paper: Paper) -> dict[str, object]:
    return {
        "code": paper.code,
        "path": str(path.relative_to(vault)),
        "summary": paper.summary,
        "tags": paper.tags,
        "created": paper.created.isoformat(),
        "updated": paper.updated.isoformat(),
    }


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _convert_to_staged_vault(
    stage: Path,
    stage_fd: int,
    preflight: MigrationPreflight,
    migration_time: datetime,
    backup_path: Path,
) -> tuple[dict[str, object], tuple[Path, ...]]:
    """Build and verify an isolated v2 replacement vault without touching live data."""
    trash_fd: int | None = None
    cache_fd: int | None = None
    trash_cache_fd: int | None = None
    try:
        try:
            trash_fd = _open_child_directory(stage_fd, ".trash", stage / ".trash")
        except FileNotFoundError:
            trash_fd = _create_directory_at(stage_fd, ".trash", stage / ".trash")

        _remove_directory_at(
            stage_fd,
            "cache",
            stage / "cache",
            missing_ok=False,
        )
        cache_fd = _create_directory_at(stage_fd, "cache", stage / "cache")
        _remove_directory_at(
            trash_fd,
            "cache",
            stage / ".trash" / "cache",
            missing_ok=True,
        )
        trash_cache_fd = _create_directory_at(
            trash_fd,
            "cache",
            stage / ".trash" / "cache",
        )

        # Every old Outline is removed from the generated stage only; the
        # untouched original remains the rollback source.
        _remove_directory_at(
            stage_fd,
            "outlines",
            stage / "outlines",
            missing_ok=True,
        )
        _remove_directory_at(
            trash_fd,
            "outlines",
            stage / ".trash" / "outlines",
            missing_ok=True,
        )

        if len(preflight.legacy_caches) > 999:
            raise ValueError("v0.1 migration supports at most 999 Caches per run")
        paper_records: list[dict[str, object]] = []
        paper_paths: list[Path] = []
        index_entries: list[dict[str, object]] = []
        date_stamp = migration_time.strftime("%Y%m%d")
        for sequence, legacy in enumerate(preflight.legacy_caches, start=1):
            code = f"K-{date_stamp}-{sequence:03d}"
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
            name = f"{code}.md"
            _write_new_bytes_at(cache_fd, name, render_paper_bytes(paper))
            verified = parse_paper_bytes(_read_regular_bytes_at(cache_fd, name))
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

            relative_destination = Path("cache") / name
            if legacy.trashed:
                _move_regular_no_overwrite_at(cache_fd, trash_cache_fd, name)
                relative_destination = Path(".trash") / "cache" / name
            else:
                index_entries.append(
                    _paper_index_entry(
                        stage,
                        stage / relative_destination,
                        verified,
                    )
                )
            paper_paths.append(stage / relative_destination)
            paper_records.append(
                {
                    "source": str(legacy.path.relative_to(preflight.vault)),
                    "destination": str(relative_destination),
                    "code": verified.code,
                    "trashed": legacy.trashed,
                    "legacy_title": cache.title,
                    "legacy_status": cache.status.value,
                    "linked_outline": cache.linked_outline,
                }
            )

        staged_paper_count = _count_regular_markdown_files(
            cache_fd
        ) + _count_regular_markdown_files(trash_cache_fd)
        if staged_paper_count != len(paper_paths):
            raise ValueError("staged Paper count does not match converted Cache count")

        _replace_bytes_at(
            stage_fd,
            "keikeu_index.json",
            _json_bytes({"version": 2, "papers": index_entries, "errors": []}),
        )

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
        _replace_bytes_at(stage_fd, _REPORT_NAME, _json_bytes(report))
        return report, tuple(paper_paths)
    finally:
        _close_descriptor_quietly(trash_cache_fd)
        _close_descriptor_quietly(cache_fd)
        _close_descriptor_quietly(trash_fd)


def _swap_staged_vault(
    vault: Path,
    workspace: Path,
    stage: Path,
    backup_path: Path,
    source_snapshot: _TreeSnapshot,
    vault_parent: _PinnedHomeDirectory,
    backup_root: _PinnedHomeDirectory,
    workspace_fd: int,
    stage_fd: int,
    vault_identity: tuple[int, int],
    workspace_identity: tuple[int, int],
    stage_identity: tuple[int, int],
    failure_hook: Callable[[str], None] | None,
) -> None:
    """Exchange in the stage without ever leaving the active path absent."""
    original_location: str | None = None
    try:
        _checkpoint(failure_hook, "before_backup")
        _require_pinned_directory(vault_parent)
        _require_pinned_directory(backup_root)
        _require_owned_stage_tree(
            vault=vault,
            workspace=workspace,
            stage=stage,
            vault_parent_fd=vault_parent.descriptor,
            workspace_fd=workspace_fd,
            stage_fd=stage_fd,
            vault_identity=vault_identity,
            workspace_identity=workspace_identity,
            stage_identity=stage_identity,
        )
        try:
            os.stat(
                backup_path.name,
                dir_fd=backup_root.descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(f"backup target already exists: {backup_path}")
        atomic_exchange_at_no_follow(
            vault_parent.descriptor,
            vault.name,
            workspace_fd,
            stage.name,
        )
        original_location = "stage"
        _require_owned_directory(
            vault_parent.descriptor,
            workspace.name,
            workspace_identity,
            workspace,
        )
        _require_owned_directory(
            vault_parent.descriptor,
            vault.name,
            stage_identity,
            vault,
        )
        _require_owned_directory(
            workspace_fd,
            stage.name,
            vault_identity,
            stage,
        )
        if snapshot_regular_tree_no_follow(stage) != source_snapshot:
            raise ValueError("v0.1 source changed before the atomic switch")
        _checkpoint(failure_hook, "after_original_renamed")
        _checkpoint(failure_hook, "after_switch")
        _require_pinned_directory(vault_parent)
        _require_pinned_directory(backup_root)
        _require_owned_directory(
            workspace_fd,
            stage.name,
            vault_identity,
            stage,
        )
        try:
            os.stat(
                backup_path.name,
                dir_fd=backup_root.descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(f"backup target already exists: {backup_path}")
        os.replace(
            stage.name,
            backup_path.name,
            src_dir_fd=workspace_fd,
            dst_dir_fd=backup_root.descriptor,
        )
        original_location = "backup"
        _require_owned_directory(
            backup_root.descriptor,
            backup_path.name,
            vault_identity,
            backup_path,
        )
        _checkpoint(failure_hook, "after_backup")
        _require_pinned_directory(backup_root)
        _require_owned_directory(
            backup_root.descriptor,
            backup_path.name,
            vault_identity,
            backup_path,
        )
    except Exception:
        if original_location == "stage":
            try:
                atomic_exchange_at_no_follow(
                    vault_parent.descriptor,
                    vault.name,
                    workspace_fd,
                    stage.name,
                )
            except Exception as rollback_error:
                raise _MigrationRecoveryError(
                    active_path=vault,
                    original_path=stage,
                    preserve_workspace=True,
                ) from rollback_error
        elif original_location == "backup":
            try:
                atomic_exchange_at_no_follow(
                    vault_parent.descriptor,
                    vault.name,
                    backup_root.descriptor,
                    backup_path.name,
                )
            except Exception as rollback_error:
                raise _MigrationRecoveryError(
                    active_path=vault,
                    original_path=backup_path,
                    preserve_workspace=False,
                ) from rollback_error
            try:
                os.replace(
                    backup_path.name,
                    stage.name,
                    src_dir_fd=backup_root.descriptor,
                    dst_dir_fd=workspace_fd,
                )
            except Exception as cleanup_error:
                raise _MigrationRecoveryError(
                    active_path=vault,
                    original_path=vault,
                    preserve_workspace=False,
                ) from cleanup_error
        raise


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
    vault = _require_migration_source(vault)
    source_snapshot = snapshot_regular_tree_no_follow(vault)
    preflight = inspect_v01_vault(vault)
    if snapshot_regular_tree_no_follow(vault) != source_snapshot:
        raise ValueError("v0.1 source changed during migration preflight")
    if not preflight.ready:
        raise MigrationPreflightError(preflight.issues)

    require_atomic_exchange()
    migration_time = now or datetime.now()
    requested_backup_root = (
        backup_root if backup_root is not None else vault.parent / "keikeu-backups"
    )
    vault_parent = _pin_home_directory_no_follow(vault.parent, create=False)
    pinned_backup_root: _PinnedHomeDirectory | None = None
    backup_path: Path | None = None
    workspace: Path | None = None
    stage: Path | None = None
    workspace_fd: int | None = None
    stage_fd: int | None = None
    workspace_identity: tuple[int, int] | None = None
    cleanup_workspace = True
    try:
        _require_pinned_directory(vault_parent)
        vault_identity = _entry_directory_identity(
            vault_parent.descriptor,
            vault.name,
            vault,
        )
        pinned_backup_root = _prepare_external_root(
            vault,
            requested_backup_root,
        )
        if (
            vault_identity[0] != vault_parent.identity[0]
            or pinned_backup_root.identity[0] != vault_identity[0]
        ):
            raise ValueError(
                "vault, staging parent, and backup_root must share one filesystem"
            )
        _require_pinned_directory(vault_parent)
        _require_pinned_directory(pinned_backup_root)
        backup_path = _unique_backup_path(
            pinned_backup_root,
            vault,
            migration_time,
        )
        _checkpoint(failure_hook, "before_workspace")
        _require_pinned_directory(vault_parent)
        _require_pinned_directory(pinned_backup_root)
        workspace, workspace_fd, workspace_identity = _create_workspace_at(
            vault_parent,
            vault.name,
        )
        stage = workspace / vault.name
        _copy_full_vault(vault, stage)
        stage_fd = open_directory_no_follow(stage)
        stage_identity = _directory_identity(stage_fd, stage)
        _require_owned_stage_tree(
            vault=vault,
            workspace=workspace,
            stage=stage,
            vault_parent_fd=vault_parent.descriptor,
            workspace_fd=workspace_fd,
            stage_fd=stage_fd,
            vault_identity=vault_identity,
            workspace_identity=workspace_identity,
            stage_identity=stage_identity,
        )
        if snapshot_regular_tree_no_follow(stage) != source_snapshot:
            raise ValueError("v0.1 source changed before staging completed")
        _checkpoint(failure_hook, "after_stage_copy")
        _require_owned_stage_tree(
            vault=vault,
            workspace=workspace,
            stage=stage,
            vault_parent_fd=vault_parent.descriptor,
            workspace_fd=workspace_fd,
            stage_fd=stage_fd,
            vault_identity=vault_identity,
            workspace_identity=workspace_identity,
            stage_identity=stage_identity,
        )
        _, staged_papers = _convert_to_staged_vault(
            stage,
            stage_fd,
            preflight,
            migration_time,
            backup_path,
        )
        _require_owned_stage_tree(
            vault=vault,
            workspace=workspace,
            stage=stage,
            vault_parent_fd=vault_parent.descriptor,
            workspace_fd=workspace_fd,
            stage_fd=stage_fd,
            vault_identity=vault_identity,
            workspace_identity=workspace_identity,
            stage_identity=stage_identity,
        )
        if snapshot_regular_tree_no_follow(vault) != source_snapshot:
            raise ValueError("v0.1 source changed before the atomic switch")
        _checkpoint(failure_hook, "before_switch")
        _swap_staged_vault(
            vault,
            workspace,
            stage,
            backup_path,
            source_snapshot,
            vault_parent,
            pinned_backup_root,
            workspace_fd,
            stage_fd,
            vault_identity,
            workspace_identity,
            stage_identity,
            failure_hook,
        )
    except _MigrationRecoveryError as exc:
        cleanup_workspace = not exc.preserve_workspace
        raise
    except _PinnedPathError:
        raise
    except _StageOwnershipError:
        cleanup_workspace = False
        raise
    finally:
        _close_descriptor_quietly(stage_fd)
        _close_descriptor_quietly(workspace_fd)
        if (
            cleanup_workspace
            and workspace is not None
            and workspace_identity is not None
        ):
            _cleanup_owned_workspace(
                vault_parent.descriptor,
                workspace.name,
                workspace_identity,
                workspace,
            )
        _close_pinned_directory(pinned_backup_root)
        _close_pinned_directory(vault_parent)

    assert stage is not None
    assert backup_path is not None
    paper_paths = tuple(vault / path.relative_to(stage) for path in staged_papers)
    return MigrationResult(
        backup_path=backup_path,
        report_path=vault / _REPORT_NAME,
        converted_count=len(paper_paths),
        paper_paths=paper_paths,
    )
