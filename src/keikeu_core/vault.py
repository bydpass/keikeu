"""Paper Vault layout, recovery bin, and local config resolution.

The user-selected vault holds only durable Paper Markdown and a disposable
index.  Recovery moves a file under ``.trash/cache``; it never copies or
rewrites an asset unless a code collision requires an explicitly requested
new Paper code.
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
from typing import Callable

from keikeu_core.models import validate_paper_code

__all__ = [
    "VaultSelectionToken",
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
    "list_active_papers",
    "next_paper_code",
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
    if expected_bytes is not None:
        try:
            descriptor = open_regular_no_follow(path)
        except (OSError, ValueError):
            return False
        try:
            before = os.fstat(descriptor)
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                current_bytes = handle.read()
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (
            (before.st_dev, before.st_ino) != identity
            or (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            or current_bytes != expected_bytes
        ):
            return False

    directory_fd = open_directory_no_follow(path.parent)
    try:
        try:
            path_stat = os.stat(
                path.name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return False
        if (path_stat.st_dev, path_stat.st_ino) != identity:
            return False
        os.unlink(path.name, dir_fd=directory_fd)
        return True
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
    """Move one regular entry through pinned parents without clobbering."""
    if (guard_path is None) != (guard_fd is None):
        raise ValueError("move guard path and descriptor must be provided together")

    def require_guard() -> None:
        if guard_path is not None and guard_fd is not None:
            _require_directory_path_identity(guard_path, guard_fd)

    linked = False
    source_unlinked = False
    source_identity: tuple[int, int] | None = None
    linked_identity: tuple[int, int] | None = None
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
        os.link(
            source_name,
            destination_name,
            src_dir_fd=source_directory_fd,
            dst_dir_fd=destination_directory_fd,
            follow_symlinks=False,
        )
        linked = True
        linked_stat = os.stat(
            destination_name,
            dir_fd=destination_directory_fd,
            follow_symlinks=False,
        )
        linked_identity = (linked_stat.st_dev, linked_stat.st_ino)
        current_source_stat = os.stat(
            source_name,
            dir_fd=source_directory_fd,
            follow_symlinks=False,
        )
        if (
            linked_identity != source_identity
            or (current_source_stat.st_dev, current_source_stat.st_ino)
            != source_identity
        ):
            raise ValueError(f"Paper changed while moving: {source_path}")
        if expected_source_bytes is not None:
            linked_bytes, current_linked_identity = _read_regular_bytes_at(
                destination_directory_fd,
                destination_name,
                destination_path,
            )
            if (
                current_linked_identity != linked_identity
                or linked_bytes != expected_source_bytes
            ):
                raise ValueError(f"Paper changed while moving: {source_path}")
        require_guard()
        os.unlink(source_name, dir_fd=source_directory_fd)
        source_unlinked = True
        require_guard()
    except Exception as move_error:
        if source_unlinked and linked_identity is not None:
            try:
                os.link(
                    destination_name,
                    source_name,
                    src_dir_fd=destination_directory_fd,
                    dst_dir_fd=source_directory_fd,
                    follow_symlinks=False,
                )
                restored_stat = os.stat(
                    source_name,
                    dir_fd=source_directory_fd,
                    follow_symlinks=False,
                )
                if (restored_stat.st_dev, restored_stat.st_ino) != linked_identity:
                    raise ValueError("restored source identity does not match")
                os.unlink(destination_name, dir_fd=destination_directory_fd)
            except Exception as rollback_error:
                raise OSError(
                    errno.EIO,
                    "Paper move could not roll back safely; both locations were "
                    f"preserved at {source_path} and {destination_path}",
                ) from rollback_error
            raise move_error
        if linked and linked_identity is not None:
            try:
                destination_stat = os.stat(
                    destination_name,
                    dir_fd=destination_directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                if (
                    destination_stat.st_dev,
                    destination_stat.st_ino,
                ) == linked_identity:
                    os.unlink(destination_name, dir_fd=destination_directory_fd)
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
                current_stat = os.stat(
                    destination.name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                if (current_stat.st_dev, current_stat.st_ino) == destination_identity:
                    os.unlink(destination.name, dir_fd=parent_fd)
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
        try:
            current = os.stat(
                relative.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            if identity is not None and stat.S_ISDIR(current.st_mode) and (
                current.st_dev,
                current.st_ino,
            ) == identity:
                try:
                    os.rmdir(relative.name, dir_fd=parent_fd)
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
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except (FileNotFoundError, OSError):
        return False
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (
            opened.st_dev,
            opened.st_ino,
        ) != identity:
            return False
        if expected_digest is not None:
            digest = hashlib.sha256()
            before = opened
            while chunk := os.read(descriptor, 1024 * 1024):
                digest.update(chunk)
            after = os.fstat(descriptor)
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
            ) or digest.hexdigest() != expected_digest:
                return False
    finally:
        os.close(descriptor)
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return False
    if (current.st_dev, current.st_ino) != identity:
        return False
    os.unlink(name, dir_fd=parent_fd)
    return True


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


def _cleanup_owned_directories(records: list[_OwnedDirectory]) -> None:
    for record in reversed(records):
        try:
            try:
                current = os.stat(
                    record.name,
                    dir_fd=record.parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(current.st_mode) and (
                current.st_dev,
                current.st_ino,
            ) == record.identity:
                try:
                    os.rmdir(record.name, dir_fd=record.parent_fd)
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


def _soft_delete_target_name(directory_fd: int, source: Path) -> str:
    target_name = source.name
    while True:
        try:
            os.stat(
                target_name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return target_name
        target_name = f"{source.stem}-{secrets.token_hex(4)}{source.suffix}"


def soft_delete(vault: Path, rel_path: str) -> Path:
    """Move an active ``cache/*.md`` Paper to recovery without overwriting.

    The file move preserves bytes exactly.  A duplicate recovery filename gains
    a random suffix; its Paper frontmatter remains the durable code authority.
    """
    vault = _lexical_absolute_path(vault)
    _require_lexical_home_path(vault)
    source_relative = _direct_paper_relative_path(vault, rel_path, ("cache",))
    source = vault / source_relative
    vault_fd = open_directory_no_follow(vault)
    cache_fd: int | None = None
    trash_cache_fd: int | None = None
    layout_records: list[_OwnedDirectory] = []
    try:
        _scan_regular_tree_fd(vault_fd, vault)
        _require_directory_path_identity(vault, vault_fd)
        cache_fd = _open_relative_directory_no_follow(vault_fd, Path("cache"), vault)
        source_stat = os.stat(
            source.name,
            dir_fd=cache_fd,
            follow_symlinks=False,
        )
        if stat.S_ISLNK(source_stat.st_mode):
            raise ValueError(f"symlink is not supported: {source}")
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError(f"Paper must be a regular file: {source}")
        source_identity = (source_stat.st_dev, source_stat.st_ino)

        for relative in (Path(".trash"), Path(".trash/cache")):
            try:
                directory_fd = _open_relative_directory_no_follow(
                    vault_fd,
                    relative,
                    vault,
                )
            except FileNotFoundError:
                layout_records.append(_mkdir_relative_owned(vault_fd, vault, relative))
            else:
                os.close(directory_fd)
        trash_cache_fd = _open_relative_directory_no_follow(
            vault_fd,
            Path(".trash/cache"),
            vault,
        )
        while True:
            target_name = _soft_delete_target_name(trash_cache_fd, source)
            target = vault / ".trash" / "cache" / target_name
            try:
                _move_regular_no_overwrite_at(
                    cache_fd,
                    source.name,
                    trash_cache_fd,
                    target_name,
                    source_path=source,
                    destination_path=target,
                    expected_source_identity=source_identity,
                    guard_path=vault,
                    guard_fd=vault_fd,
                )
            except FileExistsError:
                continue
            return target
    finally:
        if trash_cache_fd is not None:
            os.close(trash_cache_fd)
        if cache_fd is not None:
            os.close(cache_fd)
        os.close(vault_fd)
        _release_owned_directories(layout_records)


def list_trashed_papers(vault: Path) -> list[Path]:
    """Return sorted safe root/one-folder recovery Paper paths."""
    papers, _errors = scan_trashed_papers(vault)
    return papers


def restore_paper(vault: Path, rel_path: str, new_code: str | None = None) -> Path:
    """Restore a trashed Paper, requiring a new code only on active collision.

    A normal restore moves the original file bytes to its code-derived active
    path.  If that code is already active, the caller must either cancel or
    supply an unused ``new_code``.  The latter rewrites only the Paper code via
    ``markdown_io`` while preserving the frozen draft and current Summary.
    """
    vault, vault_fd = _open_pinned_vault(vault)
    try:
        return _restore_paper_pinned(vault, vault_fd, rel_path, new_code)
    finally:
        os.close(vault_fd)


def _restore_paper_pinned(
    vault: Path,
    vault_fd: int,
    rel_path: str,
    new_code: str | None,
) -> Path:
    from keikeu_core.markdown_io import _rewrite_paper_code_at, parse_paper_bytes

    source_relative = _direct_paper_relative_path(
        vault,
        rel_path,
        (".trash", "cache"),
    )
    source_parent_fd = _open_relative_directory_no_follow(
        vault_fd,
        Path(".trash/cache"),
        vault,
    )
    target_parent_fd: int | None = None
    try:
        source = vault / source_relative
        source_bytes, source_identity = _read_regular_bytes_at(
            source_parent_fd,
            source_relative.name,
            source,
        )
        paper = parse_paper_bytes(source_bytes)
        target_parent_fd = _open_relative_directory_no_follow(
            vault_fd,
            Path("cache"),
            vault,
        )

        def target_exists(name: str) -> bool:
            path = vault / "cache" / name
            try:
                target_stat = os.stat(
                    name,
                    dir_fd=target_parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return False
            if stat.S_ISLNK(target_stat.st_mode):
                raise ValueError(f"symlink is not supported: {path}")
            if not stat.S_ISREG(target_stat.st_mode):
                raise ValueError(f"Paper must be a regular file: {path}")
            return True

        current_name = f"{paper.code}.md"
        current_target = vault / "cache" / current_name
        collision = target_exists(current_name)
        if not collision and (
            new_code is None or validate_paper_code(new_code) == paper.code
        ):
            _move_regular_no_overwrite_at(
                source_parent_fd,
                source_relative.name,
                target_parent_fd,
                current_name,
                source_path=source,
                destination_path=current_target,
                expected_source_identity=source_identity,
                expected_source_bytes=source_bytes,
                guard_path=vault,
                guard_fd=vault_fd,
            )
            return current_target

        if new_code is None:
            raise FileExistsError(
                "Paper code is already active; choose a new Paper code or cancel"
            )
        new_code = validate_paper_code(new_code)
        target_name = f"{new_code}.md"
        target = vault / "cache" / target_name
        if target_exists(target_name):
            raise FileExistsError(f"Paper already exists: {target}")
        try:
            _rewrite_paper_code_at(
                source_parent_fd,
                source_relative.name,
                source,
                target_parent_fd,
                target_name,
                target,
                new_code,
                expected_source_bytes=source_bytes,
                guard_path=vault,
                guard_fd=vault_fd,
            )
        except ValueError as exc:
            if "changed" in str(exc):
                raise ValueError(
                    f"Paper changed before restore cleanup: {source}"
                ) from exc
            raise
        return target
    finally:
        if target_parent_fd is not None:
            os.close(target_parent_fd)
        os.close(source_parent_fd)


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
