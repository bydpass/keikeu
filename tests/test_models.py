"""Tests for keikeu_core.models — data structures + validation only.

These tests pin the model contract for Step 2: enum coercion, validation
errors, defaults, mutable-default isolation, datetime defaults, and the
product invariants (verbatim raw input, custom ending stored separately).
Serialization is Step 4 (markdown_io) and is intentionally NOT exercised here.

Tests are deterministic: datetime fields are only checked for type/identity,
never for exact values.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core.models import (
    Cache,
    CacheStatus,
    EndingType,
    Outline,
    Relation,
    RelationType,
)


# --------------------------------------------------------------------------- #
# Enums: str-backed, exact members and values
# --------------------------------------------------------------------------- #


def test_cache_status_members_and_values():
    assert CacheStatus.RAW.value == "raw"
    assert CacheStatus.DRAFTING.value == "drafting"
    assert CacheStatus.OUTLINED.value == "outlined"
    assert CacheStatus.ARCHIVED.value == "archived"
    assert [m.value for m in CacheStatus] == [
        "raw",
        "drafting",
        "outlined",
        "archived",
    ]


def test_ending_type_members_and_values():
    assert EndingType.HE.value == "HE"
    assert EndingType.BE.value == "BE"
    assert EndingType.OE.value == "OE"
    assert EndingType.CUSTOM.value == "custom"
    assert [m.value for m in EndingType] == ["HE", "BE", "OE", "custom"]


def test_relation_type_members_and_values():
    assert RelationType.PREQUEL.value == "前作"
    assert RelationType.SEQUEL.value == "续作"
    assert RelationType.IF.value == "IF"
    assert RelationType.SIDE_STORY.value == "外传"
    assert RelationType.SAME_SERIES.value == "同系列"
    assert [m.value for m in RelationType] == [
        "前作",
        "续作",
        "IF",
        "外传",
        "同系列",
    ]


def test_all_enum_values_are_plain_str():
    # Step 4 frontmatter serialization relies on this being a pass-through.
    for enum_cls in (CacheStatus, EndingType, RelationType):
        for member in enum_cls:
            assert isinstance(member.value, str)


def test_str_backed_equality_holds():
    # str-backed Enum: member compares equal to its backing string.
    assert CacheStatus.DRAFTING == "drafting"
    assert EndingType.CUSTOM == "custom"
    assert RelationType.IF == "IF"


# --------------------------------------------------------------------------- #
# Cache: defaults
# --------------------------------------------------------------------------- #


def test_cache_minimal_defaults():
    c = Cache(title="t", raw="r")
    assert c.title == "t"
    assert c.raw == "r"
    assert c.notes == ""
    assert c.status is CacheStatus.RAW
    assert c.linked_outline is None
    assert isinstance(c.created, datetime)
    assert isinstance(c.updated, datetime)


# --------------------------------------------------------------------------- #
# REQUIRED 1: valid cache status accepted (str + enum member)
# --------------------------------------------------------------------------- #


def test_cache_status_str_coerced_to_enum():
    c = Cache(title="t", raw="r", status="drafting")
    assert c.status is CacheStatus.DRAFTING
    assert c.status == "drafting"  # str-backed equality still holds


def test_cache_status_enum_member_passes_through_unchanged():
    c = Cache(title="t", raw="r", status=CacheStatus.ARCHIVED)
    assert c.status is CacheStatus.ARCHIVED  # identity preserved, not re-wrapped


# --------------------------------------------------------------------------- #
# REQUIRED 2: invalid cache status rejected
# --------------------------------------------------------------------------- #


def test_cache_status_bogus_raises_value_error():
    with pytest.raises(ValueError) as exc:
        Cache(title="t", raw="r", status="bogus")
    msg = str(exc.value)
    assert "status" in msg
    # Message lists the valid values for legibility.
    for valid in ("raw", "drafting", "outlined", "archived"):
        assert valid in msg


def test_cache_status_none_raises_explicit_value_error():
    with pytest.raises(ValueError) as exc:
        Cache(title="t", raw="r", status=None)
    msg = str(exc.value)
    assert "status must not be None" in msg


# --------------------------------------------------------------------------- #
# REQUIRED 3: valid ending type accepted; Outline default is OE
# --------------------------------------------------------------------------- #


def test_outline_default_ending_type_is_oe():
    o = Outline(title="t")
    assert o.ending_type is EndingType.OE  # open ending, neutral default


def test_outline_ending_type_str_coerced():
    o = Outline(title="t", ending_type="BE")
    assert o.ending_type is EndingType.BE


def test_outline_ending_type_enum_member_passes_through():
    o = Outline(title="t", ending_type=EndingType.HE)
    assert o.ending_type is EndingType.HE


# --------------------------------------------------------------------------- #
# REQUIRED 4: custom ending stored separately from the enum
# --------------------------------------------------------------------------- #


def test_custom_ending_stored_separately():
    o = Outline(
        title="t",
        ending_type="custom",
        custom_ending="they part ways but write letters",
    )
    # Enum is exactly CUSTOM; custom prose is NEVER merged into the enum value.
    assert o.ending_type is EndingType.CUSTOM
    assert o.ending_type.value == "custom"
    assert o.custom_ending == "they part ways but write letters"


def test_custom_ending_may_be_blank():
    # MVP: blank fields allowed; no non-empty requirement on custom_ending.
    o = Outline(title="t", ending_type="custom")
    assert o.ending_type is EndingType.CUSTOM
    assert o.custom_ending == ""


def test_outline_warning_fields_default_to_blank():
    o = Outline(title="t")
    assert o.warning_setting == ""
    assert o.warning_cp_structure == ""
    assert o.warning_elements == ""


def test_outline_ending_type_invalid_raises():
    for bad in ("HEHE", "nope"):
        with pytest.raises(ValueError) as exc:
            Outline(title="t", ending_type=bad)
        msg = str(exc.value)
        assert "ending_type" in msg
        for valid in ("HE", "BE", "OE", "custom"):
            assert valid in msg


def test_outline_ending_type_is_case_sensitive():
    # 'he' must NOT match HE — str Enum lookup is by exact value.
    with pytest.raises(ValueError) as exc:
        Outline(title="t", ending_type="he")
    assert "ending_type" in str(exc.value)


# --------------------------------------------------------------------------- #
# REQUIRED 5: relation type limited to allowed enum
# --------------------------------------------------------------------------- #


def test_relation_type_str_coerced_keyword_value():
    r = Relation(relation_type="IF", target_path="vault/foo.md")
    assert r.relation_type is RelationType.IF
    assert r.relation_type.value == "IF"
    assert r.target_path == "vault/foo.md"
    assert r.note == ""


@pytest.mark.parametrize(
    "value",
    ["前作", "续作", "IF", "外传", "同系列"],
)
def test_relation_type_all_members_round_trip_from_string(value):
    r = Relation(relation_type=value, target_path="vault/x.md")
    assert r.relation_type is RelationType(value)
    assert r.relation_type.value == value


def test_relation_type_invalid_raises():
    with pytest.raises(ValueError) as exc:
        Relation(relation_type="cousin", target_path="vault/x.md")
    assert "relation_type" in str(exc.value)


# --------------------------------------------------------------------------- #
# Required positional fields enforced by the dataclass (TypeError, not ValueError)
# --------------------------------------------------------------------------- #


def test_required_fields_raise_type_error_when_missing():
    with pytest.raises(TypeError):
        Cache()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Outline()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Relation()  # type: ignore[call-arg]


# --------------------------------------------------------------------------- #
# Mutable-default isolation: instances must not share list defaults
# --------------------------------------------------------------------------- #


def test_outline_mutable_defaults_are_independent():
    a = Outline(title="a")
    b = Outline(title="b")
    assert a.characters is not b.characters
    assert a.relations is not b.relations
    a.characters.append("Alice")
    a.relations.append(Relation(relation_type="IF", target_path="x.md"))
    assert b.characters == []
    assert b.relations == []


# --------------------------------------------------------------------------- #
# Relations: hold Relation objects; Outline does NOT coerce dicts (Step 4's job)
# --------------------------------------------------------------------------- #


def test_outline_relations_hold_relation_objects():
    rel = Relation(relation_type="续作", target_path="vault/next.md")
    o = Outline(title="t", relations=[rel])
    assert o.relations == [rel]
    assert isinstance(o.relations[0], Relation)


def test_outline_does_not_coerce_dicts_into_relation():
    # Step 2 stores whatever it is handed; dict->Relation coercion is Step 4.
    raw_dict = {"relation_type": "续作", "target_path": "vault/next.md"}
    o = Outline(title="t", relations=[raw_dict])
    assert o.relations[0] is raw_dict
    assert not isinstance(o.relations[0], Relation)


# --------------------------------------------------------------------------- #
# datetime defaults: fresh when omitted, preserved verbatim when supplied
# --------------------------------------------------------------------------- #


def test_cache_datetime_defaults_are_fresh_instances():
    c = Cache(title="t", raw="r")
    assert isinstance(c.created, datetime)
    assert isinstance(c.updated, datetime)


def test_outline_datetime_defaults_are_fresh_instances():
    o = Outline(title="t")
    assert isinstance(o.created, datetime)
    assert isinstance(o.updated, datetime)


def test_caller_supplied_datetime_is_preserved_verbatim():
    stored_created = datetime(2020, 1, 2, 3, 4, 5)
    stored_updated = datetime(2021, 6, 7, 8, 9, 10)
    c = Cache(
        title="t",
        raw="r",
        created=stored_created,
        updated=stored_updated,
    )
    assert c.created == stored_created
    assert c.updated == stored_updated
    o = Outline(title="t", created=stored_created, updated=stored_updated)
    assert o.created == stored_created
    assert o.updated == stored_updated


# --------------------------------------------------------------------------- #
# Product invariant 1: raw / raw_inspiration stored verbatim, untouched
# --------------------------------------------------------------------------- #


def test_raw_stored_verbatim_and_untouched():
    spark = "  what if THEY met again??? \n\n— with EXTRA whitespace —  "
    c = Cache(title="t", raw=spark)
    assert c.raw == spark  # no strip, no summarize, no rewrite


def test_raw_inspiration_stored_verbatim():
    spark = "midnight train, two strangers, one umbrella"
    o = Outline(title="t", raw_inspiration=spark)
    assert o.raw_inspiration == spark


# --------------------------------------------------------------------------- #
# MVP: empty-string title/raw currently accepted (documents intended behavior)
# --------------------------------------------------------------------------- #


def test_empty_string_title_and_raw_are_accepted():
    # No non-empty validation by design for MVP. This test documents that a
    # future required-field check would be a conscious, breaking change.
    c = Cache(title="", raw="")
    assert c.title == ""
    assert c.raw == ""
    o = Outline(title="")
    assert o.title == ""


# --------------------------------------------------------------------------- #
# Headless import: only stdlib pulled in (no flet / pydantic / attrs / yaml)
# --------------------------------------------------------------------------- #


def test_module_imports_only_stdlib():
    # Import models in a FRESH interpreter so we inspect *its* import
    # closure, not the global sys.modules of the running test process
    # (which a sibling test or conftest could already have polluted with
    # flet). PYTHONPATH points at src/ so this works with or without an
    # editable install.
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.models, sys\n"
        "forbidden = {'flet', 'pydantic', 'attr', 'attrs', 'yaml'}\n"
        "leaked = sorted(forbidden & set(sys.modules))\n"
        "assert not leaked, 'models must not import: ' + repr(leaked)\n"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(src), os.environ.get("PYTHONPATH", "")]
    )}
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
