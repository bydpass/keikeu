"""Paper v2/v3 Markdown serialization.

Paper Markdown is the active durable asset contract.  v0.1 Cache parsing is
kept separately in ``legacy_v01.py`` for the explicit one-way migrator; this
module neither reads nor writes Cache or Outline Markdown.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
import errno
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat

from keikeu_core.models import Highlight, Paper, validate_paper_code
from keikeu_core.vault import (
    _create_regular_bytes_at,
    _direct_paper_relative_path,
    _move_regular_no_overwrite_at,
    _open_pinned_vault,
    _open_pinned_vault_root,
    _open_relative_directory_no_follow,
    _paper_code_exists_at,
    _read_regular_bytes_at,
    _require_directory_path_identity,
    _unlink_owned_file_at,
    _supported_paper_relative_path,
    atomic_exchange_at_no_follow,
    open_regular_no_follow,
    next_paper_code as _next_paper_code,
    require_atomic_exchange,
)

__all__ = [
    "next_paper_code",
    "write_paper",
    "read_paper",
    "read_paper_snapshot",
    "update_paper",
    "copy_paper_with_code",
    "rename_paper",
    "render_paper_bytes",
    "parse_paper_bytes",
]


_FENCE = "---"
_PAPER_HEADERS = ("## 初稿副本", "## Summary", "## Highlights", "## Tags")
_PAPER_NUMBERED_ITEM_RE = re.compile(r"^([1-9]\d*)\. (.*)$")
_PAPER_V3_HIGHLIGHT_RE = re.compile(r"^([1-9]\d*)\. 名称：(.*)$")


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
    return "\n".join([_FENCE, *[f"{key}: {_escape_scalar(value)}" for key, value in pairs], _FENCE])


def _split_document(text: str) -> tuple[dict[str, str], list[str]]:
    lines = text.split("\n")
    if not lines or lines[0] != _FENCE:
        raise ValueError("missing frontmatter fence at start of document")
    frontmatter: dict[str, str] = {}
    index = 1
    while index < len(lines):
        line = lines[index]
        index += 1
        if line == _FENCE:
            return frontmatter, lines[index:]
        key, separator, value = line.partition(":")
        if separator:
            frontmatter[key.strip()] = _unescape_scalar(value.strip())
    raise ValueError("frontmatter fence was never closed")


def _split_sections(body_lines: list[str]) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffered: list[str] = []
    for line in body_lines:
        if line in _PAPER_HEADERS:
            if current is not None:
                sections[current] = "\n".join(buffered)
            current = line
            buffered = []
        elif current is not None:
            buffered.append(line)
    if current is not None:
        sections[current] = "\n".join(buffered)
    for header, content in sections.items():
        if content.startswith("\n"):
            content = content[1:]
        if content.endswith("\n"):
            content = content[:-1]
        sections[header] = content
    return sections


def next_paper_code(vault: Path, on_date: date | datetime | None = None) -> str:
    """Compatibility entry point for Vault-owned cross-path allocation."""
    return _next_paper_code(
        vault,
        on_date,
        parse_code=_paper_code_from_bytes,
    )


def _paper_code_from_bytes(data: bytes) -> str:
    return parse_paper_bytes(data).code


def _render_paper(paper: Paper) -> str:
    paper = replace(
        paper,
        highlights=[replace(highlight) for highlight in paper.highlights],
        tags=list(paper.tags),
        extra_frontmatter=paper.extra_frontmatter.copy(),
    )
    paper.normalize()
    frontmatter: list[tuple[str, str]] = [
        ("type", "paper"),
        ("schema_version", "3"),
        ("code", paper.code),
        ("created", paper.created.isoformat()),
        ("updated", paper.updated.isoformat()),
    ]
    if paper.display_name is not None:
        frontmatter.append(("display_name", paper.display_name))
    if paper.legacy_title is not None:
        frontmatter.append(("legacy_title", paper.legacy_title))
    known_fields = {key for key, _ in frontmatter}
    frontmatter.extend(
        (key, value)
        for key, value in paper.extra_frontmatter.items()
        if key not in known_fields
    )
    rendered_highlights: list[str] = []
    for index, highlight in enumerate(paper.highlights, start=1):
        rendered_highlights.extend(
            [
                f"{index}. 名称：{highlight.display_name or ''}",
                "   内容：",
                *[f"   {line}" for line in highlight.content.split("\n")],
            ]
        )
        if index < len(paper.highlights):
            rendered_highlights.append("")
    highlights = "\n".join(rendered_highlights)
    tags = "\n".join(f"- {tag}" for tag in paper.tags)

    def section(header: str, content: str) -> str:
        return f"{header}\n\n{content}" if content else header

    body = "\n\n".join(
        [
            f"# {paper.code}",
            section("## 初稿副本", paper.initial_summary),
            section("## Summary", paper.summary),
            section("## Highlights", highlights),
            section("## Tags", tags),
        ]
    )
    return f"{_format_frontmatter(frontmatter)}\n{body}\n"


def _parse_numbered_items(content: str) -> list[str]:
    if not content:
        return []
    items: list[str] = []
    current: str | None = None
    for line in content.split("\n"):
        match = _PAPER_NUMBERED_ITEM_RE.fullmatch(line)
        if match is not None:
            if current is not None:
                items.append(current)
            current = match.group(2)
        elif current is not None:
            current = f"{current}\n{line}"
    if current is not None:
        items.append(current)
    return items or [content]


def _parse_v3_highlights(content: str) -> list[Highlight]:
    if not content:
        return []
    lines = content.split("\n")
    highlights: list[Highlight] = []
    index = 0
    while index < len(lines):
        match = _PAPER_V3_HIGHLIGHT_RE.fullmatch(lines[index])
        if match is None:
            raise ValueError("Paper v3 Highlight must start with 'n. 名称：'")
        display_name = match.group(2)
        index += 1
        if index >= len(lines) or lines[index] != "   内容：":
            raise ValueError("Paper v3 Highlight must include an indented 内容： line")
        index += 1
        content_lines: list[str] = []
        while index < len(lines) and _PAPER_V3_HIGHLIGHT_RE.fullmatch(lines[index]) is None:
            line = lines[index]
            if (
                line == ""
                and index + 1 < len(lines)
                and _PAPER_V3_HIGHLIGHT_RE.fullmatch(lines[index + 1]) is not None
            ):
                index += 1
                break
            if not line.startswith("   "):
                raise ValueError("Paper v3 Highlight content must keep its structural indent")
            content_lines.append(line[3:])
            index += 1
        highlights.append(
            Highlight(
                display_name=display_name,
                content="\n".join(content_lines),
            )
        )
    return highlights


def _parse_bullet_items(content: str) -> list[str]:
    if not content:
        return []
    items: list[str] = []
    current: str | None = None
    for line in content.split("\n"):
        if line.startswith("- "):
            if current is not None:
                items.append(current)
            current = line[2:]
        elif current is not None:
            current = f"{current}\n{line}"
    if current is not None:
        items.append(current)
    return items or [content]


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


def _copy_source_relative(vault: Path, source: str | Path) -> Path:
    source_path = Path(source).expanduser()
    if ".." in source_path.parts:
        raise ValueError("Paper source must be a direct active or Trash file")
    if source_path.is_absolute():
        try:
            relative = source_path.relative_to(vault)
        except ValueError as exc:
            raise ValueError("Paper source is outside the selected Vault") from exc
    else:
        relative = source_path
    if (
        relative.parts[:-1] not in {("cache",), (".trash", "cache")}
        or len(relative.parts) not in {2, 3}
        or relative.suffix != ".md"
        or not relative.stem
    ):
        raise ValueError("Paper source must be a direct active or Trash file")
    return relative


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


def _copy_paper_with_code_at(
    source_directory_fd: int,
    source_name: str,
    source: Path,
    destination_directory_fd: int,
    destination_name: str,
    destination: Path,
    new_code: str,
    *,
    expected_source_bytes: bytes,
    guard_path: Path,
    guard_fd: int,
) -> tuple[tuple[int, int], tuple[int, int], bytes]:
    source_bytes, source_identity = _read_regular_bytes_at(
        source_directory_fd,
        source_name,
        source,
    )
    if source_bytes != expected_source_bytes:
        raise ValueError(f"Paper changed while copying: {source}")
    target_bytes = render_paper_bytes(
        replace(parse_paper_bytes(source_bytes), code=new_code)
    )
    _require_new_regular_name_at(
        destination_directory_fd,
        destination_name,
        destination,
    )
    _require_directory_path_identity(guard_path, guard_fd)
    target_identity = _create_regular_bytes_at(
        destination_directory_fd,
        destination_name,
        target_bytes,
        destination,
    )
    try:
        current_bytes, current_identity = _read_regular_bytes_at(
            source_directory_fd,
            source_name,
            source,
        )
        if current_identity != source_identity or current_bytes != source_bytes:
            raise ValueError(f"Paper changed while copying: {source}")
        _require_directory_path_identity(guard_path, guard_fd)
    except Exception:
        if not _unlink_owned_bytes_at(
            destination_directory_fd,
            destination_name,
            target_identity,
            target_bytes,
        ):
            raise OSError(
                errno.EIO,
                "Paper copy changed during rollback; both files were preserved at "
                f"{source} and {destination}",
            )
        raise
    return target_identity, source_identity, target_bytes


def _rewrite_paper_code_at(
    source_directory_fd: int,
    source_name: str,
    source: Path,
    destination_directory_fd: int,
    destination_name: str,
    destination: Path,
    new_code: str,
    *,
    expected_source_bytes: bytes,
    guard_path: Path,
    guard_fd: int,
) -> None:
    target_identity, source_identity, target_bytes = _copy_paper_with_code_at(
        source_directory_fd,
        source_name,
        source,
        destination_directory_fd,
        destination_name,
        destination,
        new_code,
        expected_source_bytes=expected_source_bytes,
        guard_path=guard_path,
        guard_fd=guard_fd,
    )
    while True:
        recovery_name = f".{source_name}.{secrets.token_hex(8)}.rename"
        if _entry_identity(source_directory_fd, recovery_name) is None:
            break
    recovery = source.with_name(recovery_name)
    try:
        _move_regular_no_overwrite_at(
            source_directory_fd,
            source_name,
            source_directory_fd,
            recovery_name,
            source_path=source,
            destination_path=recovery,
            expected_source_identity=source_identity,
            expected_source_bytes=expected_source_bytes,
            guard_path=guard_path,
            guard_fd=guard_fd,
        )
    except Exception:
        if not _unlink_owned_bytes_at(
            destination_directory_fd,
            destination_name,
            target_identity,
            target_bytes,
        ):
            raise OSError(
                errno.EIO,
                "Paper rename could not roll back safely; both files were preserved "
                f"at {source} and {destination}",
            )
        raise
    if not _unlink_owned_bytes_at(
        source_directory_fd,
        recovery_name,
        source_identity,
        expected_source_bytes,
    ):
        raise OSError(
            errno.EIO,
            "Paper rename could not finish safely; both files were preserved "
            f"at {recovery} and {destination}",
        )


def copy_paper_with_code(
    vault: Path,
    source: str | Path,
    destination: str | Path,
    new_code: str,
    *,
    expected_source_bytes: bytes,
) -> tuple[tuple[int, int], tuple[int, int], bytes]:
    """Create a renamed copy only from the caller's exact source snapshot."""
    if not isinstance(expected_source_bytes, bytes):
        raise TypeError("expected_source_bytes must be bytes")
    new_code = validate_paper_code(new_code)
    vault, root_fd = _open_pinned_vault(vault)
    source_relative = _copy_source_relative(vault, source)
    destination_relative = _direct_paper_relative_path(
        vault,
        destination,
        ("cache",),
    )
    source_path = vault / source_relative
    destination_path = vault / destination_relative
    source_directory_fd: int | None = None
    destination_directory_fd: int | None = None
    try:
        source_directory_fd = _open_relative_directory_no_follow(
            root_fd,
            source_relative.parent,
            vault,
        )
        destination_directory_fd = _open_relative_directory_no_follow(
            root_fd,
            Path("cache"),
            vault,
        )
        return _copy_paper_with_code_at(
            source_directory_fd,
            source_relative.name,
            source_path,
            destination_directory_fd,
            destination_relative.name,
            destination_path,
            new_code,
            expected_source_bytes=expected_source_bytes,
            guard_path=vault,
            guard_fd=root_fd,
        )
    finally:
        if destination_directory_fd is not None:
            os.close(destination_directory_fd)
        if source_directory_fd is not None:
            os.close(source_directory_fd)
        os.close(root_fd)


def write_paper(
    vault: Path,
    paper: Paper,
    *,
    destination: str | Path,
) -> Path:
    """Persist a new Paper and freeze its initial Summary on first save."""
    paper.normalize()
    vault, root_fd = _open_pinned_vault_root(vault)
    name = f"{validate_paper_code(paper.code)}.md"
    relative = _supported_paper_relative_path(vault, destination, ("cache",))
    if relative.name != name:
        raise ValueError("Paper destination filename must match its code")
    path = vault / relative
    stored = replace(paper, initial_summary=paper.summary)
    data = render_paper_bytes(stored)
    cache_fd: int | None = None
    identity: tuple[int, int] | None = None
    try:
        cache_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
        _require_new_regular_name_at(cache_fd, name, path)
        _require_directory_path_identity(path.parent, cache_fd)
        if _paper_code_exists_at(
            root_fd,
            vault,
            paper.code,
            parse_code=_paper_code_from_bytes,
        ):
            raise FileExistsError(
                f"Paper code already exists in active/Trash: {paper.code}"
            )
        identity = _create_regular_bytes_at(cache_fd, name, data, path)
        try:
            stored_bytes, stored_identity = _read_regular_bytes_at(cache_fd, name, path)
            if stored_identity != identity or stored_bytes != data:
                raise ValueError(f"Paper changed while creating: {path}")
            _require_directory_path_identity(path.parent, cache_fd)
            if _paper_code_exists_at(
                root_fd,
                vault,
                paper.code,
                parse_code=_paper_code_from_bytes,
                excluding=relative,
            ):
                raise FileExistsError(
                    f"Paper code concurrently created in active/Trash: {paper.code}"
                )
        except Exception:
            if not _unlink_owned_bytes_at(cache_fd, name, identity, data):
                raise OSError(
                    errno.EIO,
                    f"Paper create could not roll back safely: {path}",
                )
            raise
    finally:
        if cache_fd is not None:
            os.close(cache_fd)
        os.close(root_fd)
    paper.initial_summary = stored.initial_summary
    return path


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


def _parse_paper_text(text: str) -> Paper:
    frontmatter, body_lines = _split_document(text)
    if frontmatter.get("type") != "paper":
        raise ValueError("Paper must declare type: paper")
    schema_version = frontmatter.get("schema_version")
    if schema_version not in {"2", "3"}:
        raise ValueError("Paper must declare schema_version: 2 or 3")
    try:
        code = frontmatter["code"]
        created = datetime.fromisoformat(frontmatter["created"])
        updated = datetime.fromisoformat(frontmatter["updated"])
    except KeyError as exc:
        raise ValueError(f"Paper frontmatter is missing {exc.args[0]}") from None
    except ValueError:
        raise ValueError("Paper has invalid datetime frontmatter") from None
    sections = _split_sections(body_lines)
    initial_summary = sections.get("## 初稿副本", "")
    if not initial_summary.strip():
        raise ValueError("Paper initial_summary must not be blank")
    highlight_content = sections.get("## Highlights", "")
    highlights = (
        [Highlight(content=item) for item in _parse_numbered_items(highlight_content)]
        if schema_version == "2"
        else _parse_v3_highlights(highlight_content)
    )
    known_fields = {
        "type",
        "schema_version",
        "code",
        "display_name",
        "created",
        "updated",
        "legacy_title",
    }
    return Paper(
        code=code,
        initial_summary=initial_summary,
        summary=sections.get("## Summary", ""),
        display_name=frontmatter.get("display_name"),
        highlights=highlights,
        tags=_parse_bullet_items(sections.get("## Tags", "")),
        created=created,
        updated=updated,
        legacy_title=frontmatter.get("legacy_title"),
        extra_frontmatter={
            key: value for key, value in frontmatter.items() if key not in known_fields
        },
    )


def render_paper_bytes(paper: Paper) -> bytes:
    """Serialize one Paper as UTF-8 Markdown without filesystem I/O."""
    return _render_paper(paper).encode("utf-8")


def parse_paper_bytes(data: bytes) -> Paper:
    """Parse one UTF-8 Paper snapshot without filesystem I/O."""
    if not isinstance(data, bytes):
        raise TypeError("Paper data must be bytes")
    return _parse_paper_text(data.decode("utf-8"))


def read_paper_snapshot(path: Path) -> tuple[Paper, bytes]:
    """Read and parse one no-follow byte snapshot exactly once."""
    data, _identity = _read_bytes_no_follow(path)
    return parse_paper_bytes(data), data


def read_paper(path: Path) -> Paper:
    """Read a Paper v2/v3 Markdown file and preserve unknown frontmatter fields."""
    paper, _data = read_paper_snapshot(path)
    return paper


def update_paper(
    vault: Path,
    path: str | Path,
    paper: Paper,
    *,
    expected_source_bytes: bytes,
) -> None:
    """Compare-and-swap a Paper without overwriting external changes."""
    if not isinstance(expected_source_bytes, bytes):
        raise TypeError("expected_source_bytes must be bytes")
    require_atomic_exchange()
    vault, root_fd = _open_pinned_vault_root(vault)
    relative = _supported_paper_relative_path(vault, path, ("cache",))
    target = vault / relative
    cache_fd: int | None = None
    try:
        cache_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
        source_bytes, source_identity = _read_regular_bytes_at(
            cache_fd,
            relative.name,
            target,
        )
        if source_bytes != expected_source_bytes:
            raise ValueError("Paper changed externally; update refused")
        existing = parse_paper_bytes(source_bytes)
        if paper.code != existing.code:
            raise ValueError("Paper code changes require rename_paper")
        if _paper_code_exists_at(
            root_fd,
            vault,
            paper.code,
            parse_code=_paper_code_from_bytes,
            excluding=relative,
        ):
            raise ValueError(
                f"duplicate Paper code blocks mutation: {paper.code}"
            )
        paper.initial_summary = existing.initial_summary
        paper.legacy_title = existing.legacy_title
        paper.extra_frontmatter = existing.extra_frontmatter.copy()
        paper.normalize()
        _atomic_compare_exchange_bytes_at(
            cache_fd,
            target,
            relative.name,
            render_paper_bytes(paper),
            expected_bytes=expected_source_bytes,
            expected_identity=source_identity,
            guard_path=target.parent,
            guard_fd=cache_fd,
        )
    finally:
        if cache_fd is not None:
            os.close(cache_fd)
        os.close(root_fd)


def rename_paper(vault: Path, old_code: str, new_code: str) -> Path:
    """Explicitly rename a Paper code without overwriting another asset."""
    old_code = validate_paper_code(old_code)
    new_code = validate_paper_code(new_code)
    if old_code == new_code:
        raise ValueError("new Paper code must differ from the current code")
    vault, root_fd = _open_pinned_vault(vault)
    source = vault / "cache" / f"{old_code}.md"
    target = vault / "cache" / f"{new_code}.md"
    cache_fd: int | None = None
    try:
        cache_fd = _open_relative_directory_no_follow(root_fd, Path("cache"), vault)
        _require_new_regular_name_at(cache_fd, target.name, target)
        source_bytes, _source_identity = _read_regular_bytes_at(
            cache_fd,
            source.name,
            source,
        )
        if parse_paper_bytes(source_bytes).code != old_code:
            raise ValueError("Paper filename and frontmatter code do not match")
        try:
            _rewrite_paper_code_at(
                cache_fd,
                source.name,
                source,
                cache_fd,
                target.name,
                target,
                new_code,
                expected_source_bytes=source_bytes,
                guard_path=target.parent,
                guard_fd=cache_fd,
            )
        except ValueError as exc:
            if "changed" in str(exc):
                raise ValueError(
                    f"Paper changed before rename cleanup: {source}"
                ) from exc
            raise
    finally:
        if cache_fd is not None:
            os.close(cache_fd)
        os.close(root_fd)
    return target
