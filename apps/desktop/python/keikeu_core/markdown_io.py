"""Paper v4 Markdown serialization and legacy-code identification.

Paper Markdown is the active durable asset contract.  v0.1 Cache parsing is
kept separately in ``legacy_v01.py`` for the explicit one-way migrator; this
module neither reads nor writes Cache or Outline Markdown.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import unicodedata

from keikeu_core.legacy_v3 import parse_paper_v3_bytes
from keikeu_core.models import CardPageV4, PaperV4, validate_paper_code
from keikeu_core.vault import (
    _create_regular_bytes_at,
    _open_pinned_vault_root,
    _open_relative_directory_no_follow,
    _paper_code_exists_at,
    _read_regular_bytes_at,
    _require_directory_path_identity,
    _unlink_owned_file_at,
    _supported_paper_relative_path,
    atomic_exchange_at_no_follow,
    open_regular_no_follow,
    require_atomic_exchange,
)

__all__ = [
    "branch_paper_v4",
    "render_paper_v4_bytes",
    "parse_paper_v4_bytes",
    "paper_code_from_bytes",
    "read_paper_v4_snapshot",
    "replace_paper_v4_bytes",
    "write_paper_v4",
]


_FENCE = "---"
_V4_REQUIRED_FRONTMATTER = ("type", "schema_version", "code", "created", "updated")
_V4_OPTIONAL_FRONTMATTER = ("display_name", "legacy_title")
_V4_RESERVED_FRONTMATTER = set(_V4_REQUIRED_FRONTMATTER + _V4_OPTIONAL_FRONTMATTER)
_V4_PAGE_START_PREFIX = "<!-- keikeu:page "
_V4_PAGE_START_SUFFIX = " -->"
_V4_PAGE_END = "<!-- /keikeu:page -->"
_V4_TAGS_HEADER = "## Tags"


def _escape_scalar(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def _unescape_scalar(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            escaped = value[index + 1]
            decoded = {"n": "\n", "r": "\r", "\\": "\\"}.get(escaped)
            if decoded is None:
                out.extend(("\\", escaped))
            else:
                out.append(decoded)
            index += 2
        else:
            out.append(value[index])
            index += 1
    return "".join(out)


def _format_frontmatter(pairs: list[tuple[str, str]]) -> str:
    return "\n".join(
        [_FENCE, *[f"{key}: {_escape_scalar(value)}" for key, value in pairs], _FENCE]
    )


def _validate_v4_frontmatter_key(key: str) -> None:
    if not key or ":" in key:
        raise ValueError("Paper v4 frontmatter key must be non-empty without colons")
    if any(
        unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
        for character in key
    ):
        raise ValueError("Paper v4 frontmatter key contains an invalid character")


def _decode_v4_text(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Paper v4 must not contain a UTF-8 BOM")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Paper v4 must be valid UTF-8") from None
    if "\r" in text:
        without_crlf = text.replace("\r\n", "")
        if "\r" in without_crlf:
            raise ValueError("Paper v4 contains a bare CR line ending")
        if "\n" in without_crlf:
            raise ValueError("Paper v4 must not mix LF and CRLF line endings")
        text = text.replace("\r\n", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text


def _parse_v4_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    if not lines or lines[0] != _FENCE:
        raise ValueError("Paper v4 is missing the opening frontmatter fence")
    frontmatter: dict[str, str] = {}
    index = 1
    while index < len(lines) and lines[index] != _FENCE:
        line = lines[index]
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError("Paper v4 frontmatter line must contain a colon")
        key = key.strip()
        _validate_v4_frontmatter_key(key)
        if key in frontmatter:
            raise ValueError(f"Paper v4 frontmatter repeats key: {key}")
        frontmatter[key] = _unescape_scalar(value.strip())
        index += 1
    if index >= len(lines):
        raise ValueError("Paper v4 frontmatter fence was never closed")
    for key in _V4_REQUIRED_FRONTMATTER:
        if key not in frontmatter:
            raise ValueError(f"Paper v4 frontmatter is missing {key}")
    return frontmatter, index + 1


def _is_v4_start_marker(line: str) -> bool:
    return line.startswith(_V4_PAGE_START_PREFIX) and line.endswith(
        _V4_PAGE_START_SUFFIX
    )


def _is_v4_reserved_content_line(line: str) -> bool:
    candidate = line.lstrip("\\")
    return candidate == _V4_PAGE_END or _is_v4_start_marker(candidate)


def _escape_v4_content_line(line: str) -> str:
    return f"\\{line}" if _is_v4_reserved_content_line(line) else line


def _unescape_v4_content_line(line: str) -> str:
    if line.startswith("\\") and _is_v4_reserved_content_line(line):
        return line[1:]
    return line


def _v4_page_marker(page: CardPageV4) -> str:
    name = "null"
    if page.name is not None:
        name = json.dumps(page.name, ensure_ascii=False).replace("-", "\\u002d")
    page_type = json.dumps(page.type, ensure_ascii=False, separators=(",", ":"))
    return (
        f'{_V4_PAGE_START_PREFIX}{{"name":{name},"type":{page_type}}}'
        f"{_V4_PAGE_START_SUFFIX}"
    )


def _parse_v4_page_marker(line: str) -> tuple[str | None, str | None]:
    if not _is_v4_start_marker(line):
        raise ValueError("Paper v4 page must start with an exact page marker")
    payload = line[len(_V4_PAGE_START_PREFIX) : -len(_V4_PAGE_START_SUFFIX)]
    if "--" in payload:
        raise ValueError("Paper v4 page marker payload contains raw '--'")

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Paper v4 page marker repeats JSON key: {key}")
            value[key] = item
        return value

    try:
        metadata = json.loads(payload, object_pairs_hook=unique_object)
    except json.JSONDecodeError:
        raise ValueError("Paper v4 page marker contains invalid JSON") from None
    if not isinstance(metadata, dict) or set(metadata) != {"name", "type"}:
        raise ValueError("Paper v4 page marker must contain only name and type")
    name = metadata["name"]
    page_type = metadata["type"]
    if name is not None and not isinstance(name, str):
        raise ValueError("Paper v4 page marker name must be a string or null")
    if page_type not in (None, "summary", "snapshot", "whisper"):
        raise ValueError("Paper v4 page marker contains an invalid type")
    return name, page_type


def _clone_v4_paper(paper: PaperV4) -> PaperV4:
    if not isinstance(paper, PaperV4):
        raise TypeError("paper must be a PaperV4")
    return PaperV4(
        code=paper.code,
        pages=[
            CardPageV4(name=page.name, content=page.content, type=page.type)
            for page in paper.pages
        ],
        display_name=paper.display_name,
        tags=list(paper.tags),
        created=paper.created,
        updated=paper.updated,
        legacy_title=paper.legacy_title,
        extra_frontmatter=paper.extra_frontmatter.copy(),
    )


def render_paper_v4_bytes(paper: PaperV4) -> bytes:
    """Serialize one validated Paper v4 model as canonical UTF-8/LF bytes."""
    paper = _clone_v4_paper(paper)
    frontmatter: list[tuple[str, str]] = [
        ("type", "paper"),
        ("schema_version", "4"),
        ("code", paper.code),
        ("created", paper.created.isoformat()),
        ("updated", paper.updated.isoformat()),
    ]
    if paper.display_name is not None:
        frontmatter.append(("display_name", paper.display_name))
    if paper.legacy_title is not None:
        frontmatter.append(("legacy_title", paper.legacy_title))
    for key, value in paper.extra_frontmatter.items():
        _validate_v4_frontmatter_key(key)
        if key in _V4_RESERVED_FRONTMATTER:
            raise ValueError(f"extra_frontmatter conflicts with reserved key: {key}")
        frontmatter.append((key, value))

    blocks: list[str] = []
    for page in paper.pages:
        content_lines = [] if page.content == "" else page.content.split("\n")
        blocks.append(
            "\n".join(
                [
                    _v4_page_marker(page),
                    *[_escape_v4_content_line(line) for line in content_lines],
                    _V4_PAGE_END,
                ]
            )
        )
    tags = _V4_TAGS_HEADER
    if paper.tags:
        tags = f"{tags}\n\n" + "\n".join(f"- {tag}" for tag in paper.tags)
    body = "\n\n".join([f"# {paper.code}", *blocks, tags])
    return f"{_format_frontmatter(frontmatter)}\n{body}\n".encode("utf-8")


def parse_paper_v4_bytes(data: bytes) -> PaperV4:
    """Strictly parse one Paper v4 byte snapshot without filesystem I/O."""
    if not isinstance(data, bytes):
        raise TypeError("Paper v4 data must be bytes")
    lines = _decode_v4_text(data).split("\n")
    frontmatter, index = _parse_v4_frontmatter(lines)
    if frontmatter["type"] != "paper" or frontmatter["schema_version"] != "4":
        raise ValueError("Paper v4 must declare type: paper and schema_version: 4")
    try:
        code = validate_paper_code(frontmatter["code"])
        created = datetime.fromisoformat(frontmatter["created"])
        updated = datetime.fromisoformat(frontmatter["updated"])
    except ValueError:
        raise ValueError("Paper v4 has invalid identity or datetime frontmatter") from None
    if index >= len(lines) or lines[index] != f"# {code}":
        raise ValueError("Paper v4 heading must exactly match its code")
    index += 1
    if index >= len(lines) or lines[index] != "":
        raise ValueError("Paper v4 heading must be followed by exactly one blank line")
    index += 1

    pages: list[CardPageV4] = []
    while index < len(lines) and _is_v4_start_marker(lines[index]):
        page_number = len(pages) + 1
        try:
            name, page_type = _parse_v4_page_marker(lines[index])
        except ValueError as exc:
            raise ValueError(f"Paper v4 page {page_number}: {exc}") from None
        index += 1
        content_lines: list[str] = []
        while index < len(lines) and lines[index] != _V4_PAGE_END:
            line = lines[index]
            if _is_v4_start_marker(line):
                raise ValueError(
                    f"Paper v4 page {page_number} contains a nested start marker"
                )
            if _is_v4_reserved_content_line(line) and not line.startswith("\\"):
                raise ValueError(
                    f"Paper v4 page {page_number} contains an unescaped reserved marker"
                )
            content_lines.append(_unescape_v4_content_line(line))
            index += 1
        if index >= len(lines):
            raise ValueError(f"Paper v4 page {len(pages) + 1} is missing its end marker")
        try:
            pages.append(
                CardPageV4(name=name, content="\n".join(content_lines), type=page_type)
            )
        except ValueError as exc:
            raise ValueError(f"Paper v4 page {page_number}: {exc}") from None
        index += 1
        if index >= len(lines) or lines[index] != "":
            raise ValueError("Paper v4 page blocks must be separated by one blank line")
        index += 1
    if not pages:
        raise ValueError("Paper v4 must contain at least one page block")
    if index >= len(lines) or lines[index] != _V4_TAGS_HEADER:
        raise ValueError("Paper v4 must end with one Tags section")
    index += 1
    tags: list[str] = []
    if index < len(lines):
        if lines[index] != "":
            raise ValueError("Paper v4 Tags items require one blank line after the heading")
        index += 1
        if index >= len(lines):
            raise ValueError("Paper v4 empty Tags must not contain an extra blank line")
        while index < len(lines):
            line = lines[index]
            if not line.startswith("- ") or not line[2:].strip():
                raise ValueError("Paper v4 Tags must use non-empty '- value' items")
            tags.append(line[2:])
            index += 1
    known = _V4_RESERVED_FRONTMATTER
    return PaperV4(
        code=code,
        pages=pages,
        display_name=frontmatter.get("display_name"),
        tags=tags,
        created=created,
        updated=updated,
        legacy_title=frontmatter.get("legacy_title"),
        extra_frontmatter={
            key: value for key, value in frontmatter.items() if key not in known
        },
    )


def paper_code_from_bytes(data: bytes) -> str:
    """Return the immutable code from a supported v3 or v4 Paper snapshot."""
    try:
        return parse_paper_v4_bytes(data).code
    except (ValueError, UnicodeError):
        return parse_paper_v3_bytes(data).code


def _supported_v4_relative_path(
    vault: Path,
    candidate: str | Path,
    *,
    active_only: bool,
) -> Path:
    bases = (("cache",),) if active_only else (("cache",), (".trash", "cache"))
    errors: list[ValueError] = []
    for base in bases:
        try:
            return _supported_paper_relative_path(vault, candidate, base)
        except ValueError as exc:
            errors.append(exc)
    expected = "cache/[folder/]Paper.md"
    if not active_only:
        expected += " or .trash/cache/[folder/]Paper.md"
    raise ValueError(f"expected {expected}") from errors[-1]


def replace_paper_v4_bytes(
    vault: Path,
    path: str | Path,
    proposed_bytes: bytes,
    *,
    expected_source_bytes: bytes,
) -> None:
    """CAS-replace one active or Trash legacy Paper with validated v4 bytes."""
    if not isinstance(expected_source_bytes, bytes) or not isinstance(proposed_bytes, bytes):
        raise TypeError("expected and proposed Paper snapshots must be bytes")
    proposed = parse_paper_v4_bytes(proposed_bytes)
    require_atomic_exchange()
    vault, root_fd = _open_pinned_vault_root(vault)
    relative = _supported_v4_relative_path(vault, path, active_only=False)
    target = vault / relative
    directory_fd: int | None = None
    try:
        directory_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
        source_bytes, source_identity = _read_regular_bytes_at(
            directory_fd,
            relative.name,
            target,
        )
        if source_bytes != expected_source_bytes:
            raise ValueError("Paper changed externally; replacement refused")
        source_code = paper_code_from_bytes(source_bytes)
        if proposed.code != source_code:
            raise ValueError("Paper codes are immutable during migration")
        if relative.name != f"{proposed.code}.md":
            raise ValueError("Paper filename and frontmatter code do not match")
        if _paper_code_exists_at(
            root_fd,
            vault,
            proposed.code,
            parse_code=paper_code_from_bytes,
            excluding=relative,
        ):
            raise ValueError(f"duplicate Paper code blocks mutation: {proposed.code}")
        _atomic_compare_exchange_bytes_at(
            directory_fd,
            target,
            relative.name,
            proposed_bytes,
            expected_bytes=expected_source_bytes,
            expected_identity=source_identity,
            guard_path=target.parent,
            guard_fd=directory_fd,
        )
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
        os.close(root_fd)


def write_paper_v4(
    vault: Path,
    paper: PaperV4,
    *,
    destination: str | Path,
) -> Path:
    """Create one new active Paper v4 without overwriting any existing path."""
    data = render_paper_v4_bytes(paper)
    vault, root_fd = _open_pinned_vault_root(vault)
    relative = _supported_v4_relative_path(vault, destination, active_only=True)
    name = f"{paper.code}.md"
    if relative.name != name:
        raise ValueError("Paper destination filename must match its code")
    path = vault / relative
    parent_fd: int | None = None
    identity: tuple[int, int] | None = None
    try:
        parent_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
        _require_new_regular_name_at(parent_fd, name, path)
        _require_directory_path_identity(path.parent, parent_fd)
        if _paper_code_exists_at(
            root_fd,
            vault,
            paper.code,
            parse_code=paper_code_from_bytes,
        ):
            raise FileExistsError(
                f"Paper code already exists in active/Trash: {paper.code}"
            )
        identity = _create_regular_bytes_at(parent_fd, name, data, path)
        try:
            stored_bytes, stored_identity = _read_regular_bytes_at(parent_fd, name, path)
            if stored_identity != identity or stored_bytes != data:
                raise ValueError(f"Paper changed while creating: {path}")
            _require_directory_path_identity(path.parent, parent_fd)
            if _paper_code_exists_at(
                root_fd,
                vault,
                paper.code,
                parse_code=paper_code_from_bytes,
                excluding=relative,
            ):
                raise FileExistsError(
                    f"Paper code concurrently created in active/Trash: {paper.code}"
                )
        except Exception:
            if not _unlink_owned_bytes_at(parent_fd, name, identity, data):
                raise OSError(errno.EIO, f"Paper create could not roll back safely: {path}")
            raise
        return path
    finally:
        if parent_fd is not None:
            os.close(parent_fd)
        os.close(root_fd)


def branch_paper_v4(
    vault: Path,
    source: str | Path,
    destination: str | Path,
    new_code: str,
    *,
    expected_source_bytes: bytes,
    now: datetime | None = None,
) -> Path:
    """Create one same-folder v4 branch from an exact active snapshot."""
    if not isinstance(expected_source_bytes, bytes):
        raise TypeError("expected_source_bytes must be bytes")
    new_code = validate_paper_code(new_code)
    vault, root_fd = _open_pinned_vault_root(vault)
    source_relative = _supported_v4_relative_path(vault, source, active_only=True)
    destination_relative = _supported_v4_relative_path(vault, destination, active_only=True)
    if destination_relative.name != f"{new_code}.md":
        raise ValueError("branch destination filename must match its new code")
    if destination_relative.parent != source_relative.parent:
        raise ValueError("branch destination must stay in the source folder")
    source_path = vault / source_relative
    destination_path = vault / destination_relative
    source_fd: int | None = None
    destination_fd: int | None = None
    try:
        source_fd = _open_relative_directory_no_follow(root_fd, source_relative.parent, vault)
        destination_fd = _open_relative_directory_no_follow(
            root_fd,
            destination_relative.parent,
            vault,
        )
        source_bytes, source_identity = _read_regular_bytes_at(
            source_fd,
            source_relative.name,
            source_path,
        )
        if source_bytes != expected_source_bytes:
            raise ValueError(f"Paper changed before branch copy: {source_path}")
        source_paper = parse_paper_v4_bytes(source_bytes)
        if source_relative.name != f"{source_paper.code}.md":
            raise ValueError("Paper filename and frontmatter code do not match")
        if _paper_code_exists_at(
            root_fd,
            vault,
            source_paper.code,
            parse_code=paper_code_from_bytes,
            excluding=source_relative,
        ):
            raise ValueError(f"duplicate Paper code blocks mutation: {source_paper.code}")
        branch_time = now or datetime.now()
        branched = PaperV4(
            code=new_code,
            display_name=(
                f"{source_paper.display_name[:195]} · 分支"
                if source_paper.display_name is not None
                else None
            ),
            pages=[
                CardPageV4(name=page.name, content=page.content, type=page.type)
                for page in source_paper.pages
            ],
            tags=list(source_paper.tags),
            created=branch_time,
            updated=branch_time,
            legacy_title=source_paper.legacy_title,
            extra_frontmatter=source_paper.extra_frontmatter.copy(),
        )
        target_bytes = render_paper_v4_bytes(branched)
        _require_new_regular_name_at(
            destination_fd,
            destination_relative.name,
            destination_path,
        )
        if _paper_code_exists_at(
            root_fd,
            vault,
            new_code,
            parse_code=paper_code_from_bytes,
        ):
            raise FileExistsError(f"Paper code already exists in active/Trash: {new_code}")
        _require_directory_path_identity(source_path.parent, source_fd)
        _require_directory_path_identity(destination_path.parent, destination_fd)
        target_identity = _create_regular_bytes_at(
            destination_fd,
            destination_relative.name,
            target_bytes,
            destination_path,
        )
        try:
            current_source, current_identity = _read_regular_bytes_at(
                source_fd,
                source_relative.name,
                source_path,
            )
            stored_bytes, stored_identity = _read_regular_bytes_at(
                destination_fd,
                destination_relative.name,
                destination_path,
            )
            if current_identity != source_identity or current_source != source_bytes:
                raise ValueError(f"Paper changed during branch copy: {source_path}")
            if stored_identity != target_identity or stored_bytes != target_bytes:
                raise ValueError(f"branch Paper changed while creating: {destination_path}")
            _require_directory_path_identity(source_path.parent, source_fd)
            _require_directory_path_identity(destination_path.parent, destination_fd)
            if _paper_code_exists_at(
                root_fd,
                vault,
                new_code,
                parse_code=paper_code_from_bytes,
                excluding=destination_relative,
            ):
                raise FileExistsError(
                    f"Paper code concurrently created in active/Trash: {new_code}"
                )
        except Exception:
            if not _unlink_owned_bytes_at(
                destination_fd,
                destination_relative.name,
                target_identity,
                target_bytes,
            ):
                raise OSError(
                    errno.EIO,
                    "branch Paper could not roll back safely; source and branch were preserved",
                )
            raise
        return destination_path
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        if source_fd is not None:
            os.close(source_fd)
        os.close(root_fd)


def _entry_identity(directory_fd: int, name: str) -> tuple[int, int] | None:
    try:
        entry_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return entry_stat.st_dev, entry_stat.st_ino


def _unlink_owned_bytes_at(
    directory_fd: int,
    name: str,
    identity: tuple[int, int],
    expected_bytes: bytes,
) -> bool:
    return _unlink_owned_file_at(
        directory_fd,
        name,
        identity,
        expected_digest=hashlib.sha256(expected_bytes).hexdigest(),
    )


def _paper_update_recovery_error(target: Path, temporary: Path) -> OSError:
    return OSError(
        errno.EIO,
        "Paper update could not roll back safely; both contents were preserved "
        f"at {target} and {temporary}",
    )


def _rollback_paper_update_at(
    directory_fd: int,
    target_name: str,
    temporary_name: str,
    target: Path,
    temporary: Path,
    *,
    proposed_identity: tuple[int, int],
    previous_identity: tuple[int, int],
    proposed_bytes: bytes,
) -> None:
    target_identity = _entry_identity(directory_fd, target_name)
    temporary_identity = _entry_identity(directory_fd, temporary_name)
    if target_identity != proposed_identity or temporary_identity != previous_identity:
        raise _paper_update_recovery_error(target, temporary)
    try:
        atomic_exchange_at_no_follow(
            directory_fd,
            temporary_name,
            directory_fd,
            target_name,
        )
    except Exception as exc:
        raise _paper_update_recovery_error(target, temporary) from exc

    if not _unlink_owned_bytes_at(
        directory_fd,
        temporary_name,
        proposed_identity,
        proposed_bytes,
    ):
        raise _paper_update_recovery_error(target, temporary)


def _atomic_compare_exchange_bytes_at(
    directory_fd: int,
    target: Path,
    target_name: str,
    proposed_bytes: bytes,
    *,
    expected_bytes: bytes,
    expected_identity: tuple[int, int],
    guard_path: Path,
    guard_fd: int,
) -> None:
    while True:
        temporary_name = f".{target_name}.{secrets.token_hex(8)}.tmp"
        temporary = target.with_name(temporary_name)
        try:
            proposed_identity = _create_regular_bytes_at(
                directory_fd,
                temporary_name,
                proposed_bytes,
                temporary,
            )
        except FileExistsError:
            continue
        break

    try:
        _require_directory_path_identity(guard_path, guard_fd)
        atomic_exchange_at_no_follow(
            directory_fd,
            temporary_name,
            directory_fd,
            target_name,
        )
    except Exception:
        if not _unlink_owned_bytes_at(
            directory_fd,
            temporary_name,
            proposed_identity,
            proposed_bytes,
        ):
            raise _paper_update_recovery_error(target, temporary)
        raise

    try:
        previous_bytes, previous_identity = _read_regular_bytes_at(
            directory_fd,
            temporary_name,
            temporary,
        )
        if previous_bytes != expected_bytes or previous_identity != expected_identity:
            raise ValueError("Paper changed externally; update refused")
        _require_directory_path_identity(guard_path, guard_fd)
    except Exception as verification_error:
        try:
            rollback_identity = _entry_identity(directory_fd, temporary_name)
            if rollback_identity is None:
                raise _paper_update_recovery_error(target, temporary)
            _rollback_paper_update_at(
                directory_fd,
                target_name,
                temporary_name,
                target,
                temporary,
                proposed_identity=proposed_identity,
                previous_identity=rollback_identity,
                proposed_bytes=proposed_bytes,
            )
        except Exception as recovery_error:
            raise recovery_error from verification_error
        raise

    if not _unlink_owned_bytes_at(
        directory_fd,
        temporary_name,
        previous_identity,
        previous_bytes,
    ):
        raise _paper_update_recovery_error(target, temporary)


def _require_new_regular_name_at(
    directory_fd: int,
    name: str,
    display_path: Path,
) -> None:
    try:
        entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(entry.st_mode):
        raise ValueError(f"symlink is not supported: {display_path}")
    raise FileExistsError(f"Paper already exists: {display_path}")


def _read_bytes_no_follow(path: Path) -> tuple[bytes, tuple[int, int]]:
    descriptor = open_regular_no_follow(path)
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        data = handle.read()
        after = os.fstat(handle.fileno())
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
        raise ValueError(f"Paper changed while reading: {path}")
    return data, (after.st_dev, after.st_ino)


def read_paper_v4_snapshot(path: Path) -> tuple[PaperV4, bytes]:
    """Read and strictly parse one no-follow Paper v4 byte snapshot once."""
    data, _identity = _read_bytes_no_follow(path)
    return parse_paper_v4_bytes(data), data
