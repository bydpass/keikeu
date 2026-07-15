"""Safety tests for the explicit one-shot v0.1 to Paper v2 migration."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import shutil

import pytest

from keikeu_core.markdown_io import read_paper
from keikeu_core import migration_v01
from keikeu_core.migration_v01 import (
    MigrationPreflightError,
    inspect_v01_vault,
    is_v01_vault,
    migrate_v01_vault,
)


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "v01-vault"


def _copy_fixture(tmp_path: Path, name: str = "vault") -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURE_VAULT, target)
    return target


def _remove_preflight_failures(vault: Path) -> None:
    (vault / "cache" / "2026-07-03-090000-a103-empty-raw.md").unlink()
    (vault / "cache" / "2026-07-04-090000-a104-corrupt-status.md").unlink()


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_v01_detection_is_read_only_and_preflight_lists_all_blockers(tmp_path):
    vault = _copy_fixture(tmp_path)
    before = _file_bytes(vault)

    assert is_v01_vault(vault) is True
    preflight = inspect_v01_vault(vault)

    assert preflight.ready is False
    assert preflight.cache_count == 4
    assert preflight.outline_count == 1
    assert preflight.trash_outline_count == 1
    assert len(preflight.issues) == 2
    assert any("empty raw inspiration" in issue.message for issue in preflight.issues)
    assert any("CacheStatus" in issue.message for issue in preflight.issues)
    assert _file_bytes(vault) == before


def test_migration_preflight_failure_never_creates_a_backup_or_changes_vault(tmp_path):
    vault = _copy_fixture(tmp_path)
    backup_root = tmp_path / "backups"
    before = _file_bytes(vault)

    with pytest.raises(MigrationPreflightError) as exc:
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert len(exc.value.issues) == 2
    assert not backup_root.exists()
    assert _file_bytes(vault) == before


def test_one_bad_cache_blocks_the_entire_migration_without_switching(tmp_path):
    vault = _copy_fixture(tmp_path)
    (vault / "cache" / "2026-07-03-090000-a103-empty-raw.md").unlink()
    before = _file_bytes(vault)

    preflight = inspect_v01_vault(vault)
    assert len(preflight.issues) == 1
    with pytest.raises(MigrationPreflightError):
        migrate_v01_vault(
            vault,
            backup_root=tmp_path / "backups",
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before


def test_backup_copy_failure_leaves_the_active_vault_unmodified(
    tmp_path, monkeypatch
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    backup_root = tmp_path / "backups"
    before = _file_bytes(vault)
    real_copy = migration_v01._copy_full_vault

    def fail_only_backup(source: Path, destination: Path) -> None:
        if destination.parent == backup_root:
            raise OSError("injected backup copy failure")
        real_copy(source, destination)

    monkeypatch.setattr(migration_v01, "_copy_full_vault", fail_only_backup)

    with pytest.raises(OSError, match="backup copy failure"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert not backup_root.exists() or list(backup_root.iterdir()) == []


def test_successful_migration_backs_up_every_byte_and_replaces_legacy_assets(
    tmp_path,
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)

    result = migrate_v01_vault(
        vault,
        backup_root=tmp_path / "backups",
        now=datetime(2026, 7, 14, 12, 0),
    )

    assert _file_bytes(result.backup_path) == before
    assert result.converted_count == 2
    assert not (vault / "outlines").exists()
    assert not (vault / ".trash" / "outlines").exists()
    assert (vault / "keikeu_migration_report.json") == result.report_path

    papers = sorted((vault / "cache").glob("*.md"))
    assert [path.name for path in papers] == [
        "K-20260714-001.md",
        "K-20260714-002.md",
    ]
    first, second = (read_paper(path) for path in papers)
    assert first.code == "K-20260714-001"
    assert first.initial_summary == "Two strangers share an umbrella on an empty platform."
    assert first.summary == first.initial_summary
    assert first.highlights == ["Keep the train announcement as the last line."]
    assert first.tags == []
    assert first.legacy_title == "Rain Platform"
    assert second.initial_summary == "A complete sentence is enough to migrate."
    assert second.highlights == []

    with (vault / "keikeu_index.json").open(encoding="utf-8") as fh:
        index = json.load(fh)
    assert index["version"] == 2
    assert [entry["code"] for entry in index["papers"]] == [
        "K-20260714-001",
        "K-20260714-002",
    ]
    assert index["errors"] == []

    with result.report_path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    assert report["converted_count"] == 2
    assert report["removed_active_outlines"] == [
        "outlines/2026-07-01-091000-b101-rain-platform-outline.md"
    ]
    assert report["removed_trash_outlines"] == [
        ".trash/outlines/2026-06-30-080000-b100-old-outline.md"
    ]
    assert report["papers"][0]["legacy_status"] == "outlined"
    assert report["papers"][0]["linked_outline"] == (
        "outlines/2026-07-01-091000-b101-rain-platform-outline.md"
    )


def test_migration_ignores_macos_metadata_but_preserves_it_in_backup(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    (vault / "cache" / ".DS_Store").write_bytes(b"cache-metadata")
    (vault / "outlines" / ".DS_Store").write_bytes(b"outline-metadata")
    before = _file_bytes(vault)

    preflight = inspect_v01_vault(vault)

    assert preflight.ready is True
    assert preflight.cache_count == 2
    assert preflight.outline_count == 1

    result = migrate_v01_vault(
        vault,
        backup_root=tmp_path / "backups",
        now=datetime(2026, 7, 14, 12, 0),
    )

    assert _file_bytes(result.backup_path) == before
    assert not (vault / "cache" / ".DS_Store").exists()
    assert not (vault / "outlines").exists()


def test_migration_also_converts_trashed_caches_to_avoid_mixed_schema(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    trash_cache = vault / ".trash" / "cache"
    trash_cache.mkdir(parents=True)
    shutil.copyfile(
        vault / "cache" / "2026-07-01-090000-a101-rain-platform.md",
        trash_cache / "2026-06-29-090000-a100-trashed-cache.md",
    )

    result = migrate_v01_vault(
        vault,
        backup_root=tmp_path / "backups",
        now=datetime(2026, 7, 14, 12, 0),
    )

    assert result.converted_count == 3
    trashed_papers = sorted((vault / ".trash" / "cache").glob("*.md"))
    assert [path.name for path in trashed_papers] == ["K-20260714-003.md"]
    assert read_paper(trashed_papers[0]).legacy_title == "Rain Platform"


@pytest.mark.parametrize("failure_point", ["after_backup", "before_switch"])
def test_staging_failures_leave_the_active_vault_unmodified(tmp_path, failure_point):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)

    def inject(point: str) -> None:
        if point == failure_point:
            raise OSError(f"injected failure at {point}")

    with pytest.raises(OSError, match=failure_point):
        migrate_v01_vault(
            vault,
            backup_root=tmp_path / "backups",
            now=datetime(2026, 7, 14, 12, 0),
            failure_hook=inject,
        )

    assert _file_bytes(vault) == before


def test_switch_failure_restores_the_original_vault_without_mixed_schema(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)

    def inject(point: str) -> None:
        if point == "after_original_renamed":
            raise OSError("injected switch failure")

    with pytest.raises(OSError, match="switch failure"):
        migrate_v01_vault(
            vault,
            backup_root=tmp_path / "backups",
            now=datetime(2026, 7, 14, 12, 0),
            failure_hook=inject,
        )

    assert _file_bytes(vault) == before
    assert (vault / "outlines").is_dir()
    assert all("type: cache" in data.decode("utf-8") for data in before.values() if b"type: cache" in data)


def test_v2_vault_is_not_mistaken_for_a_legacy_migration_source(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    migrate_v01_vault(
        vault,
        backup_root=tmp_path / "backups",
        now=datetime(2026, 7, 14, 12, 0),
    )

    assert is_v01_vault(vault) is False
    with pytest.raises(MigrationPreflightError, match="not a v0.1 vault"):
        migrate_v01_vault(
            vault,
            backup_root=tmp_path / "other-backups",
            now=datetime(2026, 7, 14, 12, 0),
        )
