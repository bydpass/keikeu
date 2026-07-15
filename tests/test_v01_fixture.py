"""Frozen synthetic v0.1 fixture consumed only by the migration boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keikeu_core.legacy_v01 import LegacyCacheStatus, read_v01_cache


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "v01-vault"


def test_fixture_has_the_complete_v01_vault_layout():
    assert (FIXTURE_VAULT / "cache").is_dir()
    assert (FIXTURE_VAULT / "outlines").is_dir()
    assert (FIXTURE_VAULT / ".trash" / "outlines").is_dir()
    with (FIXTURE_VAULT / "keikeu_index.json").open(encoding="utf-8") as handle:
        index = json.load(handle)
    assert index["version"] == 1
    assert len(index["caches"]) == 4
    assert len(index["outlines"]) == 1


def test_valid_and_sparse_v01_caches_remain_readable_for_migration_only():
    normal = read_v01_cache(
        FIXTURE_VAULT / "cache" / "2026-07-01-090000-a101-rain-platform.md"
    )
    assert normal.status is LegacyCacheStatus.OUTLINED
    assert normal.linked_outline == "outlines/2026-07-01-091000-b101-rain-platform-outline.md"
    sparse = read_v01_cache(
        FIXTURE_VAULT / "cache" / "2026-07-02-090000-a102-blank-optional.md"
    )
    assert sparse.status is LegacyCacheStatus.RAW
    assert sparse.notes == ""


def test_empty_raw_is_readable_but_reserved_for_preflight_failure():
    cache = read_v01_cache(
        FIXTURE_VAULT / "cache" / "2026-07-03-090000-a103-empty-raw.md"
    )
    assert cache.status is LegacyCacheStatus.ARCHIVED
    assert cache.raw == ""


def test_corrupt_v01_cache_is_rejected_by_the_migration_reader():
    corrupt = FIXTURE_VAULT / "cache" / "2026-07-04-090000-a104-corrupt-status.md"
    with pytest.raises(ValueError, match="CacheStatus"):
        read_v01_cache(corrupt)


def test_outline_fixture_is_retained_as_unread_backup_input_only():
    outline = FIXTURE_VAULT / "outlines" / "2026-07-01-091000-b101-rain-platform-outline.md"
    assert b"type: outline" in outline.read_bytes()
