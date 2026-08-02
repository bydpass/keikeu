"""Frozen Paper v2/v3 model and pure codec for legacy migration only."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
import re
import unicodedata

from keikeu_core.models import validate_paper_code

__all__ = [
    "HighlightV3",
    "PaperV3",
    "parse_paper_v3_bytes",
    "render_paper_v3_bytes",
]


_FENCE = "---"
_HEADERS = ("## 初稿副本", "## Summary", "## Highlights", "## Tags")
_NUMBERED_ITEM_RE = re.compile(r"^([1-9]\d*)\. (.*)$")
_HIGHLIGHT_RE = re.compile(r"^([1-9]\d*)\. 名称：(.*)$")


def _validate_display_name(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("display_name must be a string or None")
    value = value.strip()
    if not value:
        return None
    if len(value) > 200:
        raise ValueError("display_name must contain at most 200 Unicode code points")
    if any(unicodedata.category(character) in {"Cc", "Zl", "Zp"} for character in value):
        raise ValueError("display_name must be one line without control characters")
    return value


@dataclass
class HighlightV3:
    content: str
    display_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise ValueError("Highlight content must be a string")
        self.display_name = _validate_display_name(self.display_name)


@dataclass
class PaperV3:
    code: str
    initial_summary: str
    summary: str
    display_name: str | None = None
    highlights: list[HighlightV3] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    updated: datetime = field(default_factory=datetime.now)
    legacy_title: str | None = None
    extra_frontmatter: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.code = validate_paper_code(self.code)
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must not be blank")
        if not isinstance(self.initial_summary, str):
            raise ValueError("initial_summary must be a string")
        self.display_name = _validate_display_name(self.display_name)
        if self.legacy_title is not None and not isinstance(self.legacy_title, str):
            raise ValueError("legacy_title must be a string or None")
        if not isinstance(self.highlights, list) or not all(
            isinstance(item, HighlightV3) for item in self.highlights
        ):
            raise ValueError("highlights must be a list of HighlightV3 values")
        self.highlights = [item for item in self.highlights if item.content.strip()]
        if not isinstance(self.tags, list) or not all(isinstance(tag, str) for tag in self.tags):
            raise ValueError("tags must be a list of strings")
        normalized: list[str] = []
        for tag in self.tags:
            cleaned = tag.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        self.tags = normalized
        if not isinstance(self.extra_frontmatter, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in self.extra_frontmatter.items()
        ):
            raise ValueError("extra_frontmatter must map strings to strings")


def _escape_scalar(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def _unescape_scalar(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            escaped = value[index + 1]
            decoded = {"n": "\n", "r": "\r", "\\": "\\"}.get(escaped)
            out.extend(("\\", escaped)) if decoded is None else out.append(decoded)
            index += 2
        else:
            out.append(value[index])
            index += 1
    return "".join(out)


def _format_frontmatter(pairs: list[tuple[str, str]]) -> str:
    return "\n".join(
        [_FENCE, *[f"{key}: {_escape_scalar(value)}" for key, value in pairs], _FENCE]
    )


def _split_document(text: str) -> tuple[dict[str, str], list[str]]:
    lines = text.split("\n")
    if not lines or lines[0] != _FENCE:
        raise ValueError("missing frontmatter fence at start of document")
    frontmatter: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line == _FENCE:
            return frontmatter, lines[index + 1 :]
        key, separator, value = line.partition(":")
        if separator:
            frontmatter[key.strip()] = _unescape_scalar(value.strip())
    raise ValueError("frontmatter fence was never closed")


def _split_sections(body_lines: list[str]) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffered: list[str] = []
    for line in body_lines:
        if line in _HEADERS:
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


def _parse_numbered_items(content: str) -> list[str]:
    if not content:
        return []
    items: list[str] = []
    current: str | None = None
    for line in content.split("\n"):
        match = _NUMBERED_ITEM_RE.fullmatch(line)
        if match is not None:
            if current is not None:
                items.append(current)
            current = match.group(2)
        elif current is not None:
            current = f"{current}\n{line}"
    if current is not None:
        items.append(current)
    return items or [content]


def _parse_v3_highlights(content: str) -> list[HighlightV3]:
    if not content:
        return []
    lines = content.split("\n")
    highlights: list[HighlightV3] = []
    index = 0
    while index < len(lines):
        match = _HIGHLIGHT_RE.fullmatch(lines[index])
        if match is None:
            raise ValueError("Paper v3 Highlight must start with 'n. 名称：'")
        display_name = match.group(2)
        index += 1
        if index >= len(lines) or lines[index] != "   内容：":
            raise ValueError("Paper v3 Highlight must include an indented 内容： line")
        index += 1
        content_lines: list[str] = []
        while index < len(lines) and _HIGHLIGHT_RE.fullmatch(lines[index]) is None:
            line = lines[index]
            if line == "" and index + 1 < len(lines) and _HIGHLIGHT_RE.fullmatch(lines[index + 1]):
                index += 1
                break
            if not line.startswith("   "):
                raise ValueError("Paper v3 Highlight content must keep its structural indent")
            content_lines.append(line[3:])
            index += 1
        highlights.append(HighlightV3("\n".join(content_lines), display_name))
    return highlights


def _parse_bullets(content: str) -> list[str]:
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


def render_paper_v3_bytes(paper: PaperV3) -> bytes:
    paper = replace(
        paper,
        highlights=[replace(item) for item in paper.highlights],
        tags=list(paper.tags),
        extra_frontmatter=paper.extra_frontmatter.copy(),
    )
    frontmatter = [
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
    known = {key for key, _value in frontmatter}
    frontmatter.extend(
        (key, value) for key, value in paper.extra_frontmatter.items() if key not in known
    )
    highlights: list[str] = []
    for index, item in enumerate(paper.highlights, start=1):
        highlights.extend(
            [
                f"{index}. 名称：{item.display_name or ''}",
                "   内容：",
                *[f"   {line}" for line in item.content.split("\n")],
            ]
        )
        if index < len(paper.highlights):
            highlights.append("")

    def section(header: str, content: str) -> str:
        return f"{header}\n\n{content}" if content else header

    body = "\n\n".join(
        [
            f"# {paper.code}",
            section("## 初稿副本", paper.initial_summary),
            section("## Summary", paper.summary),
            section("## Highlights", "\n".join(highlights)),
            section("## Tags", "\n".join(f"- {tag}" for tag in paper.tags)),
        ]
    )
    return f"{_format_frontmatter(frontmatter)}\n{body}\n".encode("utf-8")


def parse_paper_v3_bytes(data: bytes) -> PaperV3:
    if not isinstance(data, bytes):
        raise TypeError("Paper data must be bytes")
    frontmatter, body_lines = _split_document(data.decode("utf-8"))
    if frontmatter.get("type") != "paper":
        raise ValueError("Paper must declare type: paper")
    schema = frontmatter.get("schema_version")
    if schema not in {"2", "3"}:
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
        [HighlightV3(content=item) for item in _parse_numbered_items(highlight_content)]
        if schema == "2"
        else _parse_v3_highlights(highlight_content)
    )
    known = {
        "type",
        "schema_version",
        "code",
        "display_name",
        "created",
        "updated",
        "legacy_title",
    }
    return PaperV3(
        code=code,
        initial_summary=initial_summary,
        summary=sections.get("## Summary", ""),
        display_name=frontmatter.get("display_name"),
        highlights=highlights,
        tags=_parse_bullets(sections.get("## Tags", "")),
        created=created,
        updated=updated,
        legacy_title=frontmatter.get("legacy_title"),
        extra_frontmatter={key: value for key, value in frontmatter.items() if key not in known},
    )
