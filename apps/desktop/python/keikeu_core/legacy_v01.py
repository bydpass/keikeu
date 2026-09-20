"""Frozen v0.1 Cache reader used only by the explicit migration module.

It intentionally has no Cache writer, no Outline parser, and no imports from
the active Paper model.  Once a vault has migrated, normal application code
never imports this module or reads its old Markdown.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

__all__ = ["LegacyCache", "LegacyCacheStatus", "read_v01_cache"]


_FENCE = "---"
_CACHE_HEADERS = ("## 原始灵感", "## 临时备注")


class LegacyCacheStatus(str, Enum):
    """The frozen status values present in v0.1 Cache frontmatter."""

    RAW = "raw"
    DRAFTING = "drafting"
    OUTLINED = "outlined"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class LegacyCache:
    """The small v0.1 Cache shape needed for one-way Paper conversion."""

    title: str
    raw: str
    notes: str
    status: LegacyCacheStatus
    created: datetime
    updated: datetime
    linked_outline: str | None


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
        if line in _CACHE_HEADERS:
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


def _read_title(body_lines: list[str]) -> str:
    for line in body_lines:
        if line.startswith("# "):
            return line[2:]
    return ""


def read_v01_cache(path: Path) -> LegacyCache:
    """Read one frozen v0.1 Cache without modifying it or parsing Outlines."""
    frontmatter, body_lines = _split_document(path.read_text(encoding="utf-8"))
    sections = _split_sections(body_lines)
    linked_outline = frontmatter.get("linked_outline", "") or None
    return LegacyCache(
        title=_read_title(body_lines),
        raw=sections.get("## 原始灵感", ""),
        notes=sections.get("## 临时备注", ""),
        status=LegacyCacheStatus(frontmatter["status"]),
        created=datetime.fromisoformat(frontmatter["created"]),
        updated=datetime.fromisoformat(frontmatter["updated"]),
        linked_outline=linked_outline,
    )
