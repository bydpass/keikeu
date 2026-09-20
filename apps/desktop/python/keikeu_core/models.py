"""Paper v4 data structures and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
import unicodedata

__all__ = [
    "CardPageV4",
    "PaperV4",
    "validate_paper_code",
]


_PAPER_CODE_RE = re.compile(r"^K-(\d{8})-(\d{3})$")
_V4_RESERVED_FRONTMATTER = {
    "type",
    "schema_version",
    "code",
    "created",
    "updated",
    "display_name",
    "legacy_title",
}


def validate_paper_code(code: str) -> str:
    """Return a canonical Paper code or raise a clear ``ValueError``."""
    if not isinstance(code, str):
        raise ValueError("code must use the K-YYYYMMDD-NNN format")
    match = _PAPER_CODE_RE.fullmatch(code)
    if match is None:
        raise ValueError("code must use the K-YYYYMMDD-NNN format")
    try:
        datetime.strptime(match.group(1), "%Y%m%d")
    except ValueError:
        raise ValueError("code must contain a valid calendar date") from None
    if not 1 <= int(match.group(2)) <= 999:
        raise ValueError("code sequence must be between 001 and 999")
    return code


def _validate_v4_name(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or None")
    value = value.strip()
    if not value:
        return None
    if len(value) > 200:
        raise ValueError(f"{field_name} must contain at most 200 Unicode code points")
    if any(
        unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
        for character in value
    ):
        raise ValueError(f"{field_name} must be one line without control characters")
    return value


def _normalize_v4_tags(tags: list[str]) -> list[str]:
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError("tags must be a list of strings")
    normalized: list[str] = []
    for tag in tags:
        cleaned = tag.strip()
        if not cleaned:
            continue
        if any(
            unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
            for character in cleaned
        ):
            raise ValueError("tags must contain single-line values without control characters")
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


@dataclass
class CardPageV4:
    """One durable Paper v4 card page."""

    content: str
    name: str | None = None
    type: str | None = None

    def __post_init__(self) -> None:
        self.normalize()

    def normalize(self) -> None:
        if not isinstance(self.content, str):
            raise ValueError("page content must be a string")
        self.name = _validate_v4_name(self.name, "page name")
        if self.type not in (None, "summary", "snapshot", "whisper"):
            raise ValueError("page type must be summary, snapshot, whisper, or None")
        if self.name is None and not self.content.strip():
            raise ValueError("page must have a non-empty name or content")


@dataclass
class PaperV4:
    """One durable Paper v4 asset."""

    code: str
    pages: list[CardPageV4]
    display_name: str | None = None
    tags: list[str] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    updated: datetime = field(default_factory=datetime.now)
    legacy_title: str | None = None
    extra_frontmatter: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.normalize()

    def normalize(self) -> None:
        self.code = validate_paper_code(self.code)
        self.display_name = _validate_v4_name(self.display_name, "display_name")
        if not isinstance(self.pages, list) or not self.pages:
            raise ValueError("pages must contain at least one CardPageV4")
        if not all(isinstance(page, CardPageV4) for page in self.pages):
            raise ValueError("pages must be a list of CardPageV4 values")
        for page in self.pages:
            page.normalize()
        summary_pages = [
            index for index, page in enumerate(self.pages, start=1) if page.type == "summary"
        ]
        if len(summary_pages) > 1:
            raise ValueError(
                "Paper v4 may contain at most one summary page; found pages "
                + ", ".join(str(index) for index in summary_pages)
            )
        self.tags = _normalize_v4_tags(self.tags)
        if not isinstance(self.created, datetime) or not isinstance(self.updated, datetime):
            raise ValueError("created and updated must be datetime values")
        if self.legacy_title is not None and not isinstance(self.legacy_title, str):
            raise ValueError("legacy_title must be a string or None")
        if not isinstance(self.extra_frontmatter, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in self.extra_frontmatter.items()
        ):
            raise ValueError("extra_frontmatter must map strings to strings")
        for key in self.extra_frontmatter:
            if key != key.strip() or not key or ":" in key:
                raise ValueError("extra_frontmatter keys must be trimmed and contain no colons")
            if key in _V4_RESERVED_FRONTMATTER:
                raise ValueError(f"extra_frontmatter conflicts with reserved key: {key}")
            if any(
                unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
                for character in key
            ):
                raise ValueError("extra_frontmatter key contains an invalid character")
