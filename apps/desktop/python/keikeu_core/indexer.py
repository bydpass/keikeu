"""Rebuildable folder-aware Paper v4 metadata index.

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
import unicodedata

from keikeu_core.markdown_io import parse_paper_v4_bytes
from keikeu_core.models import PaperV4
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
    "save_index_at",
    "build_index_v4",
    "query_index_v4",
    "query_trash_v4",
    "rebuild_index_v4",
    "verify_index_v4",
]


_V4_TYPE_LABELS = {
    "summary": "总结",
    "snapshot": "高光",
    "whisper": "碎碎念",
}


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


def save_index_at(directory_fd: int, index: dict[str, object]) -> None:
    """Write a disposable index through a caller-pinned Vault directory fd."""
    if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
        raise ValueError("Vault descriptor must name a directory")
    _write_json_at(directory_fd, "keikeu_index.json", index)


def _read_paper_v4_at(root_fd: int, vault: Path, relative: Path) -> PaperV4:
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
    return parse_paper_v4_bytes(data)


def _v4_search_text(paper: PaperV4) -> str:
    fields = [paper.display_name or "", paper.code, *paper.tags]
    for page in paper.pages:
        fields.extend(
            [
                page.name or "",
                page.content,
                page.type or "",
                _V4_TYPE_LABELS.get(page.type or "", ""),
            ]
        )
    return "\0".join(fields)


def _paper_v4_entry(relative: Path, paper: PaperV4, *, base_parts: int = 1) -> dict[str, object]:
    if relative.name != f"{paper.code}.md":
        raise ValueError("Paper filename must match frontmatter code")
    remainder = relative.parts[base_parts:]
    folder = remainder[0] if len(remainder) == 2 else None
    return {
        "code": paper.code,
        "display_name": paper.display_name,
        "path": str(relative),
        "folder": folder,
        "tags": list(paper.tags),
        "preview": paper.pages[0].content,
        "page_count": len(paper.pages),
        "page_names": [page.name for page in paper.pages if page.name is not None],
        "search_text": _v4_search_text(paper),
        "created": paper.created.isoformat(),
        "updated": paper.updated.isoformat(),
    }


def _build_index_v4_at(vault: Path, root_fd: int) -> dict[str, object]:
    active_paths, active_errors = _scan_paper_area_at(root_fd, vault, Path("cache"))
    try:
        trash_paths, trash_errors = _scan_paper_area_at(
            root_fd,
            vault,
            Path(".trash/cache"),
        )
    except FileNotFoundError:
        trash_paths, trash_errors = [], []
    errors: list[dict[str, str]] = [*active_errors, *trash_errors]
    papers: list[dict[str, object]] = []
    code_paths: dict[str, list[Path]] = {}
    for relative in active_paths:
        try:
            paper = _read_paper_v4_at(root_fd, vault, relative)
            code_paths.setdefault(paper.code, []).append(relative)
            papers.append(_paper_v4_entry(relative, paper))
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append({"path": str(relative), "reason": str(exc)})
    for relative in trash_paths:
        try:
            paper = _read_paper_v4_at(root_fd, vault, relative)
            code_paths.setdefault(paper.code, []).append(relative)
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append({"path": str(relative), "reason": str(exc)})
    for code, paths in sorted(code_paths.items()):
        if len(paths) > 1:
            errors.extend(
                {
                    "path": str(relative),
                    "reason": f"duplicate Paper code across active/Trash: {code}",
                }
                for relative in paths
            )
    papers.sort(key=lambda entry: str(entry["path"]))
    errors = [
        {"path": path, "reason": reason}
        for path, reason in sorted({(item["path"], item["reason"]) for item in errors})
    ]
    return {"version": 4, "papers": papers, "errors": errors}


def build_index_v4(vault: Path) -> dict[str, object]:
    """Build the canonical v4 projection in memory without writing it."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        index = _build_index_v4_at(vault, root_fd)
        _require_directory_path_identity(vault, root_fd)
        return index
    finally:
        os.close(root_fd)


def rebuild_index_v4(vault: Path) -> dict[str, object]:
    """Rebuild and atomically persist the active-only v4 projection."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        index = _build_index_v4_at(vault, root_fd)
        _write_json_at(
            root_fd,
            "keikeu_index.json",
            index,
            guard_path=vault,
            guard_fd=root_fd,
        )
        return index
    finally:
        os.close(root_fd)


def verify_index_v4(vault: Path) -> bool:
    """Compare disk JSON with the canonical v4 projection without mutation."""
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        stored = _read_json_at(root_fd, vault)
        canonical = _build_index_v4_at(vault, root_fd)
        _require_directory_path_identity(vault, root_fd)
        return stored == canonical
    finally:
        os.close(root_fd)


def _normalized_query(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("query must be a string")
    return unicodedata.normalize("NFC", value).casefold()


def _matches_v4(entry: dict[str, object], query: str) -> bool:
    if not query:
        return True
    return query in unicodedata.normalize("NFC", str(entry["search_text"])).casefold()


def _without_search_text(entry: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in entry.items() if key != "search_text"}


def query_index_v4(vault: Path, query: str = "") -> dict[str, object]:
    """Return a read-only active Library projection without leaking search_text."""
    index = build_index_v4(vault)
    needle = _normalized_query(query)
    papers = [
        _without_search_text(entry)
        for entry in index["papers"]
        if isinstance(entry, dict) and _matches_v4(entry, needle)
    ]
    return {"papers": papers, "errors": index["errors"]}


def query_trash_v4(vault: Path, query: str = "") -> dict[str, object]:
    """Scan Trash on demand; its search projection never enters the disk index."""
    needle = _normalized_query(query)
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        try:
            paths, scan_errors = _scan_paper_area_at(
                root_fd,
                vault,
                Path(".trash/cache"),
            )
        except FileNotFoundError:
            paths, scan_errors = [], []
        papers: list[dict[str, object]] = []
        errors: list[dict[str, str]] = list(scan_errors)
        for relative in paths:
            try:
                paper = _read_paper_v4_at(root_fd, vault, relative)
                entry = _paper_v4_entry(relative, paper, base_parts=2)
            except (OSError, ValueError, UnicodeError) as exc:
                reason = str(exc)
                errors.append({"path": str(relative), "reason": reason})
                fallback_search = "\0".join((str(relative), relative.stem))
                entry = {
                    "code": relative.stem,
                    "display_name": None,
                    "path": str(relative),
                    "folder": relative.parts[2] if len(relative.parts) == 4 else None,
                    "tags": [],
                    "preview": "",
                    "page_count": 0,
                    "page_names": [],
                    "search_text": fallback_search,
                    "created": None,
                    "updated": None,
                    "repair_reason": reason,
                }
            if _matches_v4(entry, needle):
                papers.append(_without_search_text(entry))
        _require_directory_path_identity(vault, root_fd)
        papers.sort(key=lambda entry: str(entry["path"]))
        errors = [
            {"path": path, "reason": reason}
            for path, reason in sorted({(item["path"], item["reason"]) for item in errors})
        ]
        return {"papers": papers, "errors": errors}
    finally:
        os.close(root_fd)
