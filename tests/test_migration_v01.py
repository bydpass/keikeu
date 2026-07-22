"""Safety tests for the explicit one-shot v0.1 to Paper v3 migration."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
import os
from pathlib import Path
import shutil

import pytest

from keikeu_core.markdown_io import read_paper
from keikeu_core.models import Highlight
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


def test_stage_copy_failure_leaves_the_active_vault_unmodified(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    backup_root = tmp_path / "backups"
    before = _file_bytes(vault)

    def fail_stage_copy(source: Path, destination: Path) -> None:
        raise OSError("injected stage copy failure")

    monkeypatch.setattr(migration_v01, "_copy_full_vault", fail_stage_copy)

    with pytest.raises(OSError, match="stage copy failure"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert not backup_root.exists() or list(backup_root.iterdir()) == []


def test_migration_rejects_a_root_symlink_before_writing(tmp_path):
    real_vault = _copy_fixture(tmp_path, "real-vault")
    _remove_preflight_failures(real_vault)
    vault_link = tmp_path / "vault-link"
    vault_link.symlink_to(real_vault, target_is_directory=True)
    before = _file_bytes(real_vault)

    with pytest.raises(ValueError, match="symlink"):
        migrate_v01_vault(
            vault_link,
            backup_root=tmp_path / "backups",
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(real_vault) == before
    assert not (tmp_path / "backups").exists()


def test_backup_root_must_be_inside_home_and_outside_the_active_vault(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)

    with pytest.raises(ValueError, match="outside the active vault"):
        migrate_v01_vault(
            vault,
            backup_root=vault / "backups",
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert not (vault / "backups").exists()


def test_backup_root_symlink_escape_is_rejected_before_writing(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_link = tmp_path / "backup-link"
    backup_link.symlink_to("/private/tmp", target_is_directory=True)

    with pytest.raises(ValueError, match="outside current user Home"):
        migrate_v01_vault(
            vault,
            backup_root=backup_link,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert backup_link.is_symlink()


def test_existing_symlink_at_backup_target_is_rejected(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    target = backup_root / "vault-v01-backup-20260714-120000"
    target.symlink_to("/private/tmp", target_is_directory=True)

    with pytest.raises(ValueError, match="unsupported existing backup target"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert target.is_symlink()


def test_cross_device_backup_fails_before_switching_source(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_root = tmp_path / "backups"
    real_prepare = migration_v01._prepare_external_root

    def foreign_backup_root(source_vault: Path, root: Path):
        pinned = real_prepare(source_vault, root)
        return replace(
            pinned,
            identity=(pinned.identity[0] + 1, pinned.identity[1]),
        )

    monkeypatch.setattr(
        migration_v01,
        "_prepare_external_root",
        foreign_backup_root,
    )

    with pytest.raises(ValueError, match="must share one filesystem"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert list(backup_root.iterdir()) == []


def test_missing_atomic_exchange_fails_before_backup_or_staging(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_root = tmp_path / "backups"

    def unavailable() -> None:
        raise RuntimeError("atomic filesystem exchange is unavailable")

    monkeypatch.setattr(migration_v01, "require_atomic_exchange", unavailable)

    with pytest.raises(RuntimeError, match="atomic filesystem exchange is unavailable"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert not backup_root.exists()
    assert not list(vault.parent.glob(f".{vault.name}.v01-stage-*"))


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
    assert result.backup_path.is_relative_to(Path.home())
    assert not result.backup_path.is_relative_to(vault)
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
    assert first.highlights == [
        Highlight(content="Keep the train announcement as the last line.")
    ]
    assert first.tags == []
    assert first.legacy_title == "Rain Platform"
    assert second.initial_summary == "A complete sentence is enough to migrate."
    assert second.highlights == []

    with (vault / "keikeu_index.json").open(encoding="utf-8") as fh:
        index = json.load(fh)
    assert index["version"] == 3
    assert index["papers"][0]["display_name"] is None
    assert index["papers"][0]["folder"] is None
    assert index["papers"][0]["highlight_names"] == []
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
    assert not list(vault.parent.glob(f".{vault.name}.v01-rollback-*"))


def test_migration_accepts_whitespace_only_legacy_notes(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    source = vault / "cache" / "2026-07-02-090000-a102-blank-optional.md"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "## 临时备注\n",
            "## 临时备注\n\n   \n",
        ),
        encoding="utf-8",
    )

    result = migrate_v01_vault(
        vault,
        backup_root=tmp_path / "backups",
        now=datetime(2026, 7, 14, 12, 0),
    )

    papers = sorted((vault / "cache").glob("*.md"))
    assert result.converted_count == 2
    assert read_paper(papers[1]).highlights == []


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
        now=datetime(2026, 7, 14, 12, 0),
    )

    assert _file_bytes(result.backup_path) == before
    assert result.backup_path.parent == vault.parent / "keikeu-backups"
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


@pytest.mark.parametrize("mutation_point", ["after_stage_copy", "before_backup"])
def test_source_change_before_switch_is_rejected_and_kept_active(
    tmp_path,
    mutation_point,
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    source = vault / "cache" / "2026-07-01-090000-a101-rain-platform.md"
    changed_bytes = source.read_bytes() + b"\n# concurrent author edit\n"
    backup_root = tmp_path / "backups"

    def mutate_source(point: str) -> None:
        if point == mutation_point:
            source.write_bytes(changed_bytes)

    with pytest.raises(ValueError, match="source changed"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
            failure_hook=mutate_source,
        )

    assert source.read_bytes() == changed_bytes
    assert is_v01_vault(vault) is True
    assert not (vault / "keikeu_migration_report.json").exists()
    assert list(backup_root.iterdir()) == []
    assert not list(vault.parent.glob(f".{vault.name}.v01-stage-*"))


def test_source_change_between_preflight_and_raw_copy_is_rejected(
    tmp_path,
    monkeypatch,
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    source = vault / "cache" / "2026-07-01-090000-a101-rain-platform.md"
    changed_bytes = source.read_bytes() + b"\n# edit before raw copy\n"
    backup_root = tmp_path / "backups"
    real_copy = migration_v01._copy_full_vault

    def mutate_then_copy(source_root: Path, destination: Path) -> None:
        source.write_bytes(changed_bytes)
        real_copy(source_root, destination)

    monkeypatch.setattr(migration_v01, "_copy_full_vault", mutate_then_copy)

    with pytest.raises(ValueError, match="source changed before staging completed"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert source.read_bytes() == changed_bytes
    assert is_v01_vault(vault) is True
    assert not (vault / "keikeu_migration_report.json").exists()
    assert list(backup_root.iterdir()) == []
    assert not list(vault.parent.glob(f".{vault.name}.v01-stage-*"))


def test_atomic_activation_failure_leaves_original_active(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_root = tmp_path / "backups"

    def fail_exchange(
        first_parent_fd: int,
        first_name: str,
        second_parent_fd: int,
        second_name: str,
    ) -> None:
        raise OSError("injected activation exchange failure")

    monkeypatch.setattr(
        migration_v01,
        "atomic_exchange_at_no_follow",
        fail_exchange,
    )

    with pytest.raises(OSError, match="activation exchange failure"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert list(backup_root.iterdir()) == []
    assert not list(vault.parent.glob(f".{vault.name}.v01-stage-*"))


def test_backup_move_failure_atomically_restores_original(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_root = tmp_path / "backups"
    real_replace = migration_v01.os.replace

    def fail_backup_move(source, destination, *args, **kwargs):
        if kwargs.get("dst_dir_fd") is not None and str(destination).startswith(
            f"{vault.name}-v01-backup-"
        ):
            raise OSError("injected backup move failure")
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(migration_v01.os, "replace", fail_backup_move)

    with pytest.raises(OSError, match="backup move failure"):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert _file_bytes(vault) == before
    assert list(backup_root.iterdir()) == []
    assert not list(vault.parent.glob(f".{vault.name}.v01-stage-*"))


def test_failed_backup_move_and_failed_rollback_preserve_both_trees(
    tmp_path,
    monkeypatch,
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_root = tmp_path / "backups"
    real_exchange = migration_v01.atomic_exchange_at_no_follow
    real_replace = migration_v01.os.replace
    exchange_count = 0

    def fail_rollback_exchange(
        first_parent_fd: int,
        first_name: str,
        second_parent_fd: int,
        second_name: str,
    ) -> None:
        nonlocal exchange_count
        exchange_count += 1
        if exchange_count == 2:
            raise OSError("injected rollback exchange failure")
        real_exchange(
            first_parent_fd,
            first_name,
            second_parent_fd,
            second_name,
        )

    def fail_backup_move(source, destination, *args, **kwargs):
        if kwargs.get("dst_dir_fd") is not None and str(destination).startswith(
            f"{vault.name}-v01-backup-"
        ):
            raise OSError("injected backup move failure")
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(
        migration_v01,
        "atomic_exchange_at_no_follow",
        fail_rollback_exchange,
    )
    monkeypatch.setattr(migration_v01.os, "replace", fail_backup_move)

    with pytest.raises(migration_v01._MigrationRecoveryError) as exc:
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
        )

    assert exchange_count == 2
    assert (vault / "keikeu_migration_report.json").is_file()
    assert is_v01_vault(vault) is False
    assert _file_bytes(exc.value.original_path) == before
    assert exc.value.original_path.parent.exists()
    assert list(backup_root.iterdir()) == []


@pytest.mark.parametrize(
    "failure_point",
    [
        "before_switch",
        "before_backup",
        "after_original_renamed",
        "after_backup",
        "after_switch",
    ],
)
def test_staging_failures_leave_the_active_vault_unmodified(tmp_path, failure_point):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    backup_root = tmp_path / "backups"

    def inject(point: str) -> None:
        if point == failure_point:
            raise OSError(f"injected failure at {point}")

    with pytest.raises(OSError, match=failure_point):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
            failure_hook=inject,
        )

    assert _file_bytes(vault) == before
    assert not (vault / "keikeu_migration_report.json").exists()
    assert not backup_root.exists() or list(backup_root.iterdir()) == []


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


def test_recursive_cleanup_only_touches_generated_staging(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    removed: list[tuple[Path, int | None]] = []
    real_rmtree = migration_v01.shutil.rmtree

    def record_rmtree(path, *args, **kwargs):
        removed.append((Path(path), kwargs.get("dir_fd")))
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(migration_v01.shutil, "rmtree", record_rmtree)

    result = migrate_v01_vault(
        vault,
        backup_root=tmp_path / "backups",
        now=datetime(2026, 7, 14, 12, 0),
    )

    assert removed
    assert all(directory_fd is not None for _, directory_fd in removed)
    assert all(not path.is_absolute() and len(path.parts) == 1 for path, _ in removed)
    assert all(path not in {vault, result.backup_path} for path, _ in removed)
    assert result.backup_path.exists()
    assert _file_bytes(result.backup_path)


def test_workspace_creation_rejects_replaced_source_parent_without_external_write(
    tmp_path,
):
    source_parent = tmp_path / "source-parent"
    source_parent.mkdir()
    vault = _copy_fixture(source_parent)
    _remove_preflight_failures(vault)
    source_before = _file_bytes(vault)
    backup_root = tmp_path / "backups"
    sentinel = tmp_path / "workspace-external-sentinel"
    sentinel.mkdir()
    (sentinel / "keep.txt").write_bytes(b"workspace sentinel\n")
    sentinel_before = _file_bytes(sentinel)
    preserved_parent = tmp_path / "source-parent-preserved"

    def replace_source_parent(point: str) -> None:
        if point != "before_workspace":
            return
        os.replace(source_parent, preserved_parent)
        source_parent.symlink_to(sentinel, target_is_directory=True)

    with pytest.raises(
        migration_v01._PinnedPathError,
        match="generated directory was replaced",
    ):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
            failure_hook=replace_source_parent,
        )

    assert source_parent.is_symlink()
    assert _file_bytes(sentinel) == sentinel_before
    assert not list(sentinel.glob(f".{vault.name}.v01-stage-*"))
    assert _file_bytes(preserved_parent / vault.name) == source_before
    assert list(backup_root.iterdir()) == []


@pytest.mark.parametrize("replacement_level", ["root", "ancestor"])
def test_final_backup_rejects_replaced_root_without_external_write(
    tmp_path,
    replacement_level,
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    source_before = _file_bytes(vault)
    backup_parent = tmp_path / "backup-parent"
    backup_parent.mkdir()
    backup_root = backup_parent / "backups"
    sentinel_parent = tmp_path / "backup-external-sentinel"
    sentinel_root = sentinel_parent / "backups"
    sentinel_root.mkdir(parents=True)
    (sentinel_root / "keep.txt").write_bytes(b"backup sentinel\n")
    sentinel_before = _file_bytes(sentinel_parent)

    def replace_backup_boundary(point: str) -> None:
        if point != "after_switch":
            return
        if replacement_level == "root":
            preserved = tmp_path / "backup-root-preserved"
            os.replace(backup_root, preserved)
            backup_root.symlink_to(sentinel_root, target_is_directory=True)
        else:
            preserved = tmp_path / "backup-parent-preserved"
            os.replace(backup_parent, preserved)
            backup_parent.symlink_to(sentinel_parent, target_is_directory=True)

    with pytest.raises(
        migration_v01._PinnedPathError,
        match="generated directory was replaced",
    ):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
            failure_hook=replace_backup_boundary,
        )

    replaced_path = backup_root if replacement_level == "root" else backup_parent
    preserved_root = (
        tmp_path / "backup-root-preserved"
        if replacement_level == "root"
        else tmp_path / "backup-parent-preserved" / "backups"
    )
    assert replaced_path.is_symlink()
    assert _file_bytes(sentinel_parent) == sentinel_before
    assert list(preserved_root.iterdir()) == []
    assert _file_bytes(vault) == source_before
    assert is_v01_vault(vault) is True
    assert not list(vault.parent.glob(f".{vault.name}.v01-stage-*"))


@pytest.mark.parametrize("replacement_level", ["stage", "workspace"])
def test_replaced_generated_root_never_touches_external_sentinel(
    tmp_path,
    replacement_level,
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    source_before = _file_bytes(vault)
    backup_root = tmp_path / "backups"
    sentinel = tmp_path / "external-sentinel"
    (sentinel / "cache").mkdir(parents=True)
    (sentinel / ".trash" / "cache").mkdir(parents=True)
    (sentinel / "outlines").mkdir()
    (sentinel / "cache" / "keep.md").write_bytes(b"external cache\n")
    (sentinel / ".trash" / "cache" / "keep.md").write_bytes(
        b"external trash cache\n"
    )
    (sentinel / "outlines" / "keep.md").write_bytes(b"external outline\n")
    (sentinel / "keikeu_index.json").write_bytes(b"external index\n")
    (sentinel / "keikeu_migration_report.json").write_bytes(b"external report\n")
    sentinel_before = _file_bytes(sentinel)
    replacement_path: Path | None = None

    def replace_generated_root(point: str) -> None:
        nonlocal replacement_path
        if point != "after_stage_copy":
            return
        workspace = next(vault.parent.glob(f".{vault.name}.v01-stage-*"))
        if replacement_level == "stage":
            replacement_path = workspace / vault.name
            preserved = workspace / "owned-stage-preserved"
        else:
            replacement_path = workspace
            preserved = workspace.with_name(f"{workspace.name}-preserved")
        os.replace(replacement_path, preserved)
        replacement_path.symlink_to(sentinel, target_is_directory=True)

    with pytest.raises(
        migration_v01._StageOwnershipError,
        match="generated directory was replaced",
    ):
        migrate_v01_vault(
            vault,
            backup_root=backup_root,
            now=datetime(2026, 7, 14, 12, 0),
            failure_hook=replace_generated_root,
        )

    assert replacement_path is not None
    assert replacement_path.is_symlink()
    assert _file_bytes(sentinel) == sentinel_before
    assert _file_bytes(vault) == source_before
    assert list(backup_root.iterdir()) == []


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
