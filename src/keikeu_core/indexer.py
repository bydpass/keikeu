"""Rebuildable folder-aware v3 Paper metadata index.

The index projects supported root/one-folder active Papers.  Active and Trash
paths are read independently so malformed, deep, symlinked, or duplicate-code
assets become ``errors`` without hiding valid Papers or changing Markdown.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import stat

from keikeu_core.markdown_io import parse_paper_bytes
from keikeu_core.models import Paper, validate_paper_code
from keikeu_core.vault import (
    _create_regular_bytes_at,
    _open_pinned_vault_root,
    _open_relative_directory_no_follow,
    _read_regular_bytes_at,
    _require_directory_path_identity,
    _scan_paper_area_at,
    _supported_paper_relative_path,
    _unlink_owned_file_at,
    atomic_exchange_at_no_follow,
    require_atomic_exchange,
)

__all__ = [
    "rebuild_index",
    "load_index",
    "save_index",
    "save_index_at",
    "list_papers",
    "list_index_errors",
]


def _index_path(vault: Path) -> Path:
    return vault / "keikeu_index.json"


def _entry_identity(directory_fd: int, name: str) -> tuple[int, int] | None:
    try:
        entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return entry.st_dev, entry.st_ino


def _write_json_at(
    directory_fd: int,
    target_name: str,
    obj: object,
    *,
    guard_path: Path | None = None,
    guard_fd: int | None = None,
) -> None:
    if (guard_path is None) != (guard_fd is None):
        raise ValueError("index guard path and descriptor must be provided together")

    def require_guard() -> None:
        if guard_path is not None and guard_fd is not None:
            _require_directory_path_identity(guard_path, guard_fd)

    payload = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    payload_digest = hashlib.sha256(payload).hexdigest()
    while True:
        temporary_name = f".{target_name}.{secrets.token_hex(8)}.tmp"
        try:
            temporary_identity = _create_regular_bytes_at(
                directory_fd,
                temporary_name,
                payload,
                (guard_path or Path(".")) / temporary_name,
            )
        except FileExistsError:
            continue
        break

    target_existed = False
    mutation_finished = False
    try:
        try:
            target_stat = os.stat(
                target_name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(target_stat.st_mode):
                raise ValueError(f"symlink is not supported: {target_name}")
            if not stat.S_ISREG(target_stat.st_mode):
                raise ValueError(f"index must be a regular file: {target_name}")
            target_existed = True
        require_guard()
        if target_existed:
            require_atomic_exchange()
            atomic_exchange_at_no_follow(
                directory_fd,
                temporary_name,
                directory_fd,
                target_name,
            )
        else:
            os.link(
                temporary_name,
                target_name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        mutation_finished = True
        require_guard()
    except Exception as write_error:
        if mutation_finished:
            try:
                if target_existed:
                    if _entry_identity(directory_fd, target_name) != temporary_identity:
                        raise ValueError("index target changed during rollback")
                    atomic_exchange_at_no_follow(
                        directory_fd,
                        temporary_name,
                        directory_fd,
                        target_name,
                    )
                    cleanup_name = temporary_name
                else:
                    cleanup_name = target_name
                if not _unlink_owned_file_at(
                    directory_fd,
                    cleanup_name,
                    temporary_identity,
                    expected_digest=payload_digest,
                ):
                    raise ValueError("index replacement changed during rollback")
                if not target_existed and not _unlink_owned_file_at(
                    directory_fd,
                    temporary_name,
                    temporary_identity,
                    expected_digest=payload_digest,
                ):
                    raise ValueError("index temporary changed during rollback")
            except Exception as rollback_error:
                raise OSError(
                    "index write could not roll back safely; both versions were preserved"
                ) from rollback_error
        elif not _unlink_owned_file_at(
            directory_fd,
            temporary_name,
            temporary_identity,
            expected_digest=payload_digest,
        ):
            raise OSError("index temporary file could not be cleaned safely")
        raise

    if target_existed:
        previous_bytes, previous_identity = _read_regular_bytes_at(
            directory_fd,
            temporary_name,
            (guard_path or Path(".")) / temporary_name,
        )
        cleanup_digest = hashlib.sha256(previous_bytes).hexdigest()
    else:
        previous_identity = temporary_identity
        cleanup_digest = payload_digest
    if not _unlink_owned_file_at(
            directory_fd,
            temporary_name,
            previous_identity,
            expected_digest=cleanup_digest,
        ):
        raise OSError(
            "index write completed but the temporary copy was preserved"
        )


def _read_json_at(directory_fd: int, vault: Path) -> object | None:
    try:
        data, _identity = _read_regular_bytes_at(
            directory_fd,
            "keikeu_index.json",
            _index_path(vault),
        )
        return json.loads(data.decode("utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None


def _paper_entry(vault: Path, path: Path, paper: Paper) -> dict[str, object]:
    if path.stem != paper.code:
        raise ValueError("Paper filename must match frontmatter code")
    relative = path.relative_to(vault)
    return {
        "code": paper.code,
        "display_name": paper.display_name,
        "path": str(relative),
        "folder": relative.parts[1] if len(relative.parts) == 3 else None,
        "summary": paper.summary,
        "tags": paper.tags,
        "highlight_names": [
            highlight.display_name
            for highlight in paper.highlights
            if highlight.display_name is not None
        ],
        "created": paper.created.isoformat(),
        "updated": paper.updated.isoformat(),
    }


def _read_paper_at(root_fd: int, vault: Path, relative: Path) -> Paper:
    parent_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
    try:
        data, _identity = _read_regular_bytes_at(
            parent_fd,
            relative.name,
            vault / relative,
        )
        _require_directory_path_identity(vault / relative.parent, parent_fd)
    finally:
        os.close(parent_fd)
    return parse_paper_bytes(data)


def _rebuild_index_at(vault: Path, root_fd: int) -> dict[str, object]:
    papers: list[dict[str, object]] = []
    active_paths, active_errors = _scan_paper_area_at(
        root_fd,
        vault,
        Path("cache"),
    )
    try:
        trash_paths, trash_errors = _scan_paper_area_at(
            root_fd,
            vault,
            Path(".trash/cache"),
        )
    except FileNotFoundError:
        trash_paths, trash_errors = [], []
    errors: list[dict[str, str]] = [*active_errors, *trash_errors]
    code_paths: dict[str, list[Path]] = {}
    for relative in active_paths:
        try:
            paper = _read_paper_at(root_fd, vault, relative)
            code_paths.setdefault(paper.code, []).append(relative)
            papers.append(_paper_entry(vault, vault / relative, paper))
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append({"path": str(relative), "reason": str(exc)})
    for relative in trash_paths:
        try:
            paper = _read_paper_at(root_fd, vault, relative)
            code_paths.setdefault(paper.code, []).append(relative)
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append({"path": str(relative), "reason": str(exc)})
    for code, paths in sorted(code_paths.items()):
        if len(paths) < 2:
            continue
        for relative in paths:
            errors.append(
                {
                    "path": str(relative),
                    "reason": f"duplicate Paper code across active/Trash: {code}",
                }
            )
    papers.sort(key=lambda entry: str(entry["path"]))
    errors = [
        {"path": path, "reason": reason}
        for path, reason in sorted(
            {(item["path"], item["reason"]) for item in errors}
        )
    ]
    index: dict[str, object] = {"version": 3, "papers": papers, "errors": errors}
    _write_json_at(
        root_fd,
        "keikeu_index.json",
        index,
        guard_path=vault,
        guard_fd=root_fd,
    )
    return index


def rebuild_index(vault: Path) -> dict[str, object]:
    """Rebuild and return the v3 index from active Paper Markdown only."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        return _rebuild_index_at(vault, root_fd)
    finally:
        os.close(root_fd)


def _is_valid_index(data: object) -> bool:
    return (
        isinstance(data, dict)
        and type(data.get("version")) is int
        and data.get("version") == 3
        and isinstance(data.get("papers"), list)
        and isinstance(data.get("errors"), list)
    )


def _entry_is_current_at(
    vault: Path,
    root_fd: int,
    entry: object,
) -> bool:
    if not isinstance(entry, dict):
        return False
    code = entry.get("code")
    candidate = entry.get("path")
    if not isinstance(code, str) or not isinstance(candidate, str):
        return False
    if (
        entry.get("display_name") is not None
        and not isinstance(entry.get("display_name"), str)
    ):
        return False
    if entry.get("folder") is not None and not isinstance(entry.get("folder"), str):
        return False
    if (
        not isinstance(entry.get("summary"), str)
        or not isinstance(entry.get("tags"), list)
        or not all(isinstance(tag, str) for tag in entry["tags"])
        or not isinstance(entry.get("highlight_names"), list)
        or not all(isinstance(name, str) for name in entry["highlight_names"])
        or not isinstance(entry.get("created"), str)
        or not isinstance(entry.get("updated"), str)
    ):
        return False
    try:
        validate_paper_code(code)
        relative = _supported_paper_relative_path(vault, candidate, ("cache",))
        expected_folder = relative.parts[1] if len(relative.parts) == 3 else None
        if entry.get("folder") != expected_folder:
            return False
        path = vault / relative
        parent_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
        try:
            data, _identity = _read_regular_bytes_at(parent_fd, relative.name, path)
            _require_directory_path_identity(path.parent, parent_fd)
        finally:
            os.close(parent_fd)
        paper = parse_paper_bytes(data)
    except (OSError, ValueError):
        return False
    return path.stem == code == paper.code


def _error_entry_is_safe(entry: object) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("path"), str)
        and isinstance(entry.get("reason"), str)
    )


def _index_entries_are_safe_at(
    vault: Path,
    root_fd: int,
    data: dict[str, object],
) -> bool:
    papers = data["papers"]
    errors = data["errors"]
    return (
        isinstance(papers, list)
        and all(_entry_is_current_at(vault, root_fd, entry) for entry in papers)
        and isinstance(errors, list)
        and all(_error_entry_is_safe(entry) for entry in errors)
    )


def load_index(vault: Path) -> dict[str, object]:
    """Load v3 metadata, rebuilding when JSON or entries are stale."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        data = _read_json_at(root_fd, vault)
        if _is_valid_index(data) and _index_entries_are_safe_at(
            vault,
            root_fd,
            data,
        ):
            _require_directory_path_identity(vault, root_fd)
            return data
        return _rebuild_index_at(vault, root_fd)
    finally:
        os.close(root_fd)


def save_index(vault: Path, index: dict[str, object]) -> None:
    """Write the disposable index without touching Markdown assets."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        _write_json_at(
            root_fd,
            "keikeu_index.json",
            index,
            guard_path=vault,
            guard_fd=root_fd,
        )
    finally:
        os.close(root_fd)


def save_index_at(directory_fd: int, index: dict[str, object]) -> None:
    """Write the disposable index through a caller-pinned Vault directory fd."""
    if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
        raise ValueError("Vault descriptor must name a directory")
    _write_json_at(directory_fd, "keikeu_index.json", index)


def list_papers(vault: Path) -> list[dict[str, object]]:
    """Return indexed active Papers; callers may explicitly rebuild to refresh."""
    return load_index(vault)["papers"]  # type: ignore[return-value]


def list_index_errors(vault: Path) -> list[dict[str, str]]:
    """Return isolated parse errors from the last usable index rebuild."""
    return load_index(vault)["errors"]  # type: ignore[return-value]
