"""Paper Vault layout, recovery bin, and local config resolution.

The user-selected vault holds only durable Paper Markdown and a disposable
index. Recovery moves a file under ``.trash/cache`` without rewriting its
historical Paper code.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from datetime import date, datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import unicodedata
from typing import Callable, Iterable

from keikeu_core.models import validate_paper_code

__all__ = [
    "VaultSelectionToken",
    "PathOperationResult",
    "capture_vault_selection_token",
    "init_vault",
    "is_vault",
    "require_home_path",
    "validate_regular_tree_no_follow",
    "snapshot_regular_tree_no_follow",
    "validate_vault_tree_no_follow",
    "open_directory_no_follow",
    "open_regular_no_follow",
    "require_atomic_exchange",
    "atomic_exchange_at_no_follow",
    "atomic_exchange_no_follow",
    "scan_active_papers",
    "scan_trashed_papers",
    "list_active_folders",
    "list_trashed_folders",
    "list_active_papers",
    "next_paper_code",
    "create_folder",
    "rename_folder",
    "merge_folders",
    "move_papers",
    "soft_delete_papers",
    "soft_delete_folder",
    "restore_papers",
    "restore_folder",
    "permanently_delete_papers",
    "permanently_delete_folder",
    "resolve_active_paper_path",
    "resolve_trashed_paper_path",
    "vault_index_version",
    "validate_vault_papers",
    "validate_folder_name",
    "copy_vault_no_follow",
    "soft_delete",
    "list_trashed_papers",
    "restore_paper",
    "get_vault",
    "set_vault",
]

_TreeSnapshot = tuple[tuple[Path, ...], tuple[tuple[Path, str], ...]]

_EMPTY_INDEX: dict[str, object] = {"version": 3, "papers": [], "errors": []}
_ATOMIC_EXCHANGE_FLAG = 0x00000002
_DARWIN_ATOMIC_NO_REPLACE_FLAG = 0x00000004
_LINUX_ATOMIC_NO_REPLACE_FLAG = 0x00000001
_PAPER_CODE_FILENAME_RE = re.compile(r"^K-\d{8}-(\d{3})$")
_RESERVED_FOLDER_NAMES = {
    unicodedata.normalize("NFC", name).casefold()
    for name in (
        "cache",
        ".trash",
        "keikeu_index.json",
        "全部 Paper",
        "未归类",
        "Trash",
    )
}


@dataclass
class _OwnedDirectory:
    parent_fd: int
    name: str
    identity: tuple[int, int]
    display_path: Path


@dataclass(frozen=True)
class PathOperationResult:
    """One explicit filesystem item outcome for batch and folder operations."""

    source: Path
    destination: Path | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass
class _OwnedFile:
    parent_fd: int
    name: str
    identity: tuple[int, int]
    digest: str
    display_path: Path


@dataclass(frozen=True)
class VaultSelectionToken:
    """Immutable identity and byte snapshot for one validated Vault selection."""

    path: Path
    root_identity: tuple[int, int]
    tree_snapshot: _TreeSnapshot


def _current_home() -> Path:
    return Path.home()


def _native_exchange_operation():
    if sys.platform == "darwin":
        operation_name = "renameatx_np"
    elif sys.platform.startswith("linux"):
        operation_name = "renameat2"
    else:
        raise RuntimeError(
            f"atomic filesystem exchange is unavailable on {sys.platform}"
        )

    library = ctypes.CDLL(None, use_errno=True)
    try:
        operation = getattr(library, operation_name)
    except AttributeError as exc:
        raise RuntimeError(
            f"atomic filesystem exchange is unavailable on {sys.platform}"
        ) from exc
    operation.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    operation.restype = ctypes.c_int
    return operation


def require_atomic_exchange() -> None:
    """Fail without mutation when this platform lacks native path exchange."""
    _native_exchange_operation()


def require_home_path(path: Path) -> Path:
    """Return a canonical Home-contained path or reject it before a write."""
    resolved = path.expanduser().resolve()
    home = _current_home().resolve()
    try:
        relative = resolved.relative_to(home)
    except ValueError as exc:
        raise ValueError(
            f"path resolves outside current user Home: {path} -> {resolved}"
        ) from exc
    if any(part.casefold().endswith(".app") for part in relative.parts):
        raise ValueError(f"application bundle paths are read-only: {resolved}")
    return resolved


def _require_lexical_home_path(path: Path) -> Path:
    """Validate Home containment without resolving away path identity."""
    absolute = _lexical_absolute_path(path)
    home = _lexical_absolute_path(_current_home())
    try:
        relative = absolute.relative_to(home)
    except ValueError as exc:
        raise ValueError(f"path is outside current user Home: {absolute}") from exc
    if any(part.casefold().endswith(".app") for part in relative.parts):
        raise ValueError(f"application bundle paths are read-only: {absolute}")
    home_fd = open_directory_no_follow(home)
    os.close(home_fd)
    return absolute


def validate_folder_name(name: str) -> str:
    """Validate and return the trimmed one-level author folder name."""
    trimmed = name.strip()
    comparison = unicodedata.normalize("NFC", trimmed).casefold()
    if not 1 <= len(trimmed) <= 200:
        raise ValueError("folder name must contain 1-200 Unicode code points")
    if any(
        unicodedata.category(character) in {"Cc", "Zl", "Zp"}
        for character in trimmed
    ):
        raise ValueError("folder name must be one line without control characters")
    if "/" in trimmed or ":" in trimmed:
        raise ValueError("folder name cannot contain '/' or ':'")
    if trimmed in {".", ".."} or trimmed.startswith("."):
        raise ValueError("folder name cannot be '.', '..', or start with '.'")
    if comparison in _RESERVED_FOLDER_NAMES:
        raise ValueError("folder name is reserved")
    return trimmed


def _folder_name_key(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def _semantic_folder_collision_at(
    parent_fd: int,
    name: str,
    *,
    excluding: str | None = None,
) -> str | None:
    expected_key = _folder_name_key(name)
    with os.scandir(parent_fd) as entries:
        candidates = sorted(entries, key=lambda entry: entry.name)
    for entry in candidates:
        if entry.name == excluding:
            continue
        if _folder_name_key(entry.name) == expected_key:
            return entry.name
    return None


def _index_path(vault: Path) -> Path:
    return vault / "keikeu_index.json"


def _scan_regular_tree_fd(
    root_fd: int,
    root: Path,
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Return a pinned root's relative directories and files."""
    directories: list[Path] = []
    files: list[Path] = []

    def visit(directory_fd: int, relative: Path) -> None:
        with os.scandir(directory_fd) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                entry_relative = relative / entry.name
                entry_path = root / entry_relative
                entry_stat = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(entry_stat.st_mode):
                    raise ValueError(f"symlink is not supported: {entry_path}")
                if stat.S_ISDIR(entry_stat.st_mode):
                    child_fd = _open_child_directory_no_follow(
                        directory_fd,
                        entry.name,
                        entry_path,
                    )
                    child_stat = os.fstat(child_fd)
                    if (child_stat.st_dev, child_stat.st_ino) != (
                        entry_stat.st_dev,
                        entry_stat.st_ino,
                    ):
                        os.close(child_fd)
                        raise ValueError(f"directory changed while scanning: {entry_path}")
                    directories.append(entry_relative)
                    try:
                        visit(child_fd, entry_relative)
                    finally:
                        os.close(child_fd)
                elif stat.S_ISREG(entry_stat.st_mode):
                    files.append(entry_relative)
                else:
                    raise ValueError(
                        f"special filesystem entry is not supported: {entry_path}"
                    )

    visit(root_fd, Path())
    return tuple(directories), tuple(files)


def _scan_regular_tree(root: Path) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Return relative directories/files without following any path component."""
    root = _lexical_absolute_path(root)
    root_fd = open_directory_no_follow(root)
    try:
        return _scan_regular_tree_fd(root_fd, root)
    finally:
        os.close(root_fd)


def validate_regular_tree_no_follow(path: Path) -> None:
    """Reject a directory tree containing symlinks or special entries.

    This read-only validator intentionally has no Home requirement so an
    unsafe source can be classified before it is copied into the write area.
    """
    _scan_regular_tree(path.expanduser().absolute())


def validate_vault_tree_no_follow(vault: Path) -> None:
    """Reject a non-Home Vault, preserving the raw root's identity."""
    raw_vault = _lexical_absolute_path(vault)
    _require_lexical_home_path(raw_vault)
    validate_regular_tree_no_follow(raw_vault)


def _lexical_absolute_path(path: Path) -> Path:
    expanded = path.expanduser()
    if ".." in expanded.parts:
        raise ValueError(f"parent traversal is not supported: {path}")
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return expanded


def _open_child_directory_no_follow(
    directory_fd: int,
    name: str,
    display_path: Path,
) -> int:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ValueError(
                f"directory component must be ordinary and not a symlink: {display_path}"
            ) from exc
        raise
    if stat.S_ISDIR(os.fstat(descriptor).st_mode):
        return descriptor
    os.close(descriptor)
    raise ValueError(f"path changed into a non-directory: {display_path}")


def open_directory_no_follow(path: Path) -> int:
    """Open a directory through no-follow lexical components; caller closes."""
    absolute = _lexical_absolute_path(path)
    descriptor = os.open(
        absolute.anchor,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    walked = Path(absolute.anchor)
    try:
        for component in absolute.parts[1:]:
            walked /= component
            child = _open_child_directory_no_follow(descriptor, component, walked)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def open_regular_no_follow(path: Path) -> int:
    """Open a regular file through no-follow lexical components; caller closes."""
    absolute = _lexical_absolute_path(path)
    if absolute == Path(absolute.anchor):
        raise ValueError(f"regular file path is required: {path}")
    directory_fd = open_directory_no_follow(absolute.parent)
    try:
        try:
            descriptor = os.open(
                absolute.name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise ValueError(f"symlink is not supported: {absolute}") from exc
            raise
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            return descriptor
        os.close(descriptor)
        raise ValueError(f"path changed into a non-regular file: {absolute}")
    finally:
        os.close(directory_fd)


def _require_directory_path_identity(path: Path, expected_fd: int) -> None:
    current_fd = open_directory_no_follow(path)
    try:
        current = os.fstat(current_fd)
        expected = os.fstat(expected_fd)
        if (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino):
            raise ValueError(f"directory path changed during operation: {path}")
    finally:
        os.close(current_fd)


def _require_directory_fd_identity(
    actual_fd: int,
    expected_fd: int,
    path: Path,
) -> None:
    actual = os.fstat(actual_fd)
    expected = os.fstat(expected_fd)
    if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
        raise ValueError(f"directory path changed during operation: {path}")


def _open_pinned_vault(vault: Path) -> tuple[Path, int]:
    """Validate and pin one Home-contained Paper Vault root; caller closes."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        _scan_regular_tree_fd(root_fd, vault)
        _require_directory_path_identity(vault, root_fd)
    except Exception:
        os.close(root_fd)
        raise
    return vault, root_fd


def _open_pinned_vault_root(vault: Path) -> tuple[Path, int]:
    """Pin only the Home-contained Vault root for exact no-follow operations."""
    vault = _require_lexical_home_path(_lexical_absolute_path(vault))
    root_fd = open_directory_no_follow(vault)
    try:
        _require_directory_path_identity(vault, root_fd)
    except Exception:
        os.close(root_fd)
        raise
    return vault, root_fd


def snapshot_regular_tree_no_follow(
    path: Path,
) -> tuple[tuple[Path, ...], tuple[tuple[Path, str], ...]]:
    """Return a deterministic no-follow directory and SHA-256 snapshot."""
    root = _lexical_absolute_path(path)
    root_fd = open_directory_no_follow(root)
    try:
        return _snapshot_regular_tree_fd(root_fd, root)
    finally:
        os.close(root_fd)


def _open_relative_directory_no_follow(
    root_fd: int,
    relative: Path,
    root: Path,
) -> int:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"relative directory path required: {relative}")
    descriptor = os.dup(root_fd)
    walked = root
    try:
        for component in relative.parts:
            walked /= component
            child = _open_child_directory_no_follow(descriptor, component, walked)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_relative_regular_no_follow(
    root_fd: int,
    relative: Path,
    root: Path,
) -> int:
    if relative.is_absolute() or ".." in relative.parts or not relative.name:
        raise ValueError(f"relative regular file path required: {relative}")
    directory_fd = _open_relative_directory_no_follow(root_fd, relative.parent, root)
    try:
        try:
            descriptor = os.open(
                relative.name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise ValueError(f"symlink is not supported: {root / relative}") from exc
            raise
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            return descriptor
        os.close(descriptor)
        raise ValueError(f"path changed into a non-regular file: {root / relative}")
    finally:
        os.close(directory_fd)


def _read_regular_bytes_at(
    directory_fd: int,
    name: str,
    display_path: Path,
) -> tuple[bytes, tuple[int, int]]:
    """Read one stable ordinary entry through its already-pinned parent."""
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(f"symlink is not supported: {display_path}") from exc
        raise
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"path changed into a non-regular file: {display_path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise ValueError(f"file changed while reading: {display_path}")
    return b"".join(chunks), (after.st_dev, after.st_ino)


def _create_regular_bytes_at(
    directory_fd: int,
    name: str,
    data: bytes,
    display_path: Path,
) -> tuple[int, int]:
    """Create one ordinary entry without overwrite through a pinned parent."""
    descriptor = os.open(
        name,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=directory_fd,
    )
    opened = os.fstat(descriptor)
    identity = (opened.st_dev, opened.st_ino)
    digest = hashlib.sha256(data).hexdigest()
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    except Exception:
        os.close(descriptor)
        if not _unlink_owned_file_at(
            directory_fd,
            name,
            identity,
            expected_digest=digest,
        ):
            raise OSError(
                errno.EIO,
                f"created file could not be cleaned safely: {display_path}",
            )
        raise
    os.close(descriptor)
    return identity


def _snapshot_regular_tree_fd(
    root_fd: int,
    root: Path,
) -> tuple[tuple[Path, ...], tuple[tuple[Path, str], ...]]:
    directories, files = _scan_regular_tree_fd(root_fd, root)
    hashed_files: list[tuple[Path, str]] = []
    identities: dict[Path, tuple[int, int, int, int, int]] = {}
    for relative in files:
        descriptor = _open_relative_regular_no_follow(root_fd, relative, root)
        try:
            before = os.fstat(descriptor)
            digest = hashlib.sha256()
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError(f"file changed while snapshotting: {root / relative}")
        identities[relative] = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        hashed_files.append((relative, digest.hexdigest()))

    current_directories, current_files = _scan_regular_tree_fd(root_fd, root)
    if current_directories != directories or current_files != files:
        raise ValueError("directory tree changed while snapshotting")
    for relative in files:
        descriptor = _open_relative_regular_no_follow(root_fd, relative, root)
        try:
            final_stat = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (
            final_stat.st_dev,
            final_stat.st_ino,
            final_stat.st_size,
            final_stat.st_mtime_ns,
            final_stat.st_ctime_ns,
        ) != identities[relative]:
            raise ValueError(f"file changed after hashing: {root / relative}")
    return directories, tuple(hashed_files)


def _selection_token_from_pinned_root(
    path: Path,
    root_fd: int,
) -> VaultSelectionToken:
    _require_directory_path_identity(path, root_fd)
    before = os.fstat(root_fd)
    if not stat.S_ISDIR(before.st_mode):
        raise ValueError(f"Vault must be an existing directory: {path}")
    tree_snapshot = _snapshot_regular_tree_fd(root_fd, path)
    after = os.fstat(root_fd)
    root_identity = (before.st_dev, before.st_ino)
    if root_identity != (after.st_dev, after.st_ino):
        raise ValueError(f"Vault root changed while capturing selection: {path}")
    _require_directory_path_identity(path, root_fd)
    return VaultSelectionToken(path, root_identity, tree_snapshot)


def capture_vault_selection_token(path: Path) -> VaultSelectionToken:
    """Capture an immutable selection token through one pinned Vault root."""
    path = _require_lexical_home_path(_lexical_absolute_path(path))
    try:
        root_fd = open_directory_no_follow(path)
    except FileNotFoundError as exc:
        raise ValueError(f"Vault must be an existing directory: {path}") from exc
    try:
        return _selection_token_from_pinned_root(path, root_fd)
    finally:
        os.close(root_fd)


def _require_selection_token_matches(
    expected: VaultSelectionToken,
    current: VaultSelectionToken,
) -> None:
    if expected != current:
        raise ValueError(
            "Vault no longer matches the validated selection; selection was not saved"
        )


def _close_descriptor_quietly(descriptor: int | None) -> None:
    """Close a read-only guard descriptor without masking operation results."""
    if descriptor is None:
        return
    try:
        os.close(descriptor)
    except OSError:
        pass


def atomic_exchange_at_no_follow(
    first_parent_fd: int,
    first_name: str,
    second_parent_fd: int,
    second_name: str,
) -> None:
    """Atomically exchange two pinned single-level entries without following."""
    operation = _native_exchange_operation()
    for name in (first_name, second_name):
        if not name or name in {".", ".."} or Path(name).name != name:
            raise ValueError(f"atomic exchange requires a single entry name: {name!r}")
    if first_parent_fd == second_parent_fd and first_name == second_name:
        raise ValueError("atomic exchange paths must differ")
    first_stat = os.stat(
        first_name,
        dir_fd=first_parent_fd,
        follow_symlinks=False,
    )
    second_stat = os.stat(
        second_name,
        dir_fd=second_parent_fd,
        follow_symlinks=False,
    )
    first_is_directory = stat.S_ISDIR(first_stat.st_mode)
    second_is_directory = stat.S_ISDIR(second_stat.st_mode)
    first_is_file = stat.S_ISREG(first_stat.st_mode)
    second_is_file = stat.S_ISREG(second_stat.st_mode)
    if not (first_is_directory or first_is_file):
        raise ValueError(f"unsupported exchange entry: {first_name}")
    if not (second_is_directory or second_is_file):
        raise ValueError(f"unsupported exchange entry: {second_name}")
    if first_is_directory != second_is_directory:
        raise ValueError("atomic exchange entries must have the same type")
    if first_stat.st_dev != second_stat.st_dev:
        raise ValueError("atomic exchange entries must share one filesystem")
    if (first_stat.st_dev, first_stat.st_ino) == (
        second_stat.st_dev,
        second_stat.st_ino,
    ):
        raise ValueError("atomic exchange entries must be distinct")

    ctypes.set_errno(0)
    result = operation(
        first_parent_fd,
        os.fsencode(first_name),
        second_parent_fd,
        os.fsencode(second_name),
        _ATOMIC_EXCHANGE_FLAG,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            f"{first_name} <-> {second_name}",
        )


def _atomic_rename_no_replace_at(
    source_parent_fd: int,
    source_name: str,
    destination_parent_fd: int,
    destination_name: str,
) -> None:
    """Atomically rename one entry while refusing to replace another name."""
    operation = _native_exchange_operation()
    for name in (source_name, destination_name):
        if not name or name in {".", ".."} or Path(name).name != name:
            raise ValueError(f"atomic rename requires a single entry name: {name!r}")
    if source_parent_fd == destination_parent_fd and source_name == destination_name:
        raise ValueError("atomic rename paths must differ")
    if sys.platform == "darwin":
        flag = _DARWIN_ATOMIC_NO_REPLACE_FLAG
    elif sys.platform.startswith("linux"):
        flag = _LINUX_ATOMIC_NO_REPLACE_FLAG
    else:
        raise RuntimeError(
            f"atomic no-replace rename is unavailable on {sys.platform}"
        )

    ctypes.set_errno(0)
    result = operation(
        source_parent_fd,
        os.fsencode(source_name),
        destination_parent_fd,
        os.fsencode(destination_name),
        flag,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            f"{source_name} -> {destination_name}",
        )


def atomic_exchange_no_follow(first: Path, second: Path) -> None:
    """Atomically exchange two ordinary file or directory paths."""
    first = _lexical_absolute_path(first)
    second = _lexical_absolute_path(second)
    if first == second:
        raise ValueError("atomic exchange paths must differ")

    first_directory_fd: int | None = open_directory_no_follow(first.parent)
    second_directory_fd: int | None = None
    try:
        if first.parent == second.parent:
            second_directory_fd = os.dup(first_directory_fd)
        else:
            second_directory_fd = open_directory_no_follow(second.parent)
        atomic_exchange_at_no_follow(
            first_directory_fd,
            first.name,
            second_directory_fd,
            second.name,
        )
    finally:
        _close_descriptor_quietly(second_directory_fd)
        _close_descriptor_quietly(first_directory_fd)


def _unlink_owned_file(
    path: Path,
    identity: tuple[int, int],
    *,
    expected_bytes: bytes | None = None,
) -> bool:
    """Unlink only an unchanged caller-owned regular file snapshot."""
    directory_fd = open_directory_no_follow(path.parent)
    try:
        return _unlink_owned_file_at(
            directory_fd,
            path.name,
            identity,
            expected_digest=(
                hashlib.sha256(expected_bytes).hexdigest()
                if expected_bytes is not None
                else None
            ),
        )
    finally:
        os.close(directory_fd)


def _move_regular_no_overwrite_at(
    source_directory_fd: int,
    source_name: str,
    destination_directory_fd: int,
    destination_name: str,
    *,
    source_path: Path,
    destination_path: Path,
    expected_source_identity: tuple[int, int] | None = None,
    expected_source_bytes: bytes | None = None,
    guard_path: Path | None = None,
    guard_fd: int | None = None,
) -> None:
    """Atomically move one regular entry through pinned parents."""
    if (guard_path is None) != (guard_fd is None):
        raise ValueError("move guard path and descriptor must be provided together")

    def require_guard() -> None:
        if guard_path is not None and guard_fd is not None:
            _require_directory_path_identity(guard_path, guard_fd)

    source_identity: tuple[int, int] | None = None
    moved_identity: tuple[int, int] | None = None
    moved = False
    try:
        source_stat = os.stat(
            source_name,
            dir_fd=source_directory_fd,
            follow_symlinks=False,
        )
        if stat.S_ISLNK(source_stat.st_mode):
            raise ValueError(f"symlink is not supported: {source_path}")
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError(f"Paper must be a regular file: {source_path}")
        source_identity = (source_stat.st_dev, source_stat.st_ino)
        if (
            expected_source_identity is not None
            and source_identity != expected_source_identity
        ):
            raise ValueError(f"Paper changed before move: {source_path}")
        if expected_source_bytes is not None:
            current_bytes, current_identity = _read_regular_bytes_at(
                source_directory_fd,
                source_name,
                source_path,
            )
            if (
                current_identity != source_identity
                or current_bytes != expected_source_bytes
            ):
                raise ValueError(f"Paper changed before move: {source_path}")
        require_guard()
        _atomic_rename_no_replace_at(
            source_directory_fd,
            source_name,
            destination_directory_fd,
            destination_name,
        )
        moved = True
        moved_stat = os.stat(
            destination_name,
            dir_fd=destination_directory_fd,
            follow_symlinks=False,
        )
        moved_identity = (moved_stat.st_dev, moved_stat.st_ino)
        if moved_identity != source_identity:
            raise ValueError(f"Paper changed while moving: {source_path}")
        if expected_source_bytes is not None:
            moved_bytes, current_moved_identity = _read_regular_bytes_at(
                destination_directory_fd,
                destination_name,
                destination_path,
            )
            if (
                current_moved_identity != moved_identity
                or moved_bytes != expected_source_bytes
            ):
                raise ValueError(f"Paper changed while moving: {source_path}")
        require_guard()
    except Exception as move_error:
        if moved:
            try:
                current_destination = os.stat(
                    destination_name,
                    follow_symlinks=False,
                    dir_fd=destination_directory_fd,
                )
                current_identity = (
                    current_destination.st_dev,
                    current_destination.st_ino,
                )
                if moved_identity is None:
                    moved_identity = current_identity
                if current_identity != moved_identity:
                    raise ValueError("moved destination identity changed")
                try:
                    os.stat(
                        source_name,
                        dir_fd=source_directory_fd,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    pass
                else:
                    raise FileExistsError(
                        f"concurrent source path was preserved: {source_path}"
                    )
                _atomic_rename_no_replace_at(
                    destination_directory_fd,
                    destination_name,
                    source_directory_fd,
                    source_name,
                )
                restored = os.stat(
                    source_name,
                    dir_fd=source_directory_fd,
                    follow_symlinks=False,
                )
                if (restored.st_dev, restored.st_ino) != moved_identity:
                    raise ValueError("restored source identity does not match")
            except Exception as rollback_error:
                raise OSError(
                    errno.EIO,
                    "Paper move could not roll back safely; both locations were "
                    f"preserved at {source_path} and {destination_path}",
                ) from rollback_error
        raise


def _move_regular_no_overwrite(source: Path, destination: Path) -> None:
    """Move one regular path via pinned parent descriptors."""
    source_directory_fd = open_directory_no_follow(source.parent)
    destination_directory_fd = open_directory_no_follow(destination.parent)
    try:
        _move_regular_no_overwrite_at(
            source_directory_fd,
            source.name,
            destination_directory_fd,
            destination.name,
            source_path=source,
            destination_path=destination,
        )
    finally:
        os.close(destination_directory_fd)
        os.close(source_directory_fd)


def _copy_regular_file(source: Path, destination: Path) -> tuple[int, int]:
    source_fd = open_regular_no_follow(source)
    parent_fd: int | None = None
    destination_fd: int | None = None
    destination_identity: tuple[int, int] | None = None
    try:
        parent_fd = open_directory_no_follow(destination.parent)
        destination_fd = os.open(
            destination.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        destination_stat = os.fstat(destination_fd)
        destination_identity = (destination_stat.st_dev, destination_stat.st_ino)
        try:
            with os.fdopen(source_fd, "rb", closefd=False) as source_handle:
                with os.fdopen(
                    destination_fd, "wb", closefd=False
                ) as destination_handle:
                    shutil.copyfileobj(source_handle, destination_handle)
                    destination_handle.flush()
                    os.fsync(destination_handle.fileno())
        finally:
            if destination_fd is not None:
                os.close(destination_fd)
                destination_fd = None
    except Exception:
        if parent_fd is not None and destination_identity is not None:
            try:
                _unlink_owned_file_at(
                    parent_fd,
                    destination.name,
                    destination_identity,
                    expected_digest=None,
                )
            except OSError:
                pass
        raise
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        if parent_fd is not None:
            os.close(parent_fd)
        os.close(source_fd)
    assert destination_identity is not None
    return destination_identity


def _create_directory_path_no_follow(
    path: Path,
    *,
    leaf_must_be_new: bool,
) -> tuple[Path, int, list[_OwnedDirectory]]:
    absolute = _require_lexical_home_path(path)
    home = _lexical_absolute_path(_current_home())
    relative = absolute.relative_to(home)
    current_fd = open_directory_no_follow(home)
    records: list[_OwnedDirectory] = []
    walked = home
    try:
        if not relative.parts:
            if leaf_must_be_new:
                raise FileExistsError(f"destination already exists: {absolute}")
            return absolute, current_fd, records
        for index, component in enumerate(relative.parts):
            child_path = walked / component
            is_leaf = index == len(relative.parts) - 1
            try:
                child_stat = os.stat(
                    component,
                    dir_fd=current_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                os.mkdir(component, mode=0o700, dir_fd=current_fd)
                child_stat = os.stat(
                    component,
                    dir_fd=current_fd,
                    follow_symlinks=False,
                )
                identity = (child_stat.st_dev, child_stat.st_ino)
                records.append(
                    _OwnedDirectory(
                        os.dup(current_fd),
                        component,
                        identity,
                        child_path,
                    )
                )
            else:
                if is_leaf and leaf_must_be_new:
                    raise FileExistsError(f"destination already exists: {absolute}")
            child_fd = _open_child_directory_no_follow(
                current_fd,
                component,
                child_path,
            )
            opened_stat = os.fstat(child_fd)
            if (opened_stat.st_dev, opened_stat.st_ino) != (
                child_stat.st_dev,
                child_stat.st_ino,
            ):
                os.close(child_fd)
                raise ValueError(f"directory changed while opening: {child_path}")
            os.close(current_fd)
            current_fd = child_fd
            walked = child_path
        return absolute, current_fd, records
    except Exception:
        os.close(current_fd)
        _cleanup_owned_directories(records)
        raise


def _mkdir_relative_owned(
    root_fd: int,
    root: Path,
    relative: Path,
) -> _OwnedDirectory:
    parent_fd = _open_relative_directory_no_follow(root_fd, relative.parent, root)
    path = root / relative
    identity: tuple[int, int] | None = None
    try:
        os.mkdir(relative.name, mode=0o700, dir_fd=parent_fd)
        child_stat = os.stat(
            relative.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        identity = (child_stat.st_dev, child_stat.st_ino)
        child_fd = _open_child_directory_no_follow(parent_fd, relative.name, path)
        try:
            opened_stat = os.fstat(child_fd)
            if (opened_stat.st_dev, opened_stat.st_ino) != identity:
                raise ValueError(f"directory changed while creating: {path}")
        finally:
            os.close(child_fd)
        return _OwnedDirectory(parent_fd, relative.name, identity, path)
    except Exception:
        if identity is not None:
            try:
                _rmdir_owned_directory_at(parent_fd, relative.name, identity)
            except OSError:
                pass
        os.close(parent_fd)
        raise


def _copy_regular_file_at(
    source_root_fd: int,
    source_root: Path,
    destination_root_fd: int,
    destination_root: Path,
    relative: Path,
) -> _OwnedFile:
    source_fd = _open_relative_regular_no_follow(source_root_fd, relative, source_root)
    destination_parent_fd = _open_relative_directory_no_follow(
        destination_root_fd,
        relative.parent,
        destination_root,
    )
    destination_fd: int | None = None
    identity: tuple[int, int] | None = None
    digest = hashlib.sha256()
    try:
        before = os.fstat(source_fd)
        destination_fd = os.open(
            relative.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=destination_parent_fd,
        )
        destination_stat = os.fstat(destination_fd)
        identity = (destination_stat.st_dev, destination_stat.st_ino)
        while chunk := os.read(source_fd, 1024 * 1024):
            view = memoryview(chunk)
            while view:
                written = os.write(destination_fd, view)
                digest.update(view[:written])
                view = view[written:]
        os.fsync(destination_fd)
        after = os.fstat(source_fd)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError(f"source changed while copying: {source_root / relative}")
        os.close(destination_fd)
        destination_fd = None
        return _OwnedFile(
            destination_parent_fd,
            relative.name,
            identity,
            digest.hexdigest(),
            destination_root / relative,
        )
    except Exception:
        if destination_fd is not None:
            os.close(destination_fd)
        if identity is not None:
            _unlink_owned_file_at(
                destination_parent_fd,
                relative.name,
                identity,
                expected_digest=digest.hexdigest(),
            )
        os.close(destination_parent_fd)
        raise
    finally:
        os.close(source_fd)


def _unlink_owned_file_at(
    parent_fd: int,
    name: str,
    identity: tuple[int, int],
    *,
    expected_digest: str | None,
) -> bool:
    """Isolate, verify, then unlink one exact regular file.

    The random quarantine rename is the mutation boundary. If the named entry
    was replaced immediately before that boundary, the replacement is restored
    and retained instead of being deleted.
    """
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return False
    if not stat.S_ISREG(current.st_mode) or (
        current.st_dev,
        current.st_ino,
    ) != identity:
        return False

    quarantine_name = f".{name}.{secrets.token_hex(16)}.keikeu-unlink"
    try:
        _atomic_rename_no_replace_at(
            parent_fd,
            name,
            parent_fd,
            quarantine_name,
        )
    except FileNotFoundError:
        return False

    try:
        data, isolated_identity = _read_regular_bytes_at(
            parent_fd,
            quarantine_name,
            Path(quarantine_name),
        )
        matches = isolated_identity == identity and (
            expected_digest is None
            or hashlib.sha256(data).hexdigest() == expected_digest
        )
    except (OSError, ValueError):
        matches = False
        isolated_identity = None

    if not matches:
        _restore_isolated_entry_at(
            parent_fd,
            quarantine_name,
            name,
            isolated_identity,
        )
        return False

    try:
        os.unlink(quarantine_name, dir_fd=parent_fd)
    except Exception:
        _restore_isolated_entry_at(
            parent_fd,
            quarantine_name,
            name,
            isolated_identity,
        )
        raise
    return True


def _restore_isolated_entry_at(
    parent_fd: int,
    isolated_name: str,
    original_name: str,
    isolated_identity: tuple[int, int] | None,
) -> None:
    """Restore one quarantined entry without overwriting a concurrent name."""
    if isolated_identity is None:
        raise OSError(
            errno.EIO,
            f"isolated entry could not be identified and was preserved: {isolated_name}",
        )
    try:
        current = os.stat(
            isolated_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise OSError(
            errno.EIO,
            f"isolated entry changed and current paths were preserved: {isolated_name}",
        ) from exc
    if (current.st_dev, current.st_ino) != isolated_identity:
        raise OSError(
            errno.EIO,
            f"isolated entry changed and current paths were preserved: {isolated_name}",
        )
    try:
        os.stat(original_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise OSError(
            errno.EIO,
            "isolated entry could not be restored without overwriting a concurrent "
            f"path; both were preserved: {original_name}, {isolated_name}",
        )
    _atomic_rename_no_replace_at(
        parent_fd,
        isolated_name,
        parent_fd,
        original_name,
    )
    restored = os.stat(original_name, dir_fd=parent_fd, follow_symlinks=False)
    if (restored.st_dev, restored.st_ino) != isolated_identity:
        raise OSError(
            errno.EIO,
            f"isolated entry restore changed identity: {original_name}",
        )


def _cleanup_owned_files(records: list[_OwnedFile]) -> None:
    for record in reversed(records):
        try:
            _unlink_owned_file_at(
                record.parent_fd,
                record.name,
                record.identity,
                expected_digest=record.digest,
            )
        finally:
            os.close(record.parent_fd)


def _rmdir_owned_directory_at(
    parent_fd: int,
    name: str,
    identity: tuple[int, int],
) -> bool:
    """Remove one exact empty directory after isolating its current name."""
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return False
    if not stat.S_ISDIR(current.st_mode) or (
        current.st_dev,
        current.st_ino,
    ) != identity:
        return False

    quarantine_name = f".{name}.{secrets.token_hex(16)}.keikeu-rmdir"
    try:
        _atomic_rename_no_replace_at(
            parent_fd,
            name,
            parent_fd,
            quarantine_name,
        )
    except FileNotFoundError:
        return False

    isolated_fd: int | None = None
    isolated_identity: tuple[int, int] | None = None
    try:
        isolated_fd = _open_child_directory_no_follow(
            parent_fd,
            quarantine_name,
            Path(quarantine_name),
        )
        opened = os.fstat(isolated_fd)
        isolated_identity = (opened.st_dev, opened.st_ino)
        with os.scandir(isolated_fd) as entries:
            empty = next(entries, None) is None
    except (OSError, ValueError):
        empty = False
    finally:
        if isolated_fd is not None:
            os.close(isolated_fd)

    if isolated_identity != identity or not empty:
        _restore_isolated_entry_at(
            parent_fd,
            quarantine_name,
            name,
            isolated_identity,
        )
        return False

    try:
        os.rmdir(quarantine_name, dir_fd=parent_fd)
    except Exception:
        _restore_isolated_entry_at(
            parent_fd,
            quarantine_name,
            name,
            isolated_identity,
        )
        raise
    return True


def _cleanup_owned_directories(records: list[_OwnedDirectory]) -> None:
    for record in reversed(records):
        try:
            try:
                _rmdir_owned_directory_at(
                    record.parent_fd,
                    record.name,
                    record.identity,
                )
            except OSError:
                pass
        finally:
            os.close(record.parent_fd)


def _release_owned_files(records: list[_OwnedFile]) -> None:
    for record in records:
        os.close(record.parent_fd)


def _release_owned_directories(records: list[_OwnedDirectory]) -> None:
    for record in records:
        os.close(record.parent_fd)


def _owned_directories_still_named(records: list[_OwnedDirectory]) -> bool:
    for record in records:
        try:
            current = os.stat(
                record.name,
                dir_fd=record.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return False
        if not stat.S_ISDIR(current.st_mode) or (
            current.st_dev,
            current.st_ino,
        ) != record.identity:
            return False
    return True


def copy_vault_no_follow(source: Path, destination: Path) -> Path:
    """Byte-copy one Vault tree into a new Home path without symlink entries.

    ``FileExistsError`` means the destination was not brand-new. Unsupported
    entries and verification failures raise ``ValueError``; ordinary I/O
    failures retain their ``OSError`` type. The source is never changed.
    """
    source = _lexical_absolute_path(source)
    destination = _require_lexical_home_path(destination)
    if destination == source or source in destination.parents:
        raise ValueError("destination cannot be the source or one of its descendants")
    source_root_fd = open_directory_no_follow(source)
    destination_root_fd: int | None = None
    created_files: list[_OwnedFile] = []
    created_directories: list[_OwnedDirectory] = []
    try:
        _require_directory_path_identity(source, source_root_fd)
        source_before = _snapshot_regular_tree_fd(source_root_fd, source)
        source_directories = source_before[0]
        source_files = tuple(relative for relative, _digest in source_before[1])
        destination, destination_root_fd, root_records = (
            _create_directory_path_no_follow(
                destination,
                leaf_must_be_new=True,
            )
        )
        created_directories.extend(root_records)
        for relative in source_directories:
            created_directories.append(
                _mkdir_relative_owned(
                    destination_root_fd,
                    destination,
                    relative,
                )
            )
        for relative in source_files:
            created_files.append(
                _copy_regular_file_at(
                    source_root_fd,
                    source,
                    destination_root_fd,
                    destination,
                    relative,
                )
            )

        source_after = _snapshot_regular_tree_fd(source_root_fd, source)
        destination_snapshot = _snapshot_regular_tree_fd(
            destination_root_fd,
            destination,
        )
        if source_before != source_after or source_after != destination_snapshot:
            raise ValueError("copied Vault SHA snapshot does not match its source")
        _require_directory_path_identity(source, source_root_fd)
        _require_directory_path_identity(destination, destination_root_fd)
        if not _owned_directories_still_named(created_directories):
            raise ValueError("destination path changed while copying")
    except Exception:
        _cleanup_owned_files(created_files)
        _cleanup_owned_directories(created_directories)
        raise
    else:
        _release_owned_files(created_files)
        _release_owned_directories(created_directories)
    finally:
        if destination_root_fd is not None:
            os.close(destination_root_fd)
        os.close(source_root_fd)
    return destination


def init_vault(path: Path) -> None:
    """Create the current Paper layout without changing existing user data.

    New vaults contain ``cache/``, ``.trash/cache/``, and a v3 empty index.
    Existing Outline directories and an existing index are left untouched so
    this helper cannot damage a vault that still needs migration.
    """
    path, root_fd, path_records = _create_directory_path_no_follow(
        path,
        leaf_must_be_new=False,
    )
    layout_records: list[_OwnedDirectory] = []
    try:
        validate_regular_tree_no_follow(path)
        for relative in (Path("cache"), Path(".trash"), Path(".trash/cache")):
            try:
                directory_fd = _open_relative_directory_no_follow(
                    root_fd,
                    relative,
                    path,
                )
            except FileNotFoundError:
                layout_records.append(_mkdir_relative_owned(root_fd, path, relative))
            else:
                os.close(directory_fd)
        _require_directory_path_identity(path, root_fd)
        try:
            index_stat = os.stat(
                "keikeu_index.json",
                dir_fd=root_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            from keikeu_core.indexer import save_index_at

            save_index_at(root_fd, _EMPTY_INDEX)
        else:
            if stat.S_ISLNK(index_stat.st_mode) or not stat.S_ISREG(index_stat.st_mode):
                raise ValueError(f"index must be a regular file: {_index_path(path)}")
        _require_directory_path_identity(path, root_fd)
    finally:
        os.close(root_fd)
        _release_owned_directories(layout_records)
        _release_owned_directories(path_records)


def is_vault(path: Path) -> bool:
    """Return whether ``path`` is a supported Paper Vault or rebuildable."""
    try:
        path = _lexical_absolute_path(path)
        root_fd = open_directory_no_follow(path)
        try:
            cache_fd = _open_relative_directory_no_follow(
                root_fd,
                Path("cache"),
                path,
            )
            os.close(cache_fd)
            try:
                index_stat = os.stat(
                    "keikeu_index.json",
                    dir_fd=root_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                trash_fd = _open_relative_directory_no_follow(
                    root_fd,
                    Path(".trash/cache"),
                    path,
                )
                os.close(trash_fd)
                return True
            if not stat.S_ISREG(index_stat.st_mode):
                return False
            descriptor = _open_relative_regular_no_follow(
                root_fd,
                Path("keikeu_index.json"),
                path,
            )
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                try:
                    data = json.load(handle)
                except (OSError, ValueError):
                    return True
            version = data.get("version") if isinstance(data, dict) else None
            if type(version) is int:
                return version in {2, 3}
            return True
        finally:
            os.close(root_fd)
    except (OSError, ValueError):
        return False


def vault_index_version(vault: Path) -> int | None:
    """Read the root index version through exact no-follow components."""
    vault = vault.expanduser().absolute()
    index_path = _index_path(vault)
    try:
        descriptor = open_regular_no_follow(index_path)
    except FileNotFoundError:
        return None
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if type(version) is int else None


def validate_vault_papers(vault: Path) -> None:
    """Strictly validate active and recovery Paper Markdown without writing."""
    from keikeu_core.markdown_io import read_paper_snapshot

    raw_vault = _lexical_absolute_path(vault)
    validate_vault_tree_no_follow(raw_vault)
    if not is_vault(raw_vault):
        raise ValueError(f"Vault is not structurally supported: {raw_vault}")
    active, active_errors = scan_active_papers(raw_vault)
    try:
        trashed, trash_errors = scan_trashed_papers(raw_vault)
    except FileNotFoundError:
        trashed, trash_errors = [], []
    errors = [*active_errors, *trash_errors]
    if errors:
        raise ValueError(
            f"unsupported Paper path {errors[0]['path']}: {errors[0]['reason']}"
        )
    codes: dict[str, Path] = {}
    for relative in [*active, *trashed]:
        path = raw_vault / relative
        paper, _source_bytes = read_paper_snapshot(path)
        if relative.parts[0] == "cache" and path.stem != paper.code:
            raise ValueError(
                f"Paper filename and frontmatter code do not match: {path}"
            )
        previous = codes.get(paper.code)
        if previous is not None:
            raise ValueError(
                f"duplicate Paper code across active/Trash: {paper.code} "
                f"({previous}, {relative})"
            )
        codes[paper.code] = relative


def _direct_paper_relative_path(
    vault: Path,
    candidate: str | Path,
    parent: tuple[str, ...],
) -> Path:
    candidate_path = Path(candidate).expanduser()
    if ".." in candidate_path.parts:
        expected = "/".join(parent) + "/*.md"
        raise ValueError(f"expected {expected}")
    if candidate_path.is_absolute():
        try:
            relative = candidate_path.relative_to(vault)
        except ValueError as exc:
            raise ValueError(f"Paper path is outside the selected Vault: {candidate}") from exc
    else:
        relative = candidate_path
    if (
        relative.parts[: len(parent)] != parent
        or len(relative.parts) != len(parent) + 1
        or relative.suffix != ".md"
        or not relative.stem
    ):
        expected = "/".join(parent) + "/*.md"
        raise ValueError(f"expected {expected}")
    return relative


def _supported_paper_relative_path(
    vault: Path,
    candidate: str | Path,
    base: tuple[str, ...],
) -> Path:
    candidate_path = Path(candidate).expanduser()
    expected = "/".join(base) + "/[folder/]Paper.md"
    if ".." in candidate_path.parts:
        raise ValueError(f"expected {expected}")
    if candidate_path.is_absolute():
        try:
            relative = candidate_path.relative_to(vault)
        except ValueError as exc:
            raise ValueError(
                f"Paper path is outside the selected Vault: {candidate}"
            ) from exc
    else:
        relative = candidate_path
    if relative.parts[: len(base)] != base:
        raise ValueError(f"expected {expected}")
    remainder = relative.parts[len(base) :]
    if len(remainder) not in {1, 2} or relative.suffix != ".md" or not relative.stem:
        raise ValueError(f"expected {expected}")
    if len(remainder) == 2:
        if validate_folder_name(remainder[0]) != remainder[0]:
            raise ValueError("folder name must not have outer whitespace")
    return relative


def _paper_scan_error(path: Path, reason: str) -> dict[str, str]:
    return {"path": str(path), "reason": reason}


def _scan_paper_area_at(
    root_fd: int,
    vault: Path,
    base: Path,
) -> tuple[list[Path], list[dict[str, str]]]:
    """Scan root and one folder level without following any entry."""
    papers: list[Path] = []
    errors: list[dict[str, str]] = []
    base_fd = _open_relative_directory_no_follow(root_fd, base, vault)
    try:
        with os.scandir(base_fd) as entries:
            root_entries = sorted(entries, key=lambda entry: entry.name)
        for entry in root_entries:
            relative = base / entry.name
            path = vault / relative
            try:
                entry_stat = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(entry_stat.st_mode):
                    errors.append(_paper_scan_error(relative, "symlink is not supported"))
                    continue
                if stat.S_ISREG(entry_stat.st_mode):
                    if relative.suffix == ".md":
                        papers.append(relative)
                    continue
                if not stat.S_ISDIR(entry_stat.st_mode):
                    errors.append(
                        _paper_scan_error(relative, "special filesystem entry is not supported")
                    )
                    continue
                try:
                    if validate_folder_name(entry.name) != entry.name:
                        raise ValueError("folder name must not have outer whitespace")
                except ValueError as exc:
                    errors.append(_paper_scan_error(relative, str(exc)))
                    continue
                folder_fd = _open_child_directory_no_follow(base_fd, entry.name, path)
                try:
                    folder_papers: list[Path] = []
                    folder_errors: list[dict[str, str]] = []
                    opened = os.fstat(folder_fd)
                    if (opened.st_dev, opened.st_ino) != (
                        entry_stat.st_dev,
                        entry_stat.st_ino,
                    ):
                        raise ValueError(f"directory changed while scanning: {path}")
                    with os.scandir(folder_fd) as children:
                        folder_entries = sorted(children, key=lambda child: child.name)
                    for child in folder_entries:
                        child_relative = relative / child.name
                        child_stat = child.stat(follow_symlinks=False)
                        if stat.S_ISLNK(child_stat.st_mode):
                            folder_errors.append(
                                _paper_scan_error(
                                    child_relative,
                                    "symlink is not supported",
                                )
                            )
                        elif stat.S_ISREG(child_stat.st_mode):
                            if child_relative.suffix == ".md":
                                folder_papers.append(child_relative)
                        elif stat.S_ISDIR(child_stat.st_mode):
                            folder_errors.append(
                                _paper_scan_error(
                                    child_relative,
                                    "Paper folders support one level only",
                                )
                            )
                        else:
                            folder_errors.append(
                                _paper_scan_error(
                                    child_relative,
                                    "special filesystem entry is not supported",
                                )
                            )
                    _require_directory_path_identity(path, folder_fd)
                    papers.extend(folder_papers)
                    errors.extend(folder_errors)
                finally:
                    os.close(folder_fd)
            except (OSError, ValueError) as exc:
                errors.append(_paper_scan_error(relative, str(exc)))
        _require_directory_path_identity(vault / base, base_fd)
    finally:
        os.close(base_fd)
    papers.sort(key=str)
    errors.sort(key=lambda item: (item["path"], item["reason"]))
    return papers, errors


def _paper_code_exists_at(
    root_fd: int,
    vault: Path,
    code: str,
    *,
    parse_code: Callable[[bytes], str],
    excluding: Path | None = None,
) -> bool:
    """Check one code across supported paths on a caller-pinned Vault root."""
    for base in (Path("cache"), Path(".trash/cache")):
        try:
            paths, errors = _scan_paper_area_at(root_fd, vault, base)
        except FileNotFoundError:
            continue
        if any(
            Path(error["path"]).suffix == ".md"
            and Path(error["path"]).stem == code
            for error in errors
        ):
            return True
        for relative in paths:
            if relative == excluding:
                continue
            if relative.stem == code:
                return True
            parent_fd = _open_relative_directory_no_follow(
                root_fd,
                relative.parent,
                vault,
            )
            try:
                data, _identity = _read_regular_bytes_at(
                    parent_fd,
                    relative.name,
                    vault / relative,
                )
                _require_directory_path_identity(vault / relative.parent, parent_fd)
            except (OSError, ValueError):
                continue
            finally:
                os.close(parent_fd)
            try:
                if parse_code(data) == code:
                    return True
            except (ValueError, UnicodeError):
                continue
    return False


def _scan_paper_area(
    vault: Path,
    base: Path,
) -> tuple[list[Path], list[dict[str, str]]]:
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        result = _scan_paper_area_at(root_fd, vault, base)
        _require_directory_path_identity(vault, root_fd)
        return result
    finally:
        os.close(root_fd)


def scan_active_papers(vault: Path) -> tuple[list[Path], list[dict[str, str]]]:
    """Return supported active Paper paths plus isolated path errors."""
    return _scan_paper_area(vault, Path("cache"))


def _list_folder_names(vault: Path, base: Path) -> list[str]:
    vault, root_fd = _open_pinned_vault_root(vault)
    base_fd: int | None = None
    try:
        base_fd = _open_relative_directory_no_follow(root_fd, base, vault)
        with os.scandir(base_fd) as entries:
            candidates = sorted(entries, key=lambda entry: _folder_name_key(entry.name))
        folders: list[str] = []
        for entry in candidates:
            try:
                entry_stat = entry.stat(follow_symlinks=False)
                if not stat.S_ISDIR(entry_stat.st_mode):
                    continue
                if validate_folder_name(entry.name) != entry.name:
                    continue
                child_fd = _open_child_directory_no_follow(
                    base_fd,
                    entry.name,
                    vault / base / entry.name,
                )
                os.close(child_fd)
                folders.append(entry.name)
            except (OSError, ValueError):
                continue
        _require_directory_path_identity(vault / base, base_fd)
        return folders
    finally:
        if base_fd is not None:
            os.close(base_fd)
        os.close(root_fd)


def list_active_folders(vault: Path) -> list[str]:
    """Return sorted valid one-level active folder names, including empty ones."""
    return _list_folder_names(vault, Path("cache"))


def list_trashed_folders(vault: Path) -> list[str]:
    """Return sorted valid one-level Trash folder names, including empty ones."""
    return _list_folder_names(vault, Path(".trash/cache"))


def scan_trashed_papers(vault: Path) -> tuple[list[Path], list[dict[str, str]]]:
    """Return supported Trash Paper paths plus isolated path errors."""
    try:
        return _scan_paper_area(vault, Path(".trash/cache"))
    except FileNotFoundError:
        return [], []


def list_active_papers(vault: Path) -> list[Path]:
    """Return sorted safe root/one-folder active Paper paths."""
    papers, _errors = scan_active_papers(vault)
    return papers


def next_paper_code(
    vault: Path,
    on_date: date | datetime | None = None,
    *,
    parse_code: Callable[[bytes], str] | None = None,
) -> str:
    """Allocate the next code across every supported active and Trash path."""
    if on_date is None:
        day = datetime.now().date()
    elif isinstance(on_date, datetime):
        day = on_date.date()
    elif isinstance(on_date, date):
        day = on_date
    else:
        raise ValueError("on_date must be a date or datetime")
    prefix = f"K-{day.strftime('%Y%m%d')}-"
    used_sequences: set[int] = set()
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        active_paths, _active_errors = _scan_paper_area_at(
            root_fd,
            vault,
            Path("cache"),
        )
        try:
            trash_paths, _trash_errors = _scan_paper_area_at(
                root_fd,
                vault,
                Path(".trash/cache"),
            )
        except FileNotFoundError:
            trash_paths = []
        for relative in [*active_paths, *trash_paths]:
            candidates = [relative.stem]
            if parse_code is not None:
                parent_fd = _open_relative_directory_no_follow(
                    root_fd,
                    relative.parent,
                    vault,
                )
                try:
                    data, _identity = _read_regular_bytes_at(
                        parent_fd,
                        relative.name,
                        vault / relative,
                    )
                    _require_directory_path_identity(
                        vault / relative.parent,
                        parent_fd,
                    )
                    candidates.append(parse_code(data))
                except (OSError, ValueError, UnicodeError):
                    pass
                finally:
                    os.close(parent_fd)
            for candidate in candidates:
                if not candidate.startswith(prefix):
                    continue
                match = _PAPER_CODE_FILENAME_RE.fullmatch(candidate)
                if match is not None:
                    used_sequences.add(int(match.group(1)))
        _require_directory_path_identity(vault, root_fd)
    finally:
        os.close(root_fd)
    for sequence in range(1, 1000):
        if sequence not in used_sequences:
            return f"{prefix}{sequence:03d}"
    raise ValueError(f"all Paper codes for {day.isoformat()} are in use")


def resolve_active_paper_path(
    vault: Path,
    candidate: str | Path,
    *,
    must_exist: bool = True,
) -> Path:
    """Resolve one root/one-folder active Paper safely."""
    return _resolve_supported_paper_path(
        vault, candidate, ("cache",), must_exist=must_exist
    )


def resolve_trashed_paper_path(
    vault: Path,
    candidate: str | Path,
    *,
    must_exist: bool = True,
) -> Path:
    """Resolve one root/one-folder Trash Paper safely."""
    return _resolve_supported_paper_path(
        vault, candidate, (".trash", "cache"), must_exist=must_exist
    )


def _resolve_supported_paper_path(
    vault: Path,
    candidate: str | Path,
    base: tuple[str, ...],
    *,
    must_exist: bool,
) -> Path:
    raw_vault = _lexical_absolute_path(vault)
    canonical_vault = _require_lexical_home_path(raw_vault)
    relative = _supported_paper_relative_path(canonical_vault, candidate, base)
    target = canonical_vault / relative
    vault_fd = open_directory_no_follow(canonical_vault)
    parent_fd: int | None = None
    try:
        parent_fd = _open_relative_directory_no_follow(
            vault_fd,
            relative.parent,
            canonical_vault,
        )
        try:
            target_stat = os.stat(
                relative.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            if must_exist:
                raise
        else:
            if stat.S_ISLNK(target_stat.st_mode):
                raise ValueError(f"symlink is not supported: {target}")
            if not stat.S_ISREG(target_stat.st_mode):
                raise ValueError(f"Paper must be a regular file: {target}")
        _require_directory_path_identity(target.parent, parent_fd)
        return target
    finally:
        if parent_fd is not None:
            os.close(parent_fd)
        os.close(vault_fd)


def _stored_folder_name(folder: str | Path) -> str:
    name = str(folder)
    if Path(name).name != name or validate_folder_name(name) != name:
        raise ValueError("folder reference must be one exact stored name")
    return name


def _semantic_target_folder_name_at(
    root_fd: int,
    vault: Path,
    base: Path,
    requested_name: str,
) -> str:
    """Reuse an existing NFC+casefold-equivalent folder or keep the request."""
    base_fd = _open_relative_directory_no_follow(root_fd, base, vault)
    try:
        return (
            _semantic_folder_collision_at(base_fd, requested_name)
            or requested_name
        )
    finally:
        os.close(base_fd)


def _ensure_relative_directory_at(
    root_fd: int,
    vault: Path,
    relative: Path,
) -> tuple[int, _OwnedDirectory | None]:
    try:
        return _open_relative_directory_no_follow(root_fd, relative, vault), None
    except FileNotFoundError:
        record = _mkdir_relative_owned(root_fd, vault, relative)
        try:
            descriptor = _open_relative_directory_no_follow(root_fd, relative, vault)
        except Exception:
            _cleanup_owned_directories([record])
            raise
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != record.identity:
            os.close(descriptor)
            _cleanup_owned_directories([record])
            raise ValueError(f"directory changed while creating: {vault / relative}")
        return descriptor, record


def _release_or_cleanup_directory(
    record: _OwnedDirectory | None,
    *,
    keep: bool,
) -> None:
    if record is None:
        return
    if keep:
        _release_owned_directories([record])
    else:
        _cleanup_owned_directories([record])


def _move_supported_paper_at(
    vault: Path,
    root_fd: int,
    source_relative: Path,
    destination_relative: Path,
    *,
    expected_source_parent_fd: int | None = None,
    expected_destination_parent_fd: int | None = None,
) -> Path:
    from keikeu_core.markdown_io import parse_paper_bytes

    source = vault / source_relative
    destination = vault / destination_relative
    source_parent_fd = _open_relative_directory_no_follow(
        root_fd,
        source_relative.parent,
        vault,
    )
    destination_parent_fd: int | None = None
    try:
        if expected_source_parent_fd is not None:
            _require_directory_fd_identity(
                source_parent_fd,
                expected_source_parent_fd,
                source.parent,
            )
        destination_parent_fd = _open_relative_directory_no_follow(
            root_fd,
            destination_relative.parent,
            vault,
        )
        if expected_destination_parent_fd is not None:
            _require_directory_fd_identity(
                destination_parent_fd,
                expected_destination_parent_fd,
                destination.parent,
            )
        source_bytes, source_identity = _read_regular_bytes_at(
            source_parent_fd,
            source_relative.name,
            source,
        )
        paper = parse_paper_bytes(source_bytes)
        if source_relative.parts[0] == "cache" and source_relative.name != f"{paper.code}.md":
            raise ValueError(
                f"Paper filename and frontmatter code do not match: {source}"
            )
        if destination_relative.name != f"{paper.code}.md":
            raise ValueError("Paper moves must preserve the immutable code filename")
        if _paper_code_exists_at(
            root_fd,
            vault,
            paper.code,
            parse_code=lambda data: parse_paper_bytes(data).code,
            excluding=source_relative,
        ):
            raise ValueError(f"duplicate Paper code blocks mutation: {paper.code}")
        _require_directory_path_identity(source.parent, source_parent_fd)
        _require_directory_path_identity(destination.parent, destination_parent_fd)
        _move_regular_no_overwrite_at(
            source_parent_fd,
            source_relative.name,
            destination_parent_fd,
            destination_relative.name,
            source_path=source,
            destination_path=destination,
            expected_source_identity=source_identity,
            expected_source_bytes=source_bytes,
            guard_path=vault,
            guard_fd=root_fd,
        )
        try:
            _require_directory_path_identity(source.parent, source_parent_fd)
            _require_directory_path_identity(destination.parent, destination_parent_fd)
        except Exception as guard_error:
            try:
                _move_regular_no_overwrite_at(
                    destination_parent_fd,
                    destination_relative.name,
                    source_parent_fd,
                    source_relative.name,
                    source_path=destination,
                    destination_path=source,
                    expected_source_identity=source_identity,
                    expected_source_bytes=source_bytes,
                )
            except Exception as rollback_error:
                raise OSError(
                    errno.EIO,
                    "Paper move parent changed; both locations were preserved at "
                    f"{source} and {destination}",
                ) from rollback_error
            raise guard_error
        return destination
    finally:
        if destination_parent_fd is not None:
            os.close(destination_parent_fd)
        os.close(source_parent_fd)


def _result_for_move(
    vault: Path,
    root_fd: int,
    source_relative: Path,
    destination_relative: Path,
    *,
    expected_source_parent_fd: int | None = None,
    expected_destination_parent_fd: int | None = None,
) -> PathOperationResult:
    try:
        destination = _move_supported_paper_at(
            vault,
            root_fd,
            source_relative,
            destination_relative,
            expected_source_parent_fd=expected_source_parent_fd,
            expected_destination_parent_fd=expected_destination_parent_fd,
        )
    except (OSError, ValueError) as exc:
        return PathOperationResult(source=source_relative, error=str(exc))
    return PathOperationResult(
        source=source_relative,
        destination=destination.relative_to(vault),
    )


def _validate_supported_paper_at(
    vault: Path,
    root_fd: int,
    relative: Path,
) -> None:
    from keikeu_core.markdown_io import parse_paper_bytes

    parent_fd = _open_relative_directory_no_follow(
        root_fd,
        relative.parent,
        vault,
    )
    try:
        data, _identity = _read_regular_bytes_at(
            parent_fd,
            relative.name,
            vault / relative,
        )
        paper = parse_paper_bytes(data)
        if relative.name != f"{paper.code}.md":
            raise ValueError(
                f"Paper filename and frontmatter code do not match: {vault / relative}"
            )
        if _paper_code_exists_at(
            root_fd,
            vault,
            paper.code,
            parse_code=lambda value: parse_paper_bytes(value).code,
            excluding=relative,
        ):
            raise ValueError(f"duplicate Paper code blocks mutation: {paper.code}")
        _require_directory_path_identity(vault / relative.parent, parent_fd)
    finally:
        os.close(parent_fd)


def _remove_empty_folder_at(
    vault: Path,
    root_fd: int,
    relative: Path,
    *,
    expected_folder_fd: int | None = None,
) -> bool:
    parent_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
    folder_fd: int | None = None
    try:
        try:
            folder_fd = _open_relative_directory_no_follow(root_fd, relative, vault)
        except FileNotFoundError:
            if expected_folder_fd is not None:
                raise ValueError(
                    f"directory path changed during operation: {vault / relative}"
                )
            return True
        opened = os.fstat(folder_fd)
        identity = (opened.st_dev, opened.st_ino)
        if expected_folder_fd is not None:
            expected = os.fstat(expected_folder_fd)
            if identity != (expected.st_dev, expected.st_ino):
                raise ValueError(
                    f"directory path changed during operation: {vault / relative}"
                )
        with os.scandir(folder_fd) as entries:
            if next(entries, None) is not None:
                return False
        _require_directory_path_identity(vault / relative, folder_fd)
        _require_directory_path_identity(vault / relative.parent, parent_fd)
        if not _rmdir_owned_directory_at(parent_fd, relative.name, identity):
            return False
        try:
            _require_directory_path_identity(vault / relative.parent, parent_fd)
            _require_directory_path_identity(vault, root_fd)
        except Exception:
            try:
                os.mkdir(relative.name, mode=0o700, dir_fd=parent_fd)
            except Exception as rollback_error:
                raise OSError(
                    errno.EIO,
                    f"empty folder removal could not roll back safely: {vault / relative}",
                ) from rollback_error
            raise
        return True
    finally:
        if folder_fd is not None:
            os.close(folder_fd)
        os.close(parent_fd)


def create_folder(vault: Path, name: str) -> Path:
    """Create one author folder directly under active ``cache``."""
    stored_name = validate_folder_name(name)
    vault, root_fd = _open_pinned_vault_root(vault)
    record: _OwnedDirectory | None = None
    cache_fd: int | None = None
    try:
        cache_fd = _open_relative_directory_no_follow(
            root_fd,
            Path("cache"),
            vault,
        )
        collision = _semantic_folder_collision_at(cache_fd, stored_name)
        if collision is not None:
            raise FileExistsError(
                f"folder name conflicts by NFC+casefold: {collision}"
            )
        relative = Path("cache") / stored_name
        record = _mkdir_relative_owned(root_fd, vault, relative)
        collision = _semantic_folder_collision_at(
            cache_fd,
            stored_name,
            excluding=stored_name,
        )
        if collision is not None:
            raise FileExistsError(
                f"folder name conflicts by NFC+casefold: {collision}"
            )
        _require_directory_path_identity(vault / "cache", record.parent_fd)
        _require_directory_path_identity(vault, root_fd)
        return vault / relative
    except Exception:
        if record is not None:
            _cleanup_owned_directories([record])
            record = None
        raise
    finally:
        if record is not None:
            _release_owned_directories([record])
        if cache_fd is not None:
            os.close(cache_fd)
        os.close(root_fd)


def rename_folder(vault: Path, folder: str | Path, new_name: str) -> Path:
    """Atomically rename one active folder without merging or overwriting."""
    source_name = _stored_folder_name(folder)
    target_name = validate_folder_name(new_name)
    vault, root_fd = _open_pinned_vault_root(vault)
    cache_fd = _open_relative_directory_no_follow(root_fd, Path("cache"), vault)
    source_fd: int | None = None
    try:
        source = vault / "cache" / source_name
        target = vault / "cache" / target_name
        source_fd = _open_child_directory_no_follow(cache_fd, source_name, source)
        papers, folder_errors = _folder_papers_and_errors_at(
            vault,
            root_fd,
            Path("cache"),
            source_name,
            folder_fd=source_fd,
            validate_papers=True,
        )
        if folder_errors:
            raise ValueError(folder_errors[0].error or "unsupported folder entry")
        from keikeu_core.markdown_io import parse_paper_bytes

        for relative in papers:
            data, _identity = _read_regular_bytes_at(
                source_fd,
                relative.name,
                vault / relative,
            )
            code = parse_paper_bytes(data).code
            if _paper_code_exists_at(
                root_fd,
                vault,
                code,
                parse_code=lambda value: parse_paper_bytes(value).code,
                excluding=relative,
            ):
                raise ValueError(f"duplicate Paper code blocks mutation: {code}")
        if source_name == target_name:
            _require_directory_path_identity(source, source_fd)
            return source
        collision = _semantic_folder_collision_at(
            cache_fd,
            target_name,
            excluding=source_name,
        )
        if collision is not None:
            raise FileExistsError(
                f"folder name conflicts by NFC+casefold: {collision}"
            )
        try:
            os.stat(target_name, dir_fd=cache_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(f"folder already exists: {target}")
        _require_directory_path_identity(source, source_fd)
        _require_directory_path_identity(vault / "cache", cache_fd)
        source_stat = os.fstat(source_fd)
        source_identity = (source_stat.st_dev, source_stat.st_ino)
        _atomic_rename_no_replace_at(
            cache_fd,
            source_name,
            cache_fd,
            target_name,
        )
        moved_target = os.stat(
            target_name,
            dir_fd=cache_fd,
            follow_symlinks=False,
        )
        moved_identity = (moved_target.st_dev, moved_target.st_ino)
        try:
            _require_directory_path_identity(target, source_fd)
            collision = _semantic_folder_collision_at(
                cache_fd,
                target_name,
                excluding=target_name,
            )
            if collision is not None:
                raise FileExistsError(
                    f"folder name conflicts by NFC+casefold: {collision}"
                )
            _require_directory_path_identity(vault, root_fd)
        except Exception as guard_error:
            try:
                current_target = os.stat(
                    target_name,
                    dir_fd=cache_fd,
                    follow_symlinks=False,
                )
                try:
                    os.stat(source_name, dir_fd=cache_fd, follow_symlinks=False)
                except FileNotFoundError:
                    source_is_free = True
                else:
                    source_is_free = False
                if (
                    source_is_free
                    and stat.S_ISDIR(current_target.st_mode)
                    and (current_target.st_dev, current_target.st_ino) == moved_identity
                ):
                    _atomic_rename_no_replace_at(
                        cache_fd,
                        target_name,
                        cache_fd,
                        source_name,
                    )
                    restored = os.stat(
                        source_name,
                        dir_fd=cache_fd,
                        follow_symlinks=False,
                    )
                    if (restored.st_dev, restored.st_ino) != moved_identity:
                        raise ValueError("restored folder identity does not match")
                    if moved_identity == source_identity:
                        _require_directory_path_identity(source, source_fd)
                    raise guard_error
            except FileNotFoundError:
                pass
            except Exception as rollback_error:
                if rollback_error is guard_error:
                    raise
                raise OSError(
                    errno.EIO,
                    "folder rename could not roll back safely; current paths were "
                    f"preserved at {source} and {target}",
                ) from rollback_error
            raise OSError(
                errno.EIO,
                "folder rename target changed externally; replacement was preserved "
                f"at {target} and was not moved to {source}",
            ) from guard_error
        return target
    finally:
        if source_fd is not None:
            os.close(source_fd)
        os.close(cache_fd)
        os.close(root_fd)


def move_papers(
    vault: Path,
    paths: Iterable[str | Path],
    destination_folder: str | Path | None,
) -> list[PathOperationResult]:
    """Move explicit active Papers and report every item independently."""
    vault, root_fd = _open_pinned_vault_root(vault)
    destination_fd: int | None = None
    try:
        destination_parent = Path("cache")
        if destination_folder is not None:
            folder_name = _stored_folder_name(destination_folder)
            destination_parent /= folder_name
        destination_fd = _open_relative_directory_no_follow(
            root_fd,
            destination_parent,
            vault,
        )
        results: list[PathOperationResult] = []
        for candidate in paths:
            try:
                source_relative = _supported_paper_relative_path(
                    vault,
                    candidate,
                    ("cache",),
                )
                destination_relative = destination_parent / source_relative.name
                if source_relative == destination_relative:
                    _validate_supported_paper_at(
                        vault,
                        root_fd,
                        source_relative,
                    )
                    results.append(
                        PathOperationResult(
                            source=source_relative,
                            destination=source_relative,
                        )
                    )
                    continue
                results.append(
                    _result_for_move(
                        vault,
                        root_fd,
                        source_relative,
                        destination_relative,
                        expected_destination_parent_fd=destination_fd,
                    )
                )
            except (OSError, ValueError) as exc:
                results.append(PathOperationResult(source=Path(candidate), error=str(exc)))
        return results
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        os.close(root_fd)


def _folder_papers_and_errors_at(
    vault: Path,
    root_fd: int,
    base: Path,
    folder_name: str,
    *,
    folder_fd: int,
    validate_papers: bool,
    preflight_filename_conflicts: bool = False,
) -> tuple[list[Path], list[PathOperationResult]]:
    folder = base / folder_name
    papers: list[Path] = []
    errors: list[PathOperationResult] = []
    from keikeu_core.markdown_io import parse_paper_bytes

    with os.scandir(folder_fd) as entries:
        folder_entries = sorted(entries, key=lambda entry: entry.name)
    for entry in folder_entries:
        relative = folder / entry.name
        display_path = vault / relative
        try:
            entry_stat = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(entry_stat.st_mode):
                raise ValueError("symlink is not supported")
            if stat.S_ISDIR(entry_stat.st_mode):
                raise ValueError("Paper folders support one level only")
            if not stat.S_ISREG(entry_stat.st_mode):
                raise ValueError("special filesystem entry is not supported")
            if relative.suffix != ".md":
                raise ValueError("unsupported non-Paper file blocks folder operation")
            if validate_papers or preflight_filename_conflicts:
                data, identity = _read_regular_bytes_at(
                    folder_fd,
                    entry.name,
                    display_path,
                )
                if identity != (entry_stat.st_dev, entry_stat.st_ino):
                    raise ValueError("Paper changed while inspecting folder")
                try:
                    paper = parse_paper_bytes(data)
                except (ValueError, UnicodeError):
                    if validate_papers:
                        raise
                else:
                    if entry.name != f"{paper.code}.md":
                        raise ValueError(
                            "Paper filename and frontmatter code do not match"
                        )
            papers.append(relative)
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append(PathOperationResult(source=relative, error=str(exc)))
    _require_directory_path_identity(vault / folder, folder_fd)
    papers.sort(key=str)
    errors.sort(key=lambda result: (str(result.source), result.error or ""))
    return papers, errors


def merge_folders(
    vault: Path,
    source_folder: str | Path,
    destination_folder: str | Path,
) -> list[PathOperationResult]:
    """Move supported Papers into an existing folder and remove only if empty."""
    source_name = _stored_folder_name(source_folder)
    destination_name = _stored_folder_name(destination_folder)
    if source_name == destination_name:
        raise ValueError("source and destination folders must differ")
    vault, root_fd = _open_pinned_vault_root(vault)
    source_fd: int | None = None
    destination_fd: int | None = None
    try:
        source_fd = _open_relative_directory_no_follow(
            root_fd,
            Path("cache") / source_name,
            vault,
        )
        destination_fd = _open_relative_directory_no_follow(
            root_fd,
            Path("cache") / destination_name,
            vault,
        )
        papers, results = _folder_papers_and_errors_at(
            vault,
            root_fd,
            Path("cache"),
            source_name,
            folder_fd=source_fd,
            validate_papers=False,
            preflight_filename_conflicts=True,
        )
        if results:
            return results
        _require_directory_path_identity(
            vault / "cache" / source_name,
            source_fd,
        )
        for source_relative in papers:
            results.append(
                _result_for_move(
                    vault,
                    root_fd,
                    source_relative,
                    Path("cache") / destination_name / source_relative.name,
                    expected_source_parent_fd=source_fd,
                    expected_destination_parent_fd=destination_fd,
                )
            )
        source_relative = Path("cache") / source_name
        try:
            removed = _remove_empty_folder_at(
                vault,
                root_fd,
                source_relative,
                expected_folder_fd=source_fd,
            )
        except (OSError, ValueError) as exc:
            results.append(PathOperationResult(source=source_relative, error=str(exc)))
            removed = False
        if not removed and not any(result.source == source_relative for result in results):
            results.append(
                PathOperationResult(
                    source=source_relative,
                    error="folder retained because unsupported or failed items remain",
                )
            )
        return results
    finally:
        if source_fd is not None:
            os.close(source_fd)
        if destination_fd is not None:
            os.close(destination_fd)
        os.close(root_fd)


def soft_delete_papers(
    vault: Path,
    paths: Iterable[str | Path],
) -> list[PathOperationResult]:
    """Move explicit active Papers to matching Trash folders per item."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        results: list[PathOperationResult] = []
        for candidate in paths:
            record: _OwnedDirectory | None = None
            destination_fd: int | None = None
            keep_directory = False
            try:
                source_relative = _supported_paper_relative_path(
                    vault,
                    candidate,
                    ("cache",),
                )
                remainder = source_relative.parts[1:]
                if len(remainder) == 2:
                    stored_target = _semantic_target_folder_name_at(
                        root_fd,
                        vault,
                        Path(".trash/cache"),
                        remainder[0],
                    )
                    remainder = (stored_target, remainder[1])
                destination_relative = Path(".trash/cache").joinpath(*remainder)
                destination_fd, record = _ensure_relative_directory_at(
                    root_fd,
                    vault,
                    destination_relative.parent,
                )
                result = _result_for_move(
                    vault,
                    root_fd,
                    source_relative,
                    destination_relative,
                    expected_destination_parent_fd=destination_fd,
                )
                keep_directory = result.succeeded
                results.append(result)
            except (OSError, ValueError) as exc:
                results.append(PathOperationResult(source=Path(candidate), error=str(exc)))
            finally:
                if destination_fd is not None:
                    os.close(destination_fd)
                _release_or_cleanup_directory(record, keep=keep_directory)
        return results
    finally:
        os.close(root_fd)


def soft_delete(vault: Path, rel_path: str | Path) -> Path:
    """Soft-delete one exact active Paper while preserving code and folder."""
    result = soft_delete_papers(vault, [rel_path])[0]
    if result.error is not None:
        if (
            "already exists" in result.error
            or "duplicate Paper code" in result.error
            or "File exists" in result.error
        ):
            raise FileExistsError(result.error)
        raise ValueError(result.error)
    assert result.destination is not None
    return _lexical_absolute_path(vault) / result.destination


def soft_delete_folder(
    vault: Path,
    folder: str | Path,
) -> list[PathOperationResult]:
    """Soft-delete supported Papers in one folder and preserve failed/unknown items."""
    folder_name = _stored_folder_name(folder)
    vault, root_fd = _open_pinned_vault_root(vault)
    target_record: _OwnedDirectory | None = None
    keep_target = False
    source_fd: int | None = None
    target_fd: int | None = None
    try:
        source_fd = _open_relative_directory_no_follow(
            root_fd,
            Path("cache") / folder_name,
            vault,
        )
        papers, results = _folder_papers_and_errors_at(
            vault,
            root_fd,
            Path("cache"),
            folder_name,
            folder_fd=source_fd,
            validate_papers=False,
            preflight_filename_conflicts=True,
        )
        if results:
            return results
        _require_directory_path_identity(
            vault / "cache" / folder_name,
            source_fd,
        )
        target_name = _semantic_target_folder_name_at(
            root_fd,
            vault,
            Path(".trash/cache"),
            folder_name,
        )
        target_relative = Path(".trash/cache") / target_name
        target_fd, target_record = _ensure_relative_directory_at(
            root_fd,
            vault,
            target_relative,
        )
        for source_relative in papers:
            result = _result_for_move(
                vault,
                root_fd,
                source_relative,
                target_relative / source_relative.name,
                expected_source_parent_fd=source_fd,
                expected_destination_parent_fd=target_fd,
            )
            keep_target = keep_target or result.succeeded
            results.append(result)
        source_relative = Path("cache") / folder_name
        try:
            removed = _remove_empty_folder_at(
                vault,
                root_fd,
                source_relative,
                expected_folder_fd=source_fd,
            )
        except (OSError, ValueError) as exc:
            results.append(PathOperationResult(source=source_relative, error=str(exc)))
            removed = False
        if removed:
            keep_target = True
            if not papers and not results:
                results.append(
                    PathOperationResult(
                        source=source_relative,
                        destination=target_relative,
                    )
                )
        elif not any(result.source == source_relative for result in results):
            results.append(
                PathOperationResult(
                    source=source_relative,
                    error="folder retained because unsupported or failed items remain",
                )
            )
        return results
    finally:
        if source_fd is not None:
            os.close(source_fd)
        if target_fd is not None:
            os.close(target_fd)
        _release_or_cleanup_directory(target_record, keep=keep_target)
        os.close(root_fd)


def list_trashed_papers(vault: Path) -> list[Path]:
    """Return sorted safe root/one-folder recovery Paper paths."""
    papers, _errors = scan_trashed_papers(vault)
    return papers


def restore_papers(
    vault: Path,
    paths: Iterable[str | Path],
) -> list[PathOperationResult]:
    """Restore explicit Trash Papers to their matching active folder per item."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        results: list[PathOperationResult] = []
        for candidate in paths:
            record: _OwnedDirectory | None = None
            destination_fd: int | None = None
            keep_directory = False
            try:
                source_relative = _supported_paper_relative_path(
                    vault,
                    candidate,
                    (".trash", "cache"),
                )
                from keikeu_core.markdown_io import parse_paper_bytes

                source_parent_fd = _open_relative_directory_no_follow(
                    root_fd,
                    source_relative.parent,
                    vault,
                )
                try:
                    source_bytes, _identity = _read_regular_bytes_at(
                        source_parent_fd,
                        source_relative.name,
                        vault / source_relative,
                    )
                finally:
                    os.close(source_parent_fd)
                paper = parse_paper_bytes(source_bytes)
                if source_relative.name != f"{paper.code}.md":
                    raise ValueError(
                        "Paper filename and frontmatter code do not match"
                    )
                remainder = source_relative.parts[2:-1]
                if remainder:
                    remainder = (
                        _semantic_target_folder_name_at(
                            root_fd,
                            vault,
                            Path("cache"),
                            remainder[0],
                        ),
                    )
                destination_parent = Path("cache").joinpath(*remainder)
                destination_relative = destination_parent / f"{paper.code}.md"
                destination_fd, record = _ensure_relative_directory_at(
                    root_fd,
                    vault,
                    destination_parent,
                )
                result = _result_for_move(
                    vault,
                    root_fd,
                    source_relative,
                    destination_relative,
                    expected_destination_parent_fd=destination_fd,
                )
                keep_directory = result.succeeded
                results.append(result)
            except (OSError, ValueError) as exc:
                results.append(PathOperationResult(source=Path(candidate), error=str(exc)))
            finally:
                if destination_fd is not None:
                    os.close(destination_fd)
                _release_or_cleanup_directory(record, keep=keep_directory)
        return results
    finally:
        os.close(root_fd)


def restore_paper(vault: Path, rel_path: str | Path) -> Path:
    """Restore one exact Trash Paper without changing its historical code."""
    result = restore_papers(vault, [rel_path])[0]
    if result.error is not None:
        if "already exists" in result.error or "duplicate Paper code" in result.error:
            raise FileExistsError(result.error)
        raise ValueError(result.error)
    assert result.destination is not None
    return _lexical_absolute_path(vault) / result.destination


def restore_folder(
    vault: Path,
    folder: str | Path,
) -> list[PathOperationResult]:
    """Restore one Trash folder, merging only non-conflicting Papers."""
    folder_name = _stored_folder_name(folder)
    vault, root_fd = _open_pinned_vault_root(vault)
    target_record: _OwnedDirectory | None = None
    keep_target = False
    source_fd: int | None = None
    target_fd: int | None = None
    try:
        source_fd = _open_relative_directory_no_follow(
            root_fd,
            Path(".trash/cache") / folder_name,
            vault,
        )
        papers, results = _folder_papers_and_errors_at(
            vault,
            root_fd,
            Path(".trash/cache"),
            folder_name,
            folder_fd=source_fd,
            validate_papers=False,
        )
        if results:
            return results
        _require_directory_path_identity(
            vault / ".trash/cache" / folder_name,
            source_fd,
        )
        target_name = _semantic_target_folder_name_at(
            root_fd,
            vault,
            Path("cache"),
            folder_name,
        )
        target_relative = Path("cache") / target_name
        target_fd, target_record = _ensure_relative_directory_at(
            root_fd,
            vault,
            target_relative,
        )
        for source_relative in papers:
            from keikeu_core.markdown_io import parse_paper_bytes

            try:
                data, _identity = _read_regular_bytes_at(
                    source_fd,
                    source_relative.name,
                    vault / source_relative,
                )
                code = parse_paper_bytes(data).code
                if source_relative.name != f"{code}.md":
                    raise ValueError(
                        "Paper filename and frontmatter code do not match"
                    )
                result = _result_for_move(
                    vault,
                    root_fd,
                    source_relative,
                    target_relative / f"{code}.md",
                    expected_source_parent_fd=source_fd,
                    expected_destination_parent_fd=target_fd,
                )
            except (OSError, ValueError, UnicodeError) as exc:
                result = PathOperationResult(
                    source=source_relative,
                    error=str(exc),
                )
            keep_target = keep_target or result.succeeded
            results.append(result)
        source_relative = Path(".trash/cache") / folder_name
        try:
            removed = _remove_empty_folder_at(
                vault,
                root_fd,
                source_relative,
                expected_folder_fd=source_fd,
            )
        except (OSError, ValueError) as exc:
            results.append(PathOperationResult(source=source_relative, error=str(exc)))
            removed = False
        if removed:
            keep_target = True
            if not papers and not results:
                results.append(
                    PathOperationResult(
                        source=source_relative,
                        destination=target_relative,
                    )
                )
        elif not any(result.source == source_relative for result in results):
            results.append(
                PathOperationResult(
                    source=source_relative,
                    error="folder retained because unsupported or failed items remain",
                )
            )
        return results
    finally:
        if source_fd is not None:
            os.close(source_fd)
        if target_fd is not None:
            os.close(target_fd)
        _release_or_cleanup_directory(target_record, keep=keep_target)
        os.close(root_fd)


def permanently_delete_papers(
    vault: Path,
    paths: Iterable[str | Path],
) -> list[PathOperationResult]:
    """Permanently unlink only explicit validated Trash Paper paths."""
    from keikeu_core.markdown_io import parse_paper_bytes

    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        results: list[PathOperationResult] = []
        touched_folders: dict[Path, int] = {}
        for candidate in paths:
            try:
                relative = _supported_paper_relative_path(
                    vault,
                    candidate,
                    (".trash", "cache"),
                )
                parent_fd = _open_relative_directory_no_follow(
                    root_fd,
                    relative.parent,
                    vault,
                )
                try:
                    data, identity = _read_regular_bytes_at(
                        parent_fd,
                        relative.name,
                        vault / relative,
                    )
                    code = parse_paper_bytes(data).code
                    if relative.name != f"{code}.md":
                        raise ValueError(
                            "Paper filename and frontmatter code do not match"
                        )
                    if _paper_code_exists_at(
                        root_fd,
                        vault,
                        code,
                        parse_code=lambda value: parse_paper_bytes(value).code,
                        excluding=relative,
                    ):
                        raise ValueError(f"duplicate Paper code blocks mutation: {code}")
                    _require_directory_path_identity(vault / relative.parent, parent_fd)
                    deleted = _unlink_owned_file_at(
                        parent_fd,
                        relative.name,
                        identity,
                        expected_digest=hashlib.sha256(data).hexdigest(),
                    )
                    if not deleted:
                        raise ValueError(f"Paper changed before permanent delete: {vault / relative}")
                    try:
                        _require_directory_path_identity(vault / relative.parent, parent_fd)
                        _require_directory_path_identity(vault, root_fd)
                    except Exception:
                        try:
                            _create_regular_bytes_at(
                                parent_fd,
                                relative.name,
                                data,
                                vault / relative,
                            )
                        except Exception as rollback_error:
                            raise OSError(
                                errno.EIO,
                                "permanent delete path changed and byte recovery failed: "
                                f"{vault / relative}",
                            ) from rollback_error
                        raise
                    if (
                        len(relative.parts) == 4
                        and relative.parent not in touched_folders
                    ):
                        touched_folders[relative.parent] = os.dup(parent_fd)
                finally:
                    os.close(parent_fd)
                results.append(PathOperationResult(source=relative))
            except (OSError, ValueError) as exc:
                results.append(PathOperationResult(source=Path(candidate), error=str(exc)))
        for relative in sorted(touched_folders, key=str):
            try:
                _remove_empty_folder_at(
                    vault,
                    root_fd,
                    relative,
                    expected_folder_fd=touched_folders[relative],
                )
            except (OSError, ValueError) as exc:
                results.append(PathOperationResult(source=relative, error=str(exc)))
        return results
    finally:
        for folder_fd in touched_folders.values():
            os.close(folder_fd)
        os.close(root_fd)


def permanently_delete_folder(
    vault: Path,
    folder: str | Path,
) -> PathOperationResult:
    """Permanently remove one explicit, verified-empty Trash folder."""
    folder_name = _stored_folder_name(folder)
    vault, root_fd = _open_pinned_vault_root(vault)
    folder_fd: int | None = None
    relative = Path(".trash/cache") / folder_name
    try:
        folder_fd = _open_relative_directory_no_follow(
            root_fd,
            relative,
            vault,
        )
        with os.scandir(folder_fd) as entries:
            if next(entries, None) is not None:
                return PathOperationResult(
                    source=relative,
                    error="Trash folder must be empty before permanent delete",
                )
        _require_directory_path_identity(vault / relative, folder_fd)
        removed = _remove_empty_folder_at(
            vault,
            root_fd,
            relative,
            expected_folder_fd=folder_fd,
        )
        if not removed:
            return PathOperationResult(
                source=relative,
                error="Trash folder changed before permanent delete",
            )
        return PathOperationResult(source=relative)
    except (OSError, ValueError) as exc:
        return PathOperationResult(source=relative, error=str(exc))
    finally:
        if folder_fd is not None:
            os.close(folder_fd)
        os.close(root_fd)


def get_vault(config_path: Path) -> Path | None:
    """Return the configured vault path, or ``None`` for absent/bad config."""
    try:
        descriptor = open_regular_no_follow(config_path)
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            obj = json.load(handle)
    except (OSError, ValueError):
        return None
    value = obj.get("vault") if isinstance(obj, dict) else None
    return Path(value) if isinstance(value, str) else None


def set_vault(
    path: Path,
    config_path: Path,
    expected_selection: VaultSelectionToken,
) -> None:
    """Persist exactly the caller-validated Vault object and byte snapshot."""
    if not isinstance(expected_selection, VaultSelectionToken):
        raise TypeError("expected_selection must be a VaultSelectionToken")
    raw_path = _lexical_absolute_path(path)
    try:
        vault_fd = open_directory_no_follow(raw_path)
    except FileNotFoundError as exc:
        raise ValueError(f"Vault must be an existing directory: {raw_path}") from exc
    try:
        path = _require_lexical_home_path(raw_path)
        _require_selection_token_matches(
            expected_selection,
            _selection_token_from_pinned_root(path, vault_fd),
        )
        config_path = _require_lexical_home_path(config_path)
        config_parent, directory_fd, parent_records = _create_directory_path_no_follow(
            config_path.parent,
            leaf_must_be_new=False,
        )
        payload = (
            json.dumps({"vault": str(path)}, indent=2, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        payload_digest = hashlib.sha256(payload).hexdigest()
        temporary_name = f".{config_path.name}.{secrets.token_hex(8)}.tmp"
        temporary_identity: tuple[int, int] | None = None
        try:
            descriptor = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=directory_fd,
            )
            temporary_stat = os.fstat(descriptor)
            temporary_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                target_stat = os.stat(
                    config_path.name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISREG(
                    target_stat.st_mode
                ):
                    raise ValueError(f"config must be a regular file: {config_path}")

            _require_directory_path_identity(config_parent, directory_fd)
            _require_selection_token_matches(
                expected_selection,
                _selection_token_from_pinned_root(path, vault_fd),
            )
            os.replace(
                temporary_name,
                config_path.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            temporary_identity = None
        finally:
            if temporary_identity is not None:
                _unlink_owned_file_at(
                    directory_fd,
                    temporary_name,
                    temporary_identity,
                    expected_digest=payload_digest,
                )
            os.close(directory_fd)
            _release_owned_directories(parent_records)
    finally:
        os.close(vault_fd)
