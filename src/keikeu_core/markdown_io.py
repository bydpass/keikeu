"""Paper v2 Markdown serialization.

Paper Markdown is the active durable asset contract.  v0.1 Cache parsing is
kept separately in ``legacy_v01.py`` for the explicit one-way migrator; this
module neither reads nor writes Cache or Outline Markdown.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
import os
from pathlib import Path
import re
import tempfile

from keikeu_core.models import Paper, validate_paper_code

__all__ = [
    "next_paper_code",
    "write_paper",
    "read_paper",
    "update_paper",
    "copy_paper_with_code",
    "rename_paper",
]


_FENCE = "---"
_PAPER_HEADERS = ("## 初稿副本", "## Summary", "## Highlights", "## Tags")
_PAPER_NUMBERED_ITEM_RE = re.compile(r"^([1-9]\d*)\. (.*)$")
_PAPER_CODE_FILENAME_RE = re.compile(r"^K-\d{8}-(\d{3})$")


def _escape_scalar(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def _unescape_scalar(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            out.append({"n": "\n", "r": "\r", "\\": "\\"}.get(value[index + 1], value[index + 1]))
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


def _paper_path(vault: Path, code: str) -> Path:
    return vault / "cache" / f"{validate_paper_code(code)}.md"


def next_paper_code(vault: Path, on_date: date | datetime | None = None) -> str:
    """Return the next unused neutral Paper code without reserving it."""
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
    cache_dir = vault / "cache"
    if cache_dir.is_dir():
        for path in cache_dir.glob(f"{prefix}*.md"):
            match = _PAPER_CODE_FILENAME_RE.fullmatch(path.stem)
            if match is not None:
                used_sequences.add(int(match.group(1)))
    for sequence in range(1, 1000):
        if sequence not in used_sequences:
            return f"{prefix}{sequence:03d}"
    raise ValueError(f"all Paper codes for {day.isoformat()} are in use")


def _render_paper(paper: Paper) -> str:
    paper.normalize()
    frontmatter: list[tuple[str, str]] = [
        ("type", "paper"),
        ("schema_version", "2"),
        ("code", paper.code),
        ("created", paper.created.isoformat()),
        ("updated", paper.updated.isoformat()),
    ]
    if paper.legacy_title is not None:
        frontmatter.append(("legacy_title", paper.legacy_title))
    known_fields = {key for key, _ in frontmatter}
    frontmatter.extend(
        (key, value)
        for key, value in paper.extra_frontmatter.items()
        if key not in known_fields
    )
    highlights = "\n".join(
        f"{index}. {highlight}" for index, highlight in enumerate(paper.highlights, start=1)
    )
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


def _write_temp_file(target: Path, text: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        return Path(handle.name)


def _atomic_replace_text(target: Path, text: str) -> None:
    temporary = _write_temp_file(target, text)
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_create_text(target: Path, text: str) -> None:
    temporary = _write_temp_file(target, text)
    try:
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def copy_paper_with_code(source: Path, destination: Path, new_code: str) -> None:
    """Atomically create a code-renamed Paper without overwriting a target."""
    new_code = validate_paper_code(new_code)
    paper = read_paper(source)
    _atomic_create_text(destination, _render_paper(replace(paper, code=new_code)))


def write_paper(vault: Path, paper: Paper) -> Path:
    """Persist a new Paper and freeze its initial Summary on first save."""
    paper.normalize()
    path = _paper_path(vault, paper.code)
    if path.exists():
        raise FileExistsError(f"Paper already exists: {path}")
    stored = replace(paper, initial_summary=paper.summary)
    _atomic_create_text(path, _render_paper(stored))
    paper.initial_summary = stored.initial_summary
    return path


def read_paper(path: Path) -> Paper:
    """Read a Paper v2 Markdown file and preserve unknown frontmatter fields."""
    frontmatter, body_lines = _split_document(path.read_text(encoding="utf-8"))
    if frontmatter.get("type") != "paper":
        raise ValueError("Paper must declare type: paper")
    if frontmatter.get("schema_version") != "2":
        raise ValueError("Paper must declare schema_version: 2")
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
    known_fields = {"type", "schema_version", "code", "created", "updated", "legacy_title"}
    return Paper(
        code=code,
        initial_summary=initial_summary,
        summary=sections.get("## Summary", ""),
        highlights=_parse_numbered_items(sections.get("## Highlights", "")),
        tags=_parse_bullet_items(sections.get("## Tags", "")),
        created=created,
        updated=updated,
        legacy_title=frontmatter.get("legacy_title"),
        extra_frontmatter={
            key: value for key, value in frontmatter.items() if key not in known_fields
        },
    )


def update_paper(path: Path, paper: Paper) -> None:
    """Update a Paper while preserving first-save and hand-authored metadata."""
    existing = read_paper(path)
    if paper.code != existing.code:
        raise ValueError("Paper code changes require rename_paper")
    paper.initial_summary = existing.initial_summary
    paper.legacy_title = existing.legacy_title
    paper.extra_frontmatter = existing.extra_frontmatter.copy()
    paper.normalize()
    _atomic_replace_text(path, _render_paper(paper))


def rename_paper(vault: Path, old_code: str, new_code: str) -> Path:
    """Explicitly rename a Paper code without overwriting another asset."""
    old_code = validate_paper_code(old_code)
    new_code = validate_paper_code(new_code)
    if old_code == new_code:
        raise ValueError("new Paper code must differ from the current code")
    source = _paper_path(vault, old_code)
    target = _paper_path(vault, new_code)
    if target.exists():
        raise FileExistsError(f"Paper already exists: {target}")
    if read_paper(source).code != old_code:
        raise ValueError("Paper filename and frontmatter code do not match")
    copy_paper_with_code(source, target, new_code)
    try:
        source.unlink()
    except OSError:
        target.unlink(missing_ok=True)
        raise
    return target
