"""Paper v2 data structures and validation.

The active core deliberately models only durable Paper assets.  Legacy v0.1
Cache fields are isolated in ``legacy_v01.py`` for the one-shot migrator and
Outline is not part of the Road v0.2 runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re

__all__ = ["Paper", "validate_paper_code"]


_PAPER_CODE_RE = re.compile(r"^K-(\d{8})-(\d{3})$")


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


@dataclass
class Paper:
    """A Road v0.2 writing unit without lifecycle state or Outline links."""

    code: str
    initial_summary: str
    summary: str
    highlights: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    updated: datetime = field(default_factory=datetime.now)
    legacy_title: str | None = None
    extra_frontmatter: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.normalize()

    def normalize(self) -> None:
        """Validate durable fields and apply the spec's lossless list cleanup."""
        self.code = validate_paper_code(self.code)
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must not be blank")
        if not isinstance(self.initial_summary, str):
            raise ValueError("initial_summary must be a string")
        if self.legacy_title is not None and not isinstance(self.legacy_title, str):
            raise ValueError("legacy_title must be a string or None")
        if not isinstance(self.highlights, list) or not all(
            isinstance(item, str) for item in self.highlights
        ):
            raise ValueError("highlights must be a list of strings")
        self.highlights = [item for item in self.highlights if item != ""]
        if not isinstance(self.tags, list) or not all(
            isinstance(tag, str) for tag in self.tags
        ):
            raise ValueError("tags must be a list of strings")
        normalized_tags: list[str] = []
        for tag in self.tags:
            cleaned = tag.strip()
            if cleaned and cleaned not in normalized_tags:
                normalized_tags.append(cleaned)
        self.tags = normalized_tags
        if not isinstance(self.extra_frontmatter, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in self.extra_frontmatter.items()
        ):
            raise ValueError("extra_frontmatter must map strings to strings")
