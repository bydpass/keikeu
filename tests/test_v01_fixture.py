"""Frozen synthetic v0.1 vault fixture used by Road v0.2 migration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keikeu_core.markdown_io import read_cache, read_outline
from keikeu_core.models import CacheStatus, EndingType, RelationType


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "v01-vault"


def test_fixture_has_the_complete_v01_vault_layout():
    assert (FIXTURE_VAULT / "cache").is_dir()
    assert (FIXTURE_VAULT / "outlines").is_dir()
    assert (FIXTURE_VAULT / ".trash" / "outlines").is_dir()

    with (FIXTURE_VAULT / "keikeu_index.json").open(encoding="utf-8") as fh:
        index = json.load(fh)

    assert index["version"] == 1
    assert len(index["caches"]) == 4
    assert len(index["outlines"]) == 1


def test_valid_and_sparse_v01_caches_remain_parseable():
    normal = read_cache(
        FIXTURE_VAULT / "cache" / "2026-07-01-090000-a101-rain-platform.md"
    )
    assert normal.title == "Rain Platform"
    assert normal.status is CacheStatus.OUTLINED
    assert normal.linked_outline == (
        "outlines/2026-07-01-091000-b101-rain-platform-outline.md"
    )
    assert normal.notes == "Keep the train announcement as the last line."

    sparse = read_cache(
        FIXTURE_VAULT / "cache" / "2026-07-02-090000-a102-blank-optional.md"
    )
    assert sparse.status is CacheStatus.RAW
    assert sparse.raw == "A complete sentence is enough to migrate."
    assert sparse.notes == ""
    assert sparse.linked_outline is None


def test_empty_raw_is_valid_v01_but_reserved_for_v02_preflight_failure():
    empty_raw = read_cache(
        FIXTURE_VAULT / "cache" / "2026-07-03-090000-a103-empty-raw.md"
    )
    assert empty_raw.status is CacheStatus.ARCHIVED
    assert empty_raw.raw == ""
    assert empty_raw.notes == "Do not use this note as a replacement Summary."


def test_corrupt_v01_cache_is_rejected_by_the_legacy_reader():
    corrupt = FIXTURE_VAULT / "cache" / "2026-07-04-090000-a104-corrupt-status.md"
    with pytest.raises(ValueError, match="CacheStatus"):
        read_cache(corrupt)


def test_active_v01_outline_is_parseable_and_has_a_legacy_relation():
    outline = read_outline(
        FIXTURE_VAULT
        / "outlines"
        / "2026-07-01-091000-b101-rain-platform-outline.md"
    )
    assert outline.ending_type is EndingType.HE
    assert outline.relations[0].relation_type is RelationType.SEQUEL
    assert outline.relations[0].target_path == (
        "cache/2026-07-01-090000-a101-rain-platform.md"
    )
