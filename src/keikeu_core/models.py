"""Core data structures for keikeu.

Pure Python. No Flet, no GUI, no third-party dependencies.

Models for the keikeu pipeline: inspiration cache (灵感缓存) -> outline
Markdown (大纲). This module is data structures + validation ONLY.
Serialization (to_dict / from_dict / to_markdown) belongs to
``keikeu_core.markdown_io`` (Step 4), not here. Enum values are
str-backed so Step 4 can write them straight into Markdown frontmatter
and read them back without a translation table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

__all__ = [
    "CacheStatus",
    "EndingType",
    "RelationType",
    "Paper",
    "validate_paper_code",
    "Cache",
    "Relation",
    "Outline",
]


_PAPER_CODE_RE = re.compile(r"^K-(\d{8})-(\d{3})$")


def validate_paper_code(code: str) -> str:
    """Return a canonical Paper code or raise a clear ``ValueError``.

    Paper codes are intentionally neutral and stable: ``K-YYYYMMDD-NNN``.
    Validating the date as well as the shape prevents hand-edited filenames
    such as ``K-20261399-001`` from becoming durable identifiers.
    """
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


class CacheStatus(str, Enum):
    """Lifecycle state of an inspiration cache (appdesign.md 6.3).

    Kept deliberately small (appdesign.md 13.5 小枚举).
    """

    RAW = "raw"
    DRAFTING = "drafting"
    OUTLINED = "outlined"
    ARCHIVED = "archived"


class EndingType(str, Enum):
    """Ending classification for an outline (appdesign.md 5.2).

    OE (open ending) is the neutral default. ``CUSTOM`` pairs with the
    ``Outline.custom_ending`` free-text field; never stuff custom prose
    into this enum.
    """

    HE = "HE"
    BE = "BE"
    OE = "OE"
    CUSTOM = "custom"


class RelationType(str, Enum):
    """Logical relation between outlines (appdesign.md 5.2).

    Values are the user-facing Chinese labels written directly into
    outline Markdown section 7.
    """

    PREQUEL = "前作"
    SEQUEL = "续作"
    IF = "IF"
    SIDE_STORY = "外传"
    SAME_SERIES = "同系列"


def _coerce_enum(enum_cls: type[Enum], value: object, field_name: str) -> Enum:
    """Coerce ``value`` into a member of ``enum_cls`` with a clear error.

    Accepts either an existing enum member or any value the enum
    constructor understands (for these str-backed enums, the backing
    string, e.g. ``"raw"``).

    ``enum_cls(value)`` already raises ``ValueError`` on an unknown
    value, but its message ("'x' is not a valid CacheStatus") omits
    which field failed. We re-raise with field context to keep failures
    legible, and reject ``None`` up front so a missing/None value fails
    as a deliberate, well-labelled ValueError rather than an opaque one.

    The constructor is also guarded against ``TypeError`` (e.g. an
    unhashable value such as a list/dict): current CPython raises
    ``ValueError`` for these, but catching ``TypeError`` too keeps the
    "invalid input raises ValueError" contract from leaking on any
    runtime that classifies an unhashable lookup differently.
    """
    if value is None:
        raise ValueError(
            f"{field_name} must not be None; "
            f"expected a {enum_cls.__name__} or one of "
            f"{[m.value for m in enum_cls]!r}"
        )
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"{value!r} is not a valid {field_name}; "
            f"expected one of {[m.value for m in enum_cls]!r}"
        ) from None


@dataclass
class Cache:
    """An inspiration cache: a raw idea captured with low friction.

    ``raw`` is the verbatim spark and must never be summarized or
    rewritten (product invariant 1).
    """

    title: str
    raw: str
    notes: str = ""
    status: CacheStatus = CacheStatus.RAW
    created: datetime = field(default_factory=datetime.now)
    updated: datetime = field(default_factory=datetime.now)
    linked_outline: str | None = None

    def __post_init__(self) -> None:
        # Coerce a str (or any valid value) into the enum; None or an
        # unknown value raises a field-labelled ValueError.
        self.status = _coerce_enum(CacheStatus, self.status, "status")


@dataclass
class Paper:
    """A Road v0.2 writing unit, independent of v0.1 lifecycle state.

    ``initial_summary`` is allowed to be blank only before the first successful
    write. ``write_paper`` freezes it from ``summary``; ``update_paper`` then
    preserves it from the stored file. ``extra_frontmatter`` keeps unknown
    hand-authored fields round-trippable without making them product fields.
    """

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
        # Only empty strings are removed. Whitespace in a Highlight is author
        # content and must not be silently normalized.
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


@dataclass
class Relation:
    """A typed link from one outline to another local outline/cache.

    ``target_path`` is a path string into the user's vault; resolving
    and validating the target file is not this layer's job.
    """

    relation_type: RelationType
    target_path: str
    note: str = ""

    def __post_init__(self) -> None:
        self.relation_type = _coerce_enum(
            RelationType, self.relation_type, "relation_type"
        )


@dataclass
class Outline:
    """A structured outline derived from a cache (appdesign.md 5.1).

    Every field may be left blank in MVP; the GUI gently suggests
    completion but never enforces it. ``raw_inspiration`` mirrors the
    originating cache's ``raw`` and is likewise preserved verbatim.
    """

    title: str
    raw_inspiration: str = ""
    summary: str = ""
    fandom: str = ""
    characters: list[str] = field(default_factory=list)
    cp: str = ""
    warning_setting: str = ""
    warning_cp_structure: str = ""
    warning_elements: str = ""
    plot: str = ""
    ending_type: EndingType = EndingType.OE
    custom_ending: str = ""
    relations: list[Relation] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self.ending_type = _coerce_enum(
            EndingType, self.ending_type, "ending_type"
        )
