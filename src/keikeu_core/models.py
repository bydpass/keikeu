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

__all__ = [
    "CacheStatus",
    "EndingType",
    "RelationType",
    "Cache",
    "Relation",
    "Outline",
]


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
