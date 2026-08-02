"""Paper v2/v3 to v4 preflight, loss-audit, backup, and resume contracts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core import migration_v4 as migration_mod
from keikeu_core.markdown_io import (
    parse_paper_v4_bytes,
    render_paper_bytes,
    render_paper_v4_bytes,
)
from keikeu_core.migration_v4 import (
    MigrationCommitUnknown,
    classify_migration_stage,
    inspect_paper_v4_migration,
    migrate_papers_to_v4,
)
from keikeu_core.models import CardPageV4, Highlight, Paper, PaperV4
from keikeu_core.vault import init_vault, snapshot_regular_tree_no_follow


NOW = datetime(2026, 8, 2, 12, 0)
V2_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "v03-vault"
    / "mixed-vault"
    / "cache"
    / "K-20260720-001.md"
)


def fresh_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    init_vault(vault)
    return vault


def legacy_paper(code: str, **overrides) -> Paper:
    values = {
        "code": code,
        "initial_summary": "将被备份保留但从 v4 active schema 丢弃",
        "summary": "当前总结",
        "highlights": [Highlight(content="高光正文", display_name="高光标题")],
        "tags": ["夜车", "重逢,旧友"],
        "created": NOW,
        "updated": NOW,
        "legacy_title": "旧标题",
        "extra_frontmatter": {"source": "manual"},
    }
    values.update(overrides)
    return Paper(**values)


def store_legacy(vault: Path, relative: str, paper: Paper) -> Path:
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_paper_bytes(paper))
    return path


def store_v4(vault: Path, relative: str, paper: PaperV4) -> Path:
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_paper_v4_bytes(paper))
    return path


def test_preflight_maps_v2_v3_without_writing_and_preserves_mapped_fields(tmp_path):
    vault = fresh_vault(tmp_path)
    v2 = vault / "cache" / V2_FIXTURE.name
    v2.write_bytes(V2_FIXTURE.read_bytes())
    v3 = store_legacy(
        vault,
        "cache/文件夹/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    before = snapshot_regular_tree_no_follow(vault)

    preflight = inspect_paper_v4_migration(vault)

    assert preflight.state == "legacy"
    assert preflight.ready is True
    assert [item.source_schema for item in preflight.candidates] == [2, 3]
    assert snapshot_regular_tree_no_follow(vault) == before
    mapped_v2 = parse_paper_v4_bytes(preflight.candidates[0].target_bytes)
    assert [page.type for page in mapped_v2.pages] == ["summary", "snapshot", "snapshot"]
    assert [page.name for page in mapped_v2.pages] == [None, None, None]
    mapped_v3 = parse_paper_v4_bytes(preflight.candidates[1].target_bytes)
    assert mapped_v3.pages == [
        CardPageV4(content="当前总结", type="summary"),
        CardPageV4(name="高光标题", content="高光正文", type="snapshot"),
    ]
    assert mapped_v3.tags == ["夜车", "重逢,旧友"]
    assert mapped_v3.legacy_title == "旧标题"
    assert mapped_v3.extra_frontmatter == {"source": "manual"}
    assert v3.read_bytes() == preflight.candidates[1].source_bytes


def test_schema_scan_accepts_valid_v4_crlf_and_reports_symlink_without_following_it(tmp_path):
    vault = fresh_vault(tmp_path)
    paper = PaperV4(
        code="K-20260802-001",
        pages=[CardPageV4(content="CRLF")],
        created=NOW,
        updated=NOW,
    )
    path = store_v4(vault, "cache/K-20260802-001.md", paper)
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert inspect_paper_v4_migration(vault).state == "pure_v4"

    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside")
    link = vault / "cache" / "linked.md"
    link.symlink_to(outside)
    preflight = inspect_paper_v4_migration(vault)
    assert preflight.state == "repair_required"
    assert any("symlink" in issue.reason for issue in preflight.issues)
    assert outside.read_bytes() == b"outside"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda data: data.replace(
                b"code: K-20260802-001\n",
                b"code: K-20260802-001\ncode: K-20260802-001\n",
                1,
            ),
            "repeats key",
        ),
        (
            lambda data: data.replace(
                b"# K-20260802-001\n\n##",
                b"# K-20260802-001\n\nstray\n\n##",
                1,
            ),
            "stray text",
        ),
        (
            lambda data: data.replace(
                b"## Summary\n\n",
                b"## Summary\n\ncurrent\n\n## Summary\n\n",
                1,
            ),
            "exactly once",
        ),
        (
            lambda data: data.replace(b"1. \xe5\x90\x8d\xe7\xa7\xb0\xef\xbc\x9a", b"2. \xe5\x90\x8d\xe7\xa7\xb0\xef\xbc\x9a", 1),
            "descriptor",
        ),
        (
            lambda data: data.replace(b"- \xe5\xa4\x9c\xe8\xbd\xa6\n", b"continuation\n", 1),
            "multiline or malformed",
        ),
    ],
)
def test_raw_loss_audit_blocks_ambiguous_or_unassigned_bytes(tmp_path, mutate, message):
    vault = fresh_vault(tmp_path)
    path = store_legacy(
        vault,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    path.write_bytes(mutate(path.read_bytes()))
    before = path.read_bytes()

    preflight = inspect_paper_v4_migration(vault)

    assert preflight.ready is False
    assert preflight.state == "repair_required"
    assert message in preflight.issues[0].reason
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (b"-  \xe5\xa4\x9c\xe8\xbd\xa6 \n", "outer whitespace"),
        (b"- \n", "empty"),
        (b"- \xe5\xa4\x9c\xe8\xbd\xa6\n- \xe5\xa4\x9c\xe8\xbd\xa6\n", "duplicates"),
        (b"- \xe5\xa4\x9c\xe8\xbd\xa6\ncontinued\n", "multiline"),
    ],
)
def test_preflight_blocks_legacy_tag_normalization_instead_of_applying_it(
    tmp_path,
    replacement,
    message,
):
    vault = fresh_vault(tmp_path)
    path = store_legacy(
        vault,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001", tags=["夜车"]),
    )
    path.write_bytes(path.read_bytes().replace(b"- \xe5\xa4\x9c\xe8\xbd\xa6\n", replacement, 1))

    preflight = inspect_paper_v4_migration(vault)

    assert preflight.ready is False
    assert message in preflight.issues[0].reason


def test_migration_backs_up_entire_mixed_vault_then_converges_and_builds_index(tmp_path):
    vault = fresh_vault(tmp_path)
    active = store_legacy(
        vault,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    trashed = store_legacy(
        vault,
        ".trash/cache/旧页/K-20260802-002.md",
        legacy_paper("K-20260802-002", highlights=[]),
    )
    store_v4(
        vault,
        "cache/K-20260802-003.md",
        PaperV4(
            code="K-20260802-003",
            pages=[CardPageV4(content="已经是 v4")],
            created=NOW,
            updated=NOW,
        ),
    )
    preflight = inspect_paper_v4_migration(vault)
    active_before = active.read_bytes()
    trash_before = trashed.read_bytes()

    result = migrate_papers_to_v4(
        vault,
        preflight,
        backup_root=tmp_path / "backups",
        now=NOW,
    )

    completed = inspect_paper_v4_migration(vault)
    assert completed.state == "pure_v4"
    assert completed.complete is True
    assert result.converted_count == 2
    assert result.warnings == ()
    assert (result.backup_path / active.relative_to(vault)).read_bytes() == active_before
    assert (result.backup_path / trashed.relative_to(vault)).read_bytes() == trash_before
    assert parse_paper_v4_bytes(active.read_bytes()).pages[0].content == "当前总结"
    assert json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8"))["version"] == 4
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["backup_verified"] is True
    assert report["discarded_initial_summary_count"] == 2
    assert "content" not in report and "length" not in report


def test_failed_preflight_creates_no_backup_and_changes_no_source(tmp_path):
    vault = fresh_vault(tmp_path)
    path = store_legacy(
        vault,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    path.write_bytes(
        path.read_bytes().replace(
            "## Summary\n\n当前总结".encode(),
            b"## Summary\n\n   ",
            1,
        )
    )
    preflight = inspect_paper_v4_migration(vault)
    before = snapshot_regular_tree_no_follow(vault)

    with pytest.raises(ValueError, match="not ready"):
        migrate_papers_to_v4(
            vault,
            preflight,
            backup_root=tmp_path / "backups",
            now=NOW,
        )

    assert snapshot_regular_tree_no_follow(vault) == before
    assert not (tmp_path / "backups").exists()


def test_interruption_leaves_complete_files_and_fresh_preflight_resumes_remaining(tmp_path):
    vault = fresh_vault(tmp_path)
    first = store_legacy(
        vault,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    second = store_legacy(
        vault,
        "cache/K-20260802-002.md",
        legacy_paper("K-20260802-002"),
    )
    preflight = inspect_paper_v4_migration(vault)

    def interrupt(point: str) -> None:
        if point == "after_replace:1":
            raise RuntimeError("synthetic interruption")

    with pytest.raises(MigrationCommitUnknown) as unknown:
        migrate_papers_to_v4(
            vault,
            preflight,
            backup_root=tmp_path / "backups-a",
            now=NOW,
            failure_hook=interrupt,
        )
    assert unknown.value.converted_count == 1
    assert parse_paper_v4_bytes(first.read_bytes()).code == "K-20260802-001"
    assert b"schema_version: 3" in second.read_bytes()

    resumed = inspect_paper_v4_migration(vault)
    assert resumed.state == "mixed"
    assert [item.path for item in resumed.candidates] == [Path("cache/K-20260802-002.md")]
    result = migrate_papers_to_v4(
        vault,
        resumed,
        backup_root=tmp_path / "backups-b",
        now=datetime(2026, 8, 2, 12, 1),
    )
    assert result.converted_count == 1
    assert inspect_paper_v4_migration(vault).state == "pure_v4"


def test_stale_preflight_is_zero_write_and_creates_no_backup(tmp_path):
    vault = fresh_vault(tmp_path)
    path = store_legacy(
        vault,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    preflight = inspect_paper_v4_migration(vault)
    path.write_bytes(
        render_paper_bytes(
            legacy_paper("K-20260802-001", summary="外部改动后的总结")
        )
    )
    before = snapshot_regular_tree_no_follow(vault)

    with pytest.raises(ValueError, match="stale"):
        migrate_papers_to_v4(
            vault,
            preflight,
            backup_root=tmp_path / "backups",
            now=NOW,
        )

    assert snapshot_regular_tree_no_follow(vault) == before
    assert not (tmp_path / "backups").exists()


def test_index_failure_after_complete_migration_returns_degraded_warning(
    tmp_path,
    monkeypatch,
):
    vault = fresh_vault(tmp_path)
    path = store_legacy(
        vault,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    preflight = inspect_paper_v4_migration(vault)

    def fail_index(_vault: Path):
        raise OSError("synthetic index failure")

    monkeypatch.setattr(migration_mod, "rebuild_index_v4", fail_index)
    result = migrate_papers_to_v4(
        vault,
        preflight,
        backup_root=tmp_path / "backups",
        now=NOW,
    )

    assert result.warnings == ("index_degraded",)
    assert parse_paper_v4_bytes(path.read_bytes()).code == "K-20260802-001"
    assert result.report_path.is_file()


def test_two_stage_classifier_never_activates_v01_and_paper_migration_together(tmp_path):
    v01 = fresh_vault(tmp_path / "one")
    (v01 / "keikeu_index.json").write_text('{"version": 1}\n', encoding="utf-8")
    legacy_cache = v01 / "cache" / "legacy.md"
    legacy_cache.write_text("---\ntype: cache\n---\nraw\n", encoding="utf-8")
    assert classify_migration_stage(v01) == "v01_to_v3"

    mixed = fresh_vault(tmp_path / "two")
    (mixed / "keikeu_index.json").write_text('{"version": 1}\n', encoding="utf-8")
    store_legacy(
        mixed,
        "cache/K-20260802-001.md",
        legacy_paper("K-20260802-001"),
    )
    assert classify_migration_stage(mixed) == "repair_required"

    corrupt_mixed = fresh_vault(tmp_path / "two-b")
    (corrupt_mixed / "keikeu_index.json").write_text('{"version": 1}\n', encoding="utf-8")
    (corrupt_mixed / "cache" / "paper.md").write_text(
        "---\ntype: paper\nschema_version: 99\n---\n",
        encoding="utf-8",
    )
    assert classify_migration_stage(corrupt_mixed) == "repair_required"

    old = fresh_vault(tmp_path / "three")
    store_legacy(old, "cache/K-20260802-001.md", legacy_paper("K-20260802-001"))
    assert classify_migration_stage(old) == "paper_to_v4"

    current = fresh_vault(tmp_path / "four")
    store_v4(
        current,
        "cache/K-20260802-001.md",
        PaperV4(
            code="K-20260802-001",
            pages=[CardPageV4(content="current")],
            created=NOW,
            updated=NOW,
        ),
    )
    assert classify_migration_stage(current) == "ready"
    (current / "keikeu_index.json").write_bytes(b"invalid index")
    assert classify_migration_stage(current) == "ready"

    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside")
    (current / "cache" / "linked.md").symlink_to(outside)
    assert classify_migration_stage(current) == "repair_required"
    assert outside.read_bytes() == b"outside"
