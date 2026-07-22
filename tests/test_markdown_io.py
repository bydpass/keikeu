"""Paper v2/v3 Markdown read/write contracts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core import markdown_io as markdown_mod
from keikeu_core.markdown_io import (
    branch_paper,
    next_paper_code,
    parse_paper_bytes,
    read_paper,
    read_paper_snapshot,
    render_paper_bytes,
    update_paper,
    write_paper as _write_paper,
)
from keikeu_core.models import Highlight, Paper
from keikeu_core.vault import init_vault


def write_paper(
    vault: Path,
    paper: Paper,
    *,
    destination: str | Path | None = None,
) -> Path:
    return _write_paper(
        vault,
        paper,
        destination=destination or Path("cache") / f"{paper.code}.md",
    )


@pytest.fixture(autouse=True)
def _paper_vault_layout(tmp_path):
    init_vault(tmp_path)


def test_paper_complete_cjk_and_multiline_round_trip(tmp_path):
    created = datetime(2026, 7, 14, 9, 30)
    paper = Paper(
        code="K-20260714-001",
        initial_summary="not persisted before the first save",
        summary="深夜的末班公交上，两个人隔着一个空位假装睡着。\nA 明早离开。",
        display_name="雪夜巴士 🌙",
        highlights=[
            Highlight(
                display_name="旧打火机",
                content="旧打火机被塞回手里。\n\n2. 谁也没有解释。",
            ),
            Highlight(display_name="会被删除", content=""),
            Highlight(content="公交驶过平时下车的站。"),
        ],
        tags=["  末班车 ", "离别", "末班车", "离别 ", "暧昧"],
        created=created,
        updated=created,
        legacy_title="旧 Cache 标题",
    )

    path = write_paper(tmp_path, paper)
    back = read_paper(path)
    assert back.initial_summary == paper.summary
    assert back.summary == paper.summary
    assert back.display_name == "雪夜巴士 🌙"
    assert back.highlights == [
        Highlight(
            display_name="旧打火机",
            content="旧打火机被塞回手里。\n\n2. 谁也没有解释。",
        ),
        Highlight(content="公交驶过平时下车的站。"),
    ]
    assert back.tags == ["末班车", "离别", "暧昧"]
    assert back.legacy_title == "旧 Cache 标题"
    text = path.read_text(encoding="utf-8")
    assert "schema_version: 3" in text
    assert "display_name: 雪夜巴士 🌙" in text
    assert "   2. 谁也没有解释。" in text


def test_v2_read_then_successful_save_writes_v3_and_preserves_unknown_frontmatter(
    tmp_path,
):
    fixture = (
        Path(__file__).parent
        / "fixtures/v03-vault/mixed-vault/cache/K-20260720-001.md"
    )
    path = tmp_path / "cache" / fixture.name
    path.write_bytes(
        fixture.read_bytes().replace(
            b"fixture: synthetic-road-v03",
            b"fixture: synthetic-road-v03\nsource: C:\\drafts\\story",
        )
    )

    paper, source_bytes = read_paper_snapshot(path)
    assert paper.display_name is None
    assert paper.highlights == [
        Highlight(content="末班车的灯在雨中熄灭。"),
        Highlight(content="站台时钟比广播慢一分钟。"),
    ]
    assert paper.extra_frontmatter == {
        "fixture": "synthetic-road-v03",
        "source": r"C:\drafts\story",
    }

    paper.display_name = "蓝伞"
    paper.highlights[0].display_name = "熄灯"
    update_paper(tmp_path, path, paper, expected_source_bytes=source_bytes)

    saved = path.read_text(encoding="utf-8")
    assert "schema_version: 3" in saved
    assert "display_name: 蓝伞" in saved
    assert "fixture: synthetic-road-v03" in saved
    assert read_paper(path).extra_frontmatter["source"] == r"C:\drafts\story"
    assert read_paper(path).highlights[0] == Highlight(
        content="末班车的灯在雨中熄灭。",
        display_name="熄灯",
    )


def test_minimal_paper_keeps_empty_optional_sections(tmp_path):
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="Only required Summary."),
    )
    text = path.read_text(encoding="utf-8")
    assert "## Highlights" in text
    assert "## Tags" in text
    assert read_paper(path).highlights == []
    assert read_paper(path).tags == []


def test_snapshot_and_pure_serializer_use_exact_utf8_bytes_once(tmp_path, monkeypatch):
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="夜行列车"),
    )
    expected = path.read_bytes()
    real_open = markdown_mod.open_regular_no_follow
    opens = 0

    def counted_open(candidate: Path) -> int:
        nonlocal opens
        opens += 1
        return real_open(candidate)

    monkeypatch.setattr(markdown_mod, "open_regular_no_follow", counted_open)
    paper, source_bytes = read_paper_snapshot(path)

    assert opens == 1
    assert source_bytes == expected
    assert parse_paper_bytes(source_bytes) == paper
    assert render_paper_bytes(paper) == source_bytes


def test_write_paper_refuses_a_missing_cache_layout(tmp_path):
    (tmp_path / "cache").rmdir()

    with pytest.raises(FileNotFoundError):
        write_paper(
            tmp_path,
            Paper(code="K-20260714-001", initial_summary="", summary="summary"),
        )

    assert not (tmp_path / "cache").exists()


def test_update_preserves_frozen_draft_legacy_title_and_unknown_frontmatter(tmp_path):
    path = write_paper(
        tmp_path,
        Paper(
            code="K-20260714-001",
            initial_summary="",
            summary="first summary",
            legacy_title="old title",
        ),
    )
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "code: K-20260714-001\n", "code: K-20260714-001\nsource: hand-edit\n"
        ),
        encoding="utf-8",
    )
    edited = read_paper(path)
    expected_source_bytes = path.read_bytes()
    edited.summary = "new current summary"
    edited.initial_summary = "attempted rewrite"
    edited.legacy_title = "attempted rewrite"
    update_paper(
        tmp_path,
        path,
        edited,
        expected_source_bytes=expected_source_bytes,
    )

    back = read_paper(path)
    assert back.initial_summary == "first summary"
    assert back.summary == "new current summary"
    assert back.legacy_title == "old title"
    assert back.extra_frontmatter == {"source": "hand-edit"}


def test_blank_summary_never_creates_or_overwrites_a_paper(tmp_path):
    unsaved = Paper(code="K-20260714-001", initial_summary="", summary="valid")
    unsaved.summary = "   "
    with pytest.raises(ValueError, match="summary"):
        write_paper(tmp_path, unsaved)
    assert not (tmp_path / "cache" / "K-20260714-001.md").exists()

    path = write_paper(
        tmp_path, Paper(code="K-20260714-001", initial_summary="", summary="valid")
    )
    before = path.read_bytes()
    edited = read_paper(path)
    edited.summary = "   "
    with pytest.raises(ValueError, match="summary"):
        update_paper(tmp_path, path, edited, expected_source_bytes=before)
    assert path.read_bytes() == before


def test_next_code_and_new_write_never_overwrite(tmp_path):
    day = datetime(2026, 7, 14)
    path = write_paper(
        tmp_path, Paper(code="K-20260714-001", initial_summary="", summary="first")
    )
    before = path.read_bytes()
    assert next_paper_code(tmp_path, day) == "K-20260714-002"
    with pytest.raises(FileExistsError):
        write_paper(
            tmp_path,
            Paper(code="K-20260714-001", initial_summary="", summary="replacement"),
        )
    assert path.read_bytes() == before


def test_folder_destination_and_global_active_trash_code_scan(tmp_path):
    day = datetime(2026, 7, 14)
    active_folder = tmp_path / "cache" / "夜行列车"
    trash_folder = tmp_path / ".trash" / "cache" / "旧车站"
    active_folder.mkdir()
    trash_folder.mkdir()
    active = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="active"),
        destination="cache/夜行列车/K-20260714-001.md",
    )
    trashed = write_paper(
        tmp_path,
        Paper(code="K-20260714-002", initial_summary="", summary="trash"),
    )
    trashed.rename(trash_folder / "provider-copy.md")

    assert active == active_folder / "K-20260714-001.md"
    assert next_paper_code(tmp_path, day) == "K-20260714-003"

    paper, source_bytes = read_paper_snapshot(active)
    paper.summary = "updated in folder"
    update_paper(
        tmp_path,
        active.relative_to(tmp_path),
        paper,
        expected_source_bytes=source_bytes,
    )
    assert read_paper(active).summary == "updated in folder"


def test_write_requires_an_exact_supported_destination(tmp_path):
    paper = Paper(code="K-20260714-001", initial_summary="", summary="summary")

    with pytest.raises(ValueError, match="filename must match"):
        write_paper(tmp_path, paper, destination="cache/K-20260714-002.md")
    with pytest.raises(ValueError, match="expected"):
        write_paper(
            tmp_path,
            paper,
            destination="cache/deep/more/K-20260714-001.md",
        )


def test_folder_write_rolls_back_if_the_exact_parent_path_is_replaced(
    tmp_path,
    monkeypatch,
):
    folder = tmp_path / "cache" / "夜行列车"
    parked = tmp_path / "cache" / "parked"
    folder.mkdir()
    real_create = markdown_mod._create_regular_bytes_at
    replaced = False

    def replace_folder_then_create(*args, **kwargs):
        nonlocal replaced
        if not replaced and args[1] == "K-20260714-001.md":
            replaced = True
            folder.rename(parked)
            folder.mkdir()
        return real_create(*args, **kwargs)

    monkeypatch.setattr(
        markdown_mod,
        "_create_regular_bytes_at",
        replace_folder_then_create,
    )

    with pytest.raises(ValueError, match="directory path changed"):
        write_paper(
            tmp_path,
            Paper(code="K-20260714-001", initial_summary="", summary="summary"),
            destination="cache/夜行列车/K-20260714-001.md",
        )

    assert not (parked / "K-20260714-001.md").exists()
    assert not (folder / "K-20260714-001.md").exists()


def test_folder_update_rolls_back_if_the_exact_parent_path_is_replaced(
    tmp_path,
    monkeypatch,
):
    folder = tmp_path / "cache" / "夜行列车"
    parked = tmp_path / "cache" / "parked"
    folder.mkdir()
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="original"),
        destination="cache/夜行列车/K-20260714-001.md",
    )
    original_bytes = path.read_bytes()
    paper, source_bytes = read_paper_snapshot(path)
    paper.summary = "updated"
    real_exchange = markdown_mod.atomic_exchange_at_no_follow
    replaced = False

    def replace_folder_then_exchange(*args, **kwargs):
        nonlocal replaced
        if not replaced:
            replaced = True
            folder.rename(parked)
            folder.mkdir()
        return real_exchange(*args, **kwargs)

    monkeypatch.setattr(
        markdown_mod,
        "atomic_exchange_at_no_follow",
        replace_folder_then_exchange,
    )

    with pytest.raises(ValueError, match="directory path changed"):
        update_paper(
            tmp_path,
            path.relative_to(tmp_path),
            paper,
            expected_source_bytes=source_bytes,
        )

    assert (parked / path.name).read_bytes() == original_bytes
    assert not (folder / path.name).exists()


def test_global_duplicate_code_blocks_create_and_update_mutations(tmp_path):
    active = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="original"),
    )
    trash_folder = tmp_path / ".trash" / "cache" / "旧车站"
    trash_folder.mkdir()
    duplicate = trash_folder / "provider-copy.md"
    duplicate.write_bytes(active.read_bytes())
    original_bytes = active.read_bytes()
    active.unlink()

    with pytest.raises(FileExistsError, match="active/Trash"):
        write_paper(
            tmp_path,
            Paper(code="K-20260714-001", initial_summary="", summary="new"),
            destination="cache/K-20260714-001.md",
        )

    active.write_bytes(original_bytes)
    paper, source_bytes = read_paper_snapshot(active)
    paper.summary = "must not update"
    with pytest.raises(ValueError, match="duplicate Paper code"):
        update_paper(
            tmp_path,
            active.relative_to(tmp_path),
            paper,
            expected_source_bytes=source_bytes,
        )

    assert active.read_bytes() == original_bytes
    assert duplicate.read_bytes() == original_bytes


def test_write_rolls_back_if_the_code_appears_in_another_folder_during_create(
    tmp_path,
    monkeypatch,
):
    competing_folder = tmp_path / "cache" / "并发导入"
    competing_folder.mkdir()
    target = tmp_path / "cache" / "K-20260714-001.md"
    competing = competing_folder / "provider-copy.md"
    real_create = markdown_mod._create_regular_bytes_at

    def create_then_compete(directory_fd, name, data, display_path):
        identity = real_create(directory_fd, name, data, display_path)
        competing.write_bytes(data)
        return identity

    monkeypatch.setattr(
        markdown_mod,
        "_create_regular_bytes_at",
        create_then_compete,
    )

    with pytest.raises(FileExistsError, match="concurrently created"):
        write_paper(
            tmp_path,
            Paper(code="K-20260714-001", initial_summary="", summary="new"),
        )

    assert not target.exists()
    assert read_paper(competing).code == "K-20260714-001"


def test_write_refuses_a_byte_identical_ordinary_vault_root_replacement(
    tmp_path,
    monkeypatch,
):
    vault = tmp_path / "vault"
    replacement = tmp_path / "replacement-vault"
    parked = tmp_path / "parked-vault"
    init_vault(vault)
    shutil.copytree(vault, replacement)
    target_name = "K-20260714-001.md"
    real_create = markdown_mod._create_regular_bytes_at
    swapped = False

    def replace_root_then_create(*args, **kwargs):
        nonlocal swapped
        if not swapped and args[1] == target_name:
            swapped = True
            vault.rename(parked)
            replacement.rename(vault)
        return real_create(*args, **kwargs)

    monkeypatch.setattr(
        markdown_mod,
        "_create_regular_bytes_at",
        replace_root_then_create,
    )
    with pytest.raises(ValueError, match="directory path changed"):
        write_paper(
            vault,
            Paper(code="K-20260714-001", initial_summary="", summary="new"),
        )

    assert not (parked / "cache" / target_name).exists()
    assert not (vault / "cache" / target_name).exists()
    assert (parked / "keikeu_index.json").read_bytes() == (
        vault / "keikeu_index.json"
    ).read_bytes()


def test_create_rejects_a_symlink_target_without_touching_outside(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside bytes")
    cache = tmp_path / "cache"
    target = cache / "K-20260714-001.md"
    target.symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        write_paper(
            tmp_path,
            Paper(code="K-20260714-001", initial_summary="", summary="new"),
        )

    assert target.is_symlink()
    assert outside.read_bytes() == b"outside bytes"


def test_update_rejects_a_symlink_target_without_touching_outside(tmp_path):
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="first"),
    )
    edited = read_paper(path)
    expected_source_bytes = path.read_bytes()
    edited.summary = "replacement"
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside bytes")
    path.unlink()
    path.symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        update_paper(
            tmp_path,
            path,
            edited,
            expected_source_bytes=expected_source_bytes,
        )

    assert path.is_symlink()
    assert outside.read_bytes() == b"outside bytes"


def test_update_rejects_external_bytes_before_creating_a_temp(tmp_path):
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="first"),
    )
    expected_source_bytes = path.read_bytes()
    edited = read_paper(path)
    edited.summary = "replacement"
    external_bytes = expected_source_bytes.replace(b"first", b"other")
    path.write_bytes(external_bytes)

    with pytest.raises(ValueError, match="changed externally; update refused"):
        update_paper(
            tmp_path,
            path,
            edited,
            expected_source_bytes=expected_source_bytes,
        )

    assert path.read_bytes() == external_bytes
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_update_preserves_a_regular_file_replaced_during_validation(
    tmp_path, monkeypatch
):
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="first"),
    )
    edited = read_paper(path)
    expected_source_bytes = path.read_bytes()
    edited.summary = "replacement"
    concurrent = path.read_bytes().replace(b"first", b"other")
    concurrent_path = path.with_name("concurrent.tmp")
    concurrent_path.write_bytes(concurrent)
    real_exchange = markdown_mod.atomic_exchange_at_no_follow
    exchanged = False

    def replace_at_exchange(
        first_fd: int,
        first_name: str,
        second_fd: int,
        second_name: str,
    ) -> None:
        nonlocal exchanged
        if not exchanged:
            exchanged = True
            concurrent_path.replace(path)
        real_exchange(first_fd, first_name, second_fd, second_name)

    monkeypatch.setattr(
        markdown_mod,
        "atomic_exchange_at_no_follow",
        replace_at_exchange,
    )
    with pytest.raises(ValueError, match="changed externally; update refused"):
        update_paper(
            tmp_path,
            path,
            edited,
            expected_source_bytes=expected_source_bytes,
        )

    assert path.read_bytes() == concurrent
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_update_exchange_failure_preserves_source_and_cleans_owned_temp(
    tmp_path, monkeypatch
):
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="first"),
    )
    expected_source_bytes = path.read_bytes()
    edited = read_paper(path)
    edited.summary = "replacement"

    def fail_exchange(
        _first_fd: int,
        _first_name: str,
        _second_fd: int,
        _second_name: str,
    ) -> None:
        raise OSError("injected exchange failure")

    monkeypatch.setattr(markdown_mod, "atomic_exchange_at_no_follow", fail_exchange)
    with pytest.raises(OSError, match="injected exchange failure"):
        update_paper(
            tmp_path,
            path,
            edited,
            expected_source_bytes=expected_source_bytes,
        )

    assert path.read_bytes() == expected_source_bytes
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_update_rollback_failure_preserves_previous_and_proposed_contents(
    tmp_path, monkeypatch
):
    path = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="first"),
    )
    expected_source_bytes = path.read_bytes()
    edited = read_paper(path)
    edited.summary = "replacement"
    concurrent = expected_source_bytes.replace(b"first", b"other")
    concurrent_path = path.with_name("concurrent.tmp")
    concurrent_path.write_bytes(concurrent)
    real_exchange = markdown_mod.atomic_exchange_at_no_follow
    exchanges = 0

    def inject_then_fail_rollback(
        first_fd: int,
        first_name: str,
        second_fd: int,
        second_name: str,
    ) -> None:
        nonlocal exchanges
        exchanges += 1
        if exchanges == 1:
            concurrent_path.replace(path)
            real_exchange(first_fd, first_name, second_fd, second_name)
            return
        raise OSError("injected rollback failure")

    monkeypatch.setattr(
        markdown_mod,
        "atomic_exchange_at_no_follow",
        inject_then_fail_rollback,
    )
    with pytest.raises(OSError, match="both contents were preserved"):
        update_paper(
            tmp_path,
            path,
            edited,
            expected_source_bytes=expected_source_bytes,
        )

    temporary_paths = list(path.parent.glob(f".{path.name}.*.tmp"))
    assert len(temporary_paths) == 1
    assert temporary_paths[0].read_bytes() == concurrent
    assert read_paper(path).summary == "replacement"


def test_update_refuses_a_byte_identical_ordinary_vault_root_replacement(
    tmp_path,
    monkeypatch,
):
    vault = tmp_path / "vault"
    replacement = tmp_path / "replacement-vault"
    parked = tmp_path / "parked-vault"
    init_vault(vault)
    path = write_paper(
        vault,
        Paper(code="K-20260714-001", initial_summary="", summary="first"),
    )
    source_bytes = path.read_bytes()
    edited = read_paper(path)
    edited.summary = "replacement"
    shutil.copytree(vault, replacement)
    real_exchange = markdown_mod.atomic_exchange_at_no_follow
    swapped = False

    def replace_root_then_exchange(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            vault.rename(parked)
            replacement.rename(vault)
        return real_exchange(*args, **kwargs)

    monkeypatch.setattr(
        markdown_mod,
        "atomic_exchange_at_no_follow",
        replace_root_then_exchange,
    )
    with pytest.raises(ValueError, match="directory path changed"):
        update_paper(
            vault,
            path,
            edited,
            expected_source_bytes=source_bytes,
        )

    assert (parked / "cache" / path.name).read_bytes() == source_bytes
    assert (vault / "cache" / path.name).read_bytes() == source_bytes
    assert list((parked / "cache").glob(f".{path.name}.*.tmp")) == []
    assert list((vault / "cache").glob(f".{path.name}.*.tmp")) == []


def test_branch_copy_uses_current_summary_new_timestamps_and_no_history(tmp_path):
    source = write_paper(
        tmp_path,
        Paper(
            code="K-20260714-001",
            initial_summary="",
            summary="first summary",
            display_name="源 Paper",
            highlights=[Highlight(content="anchor")],
            tags=["tag"],
            legacy_title="old cache title",
            extra_frontmatter={"provider_history": "old"},
        ),
    )
    paper, source_bytes = read_paper_snapshot(source)
    paper.summary = "current saved summary"
    update_paper(
        tmp_path,
        source,
        paper,
        expected_source_bytes=source_bytes,
    )
    paper, source_bytes = read_paper_snapshot(source)
    branch_time = datetime(2026, 7, 22, 13, 45)
    target = branch_paper(
        tmp_path,
        source.relative_to(tmp_path),
        "cache/K-20260714-002.md",
        "K-20260714-002",
        expected_source_bytes=source_bytes,
        now=branch_time,
    )

    branched = read_paper(target)
    assert source.exists()
    assert branched.code == "K-20260714-002"
    assert branched.display_name == "源 Paper · 分支"
    assert branched.initial_summary == "current saved summary"
    assert branched.summary == "current saved summary"
    assert branched.highlights == [Highlight(content="anchor")]
    assert branched.tags == ["tag"]
    assert branched.created == branch_time
    assert branched.updated == branch_time
    assert branched.legacy_title is None
    assert branched.extra_frontmatter == {}


def test_branch_copy_refuses_occupied_code_and_changed_source(tmp_path):
    source = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="source"),
    )
    _paper, source_bytes = read_paper_snapshot(source)
    write_paper(
        tmp_path, Paper(code="K-20260714-002", initial_summary="", summary="occupied")
    )
    with pytest.raises(FileExistsError):
        branch_paper(
            tmp_path,
            source.relative_to(tmp_path),
            "cache/K-20260714-002.md",
            "K-20260714-002",
            expected_source_bytes=source_bytes,
        )

    with source.open("ab") as handle:
        handle.write(b"external edit")
    with pytest.raises(ValueError, match="changed before branch copy"):
        branch_paper(
            tmp_path,
            source.relative_to(tmp_path),
            "cache/K-20260714-003.md",
            "K-20260714-003",
            expected_source_bytes=source_bytes,
        )


def test_branch_copy_stays_in_source_folder_and_bounds_generated_name(tmp_path):
    folder = tmp_path / "cache" / "A"
    folder.mkdir(parents=True)
    source = write_paper(
        tmp_path,
        Paper(
            code="K-20260714-001",
            initial_summary="",
            summary="source",
            display_name="名" * 200,
        ),
        destination="cache/A/K-20260714-001.md",
    )
    _paper, source_bytes = read_paper_snapshot(source)

    with pytest.raises(ValueError, match="stay in the source folder"):
        branch_paper(
            tmp_path,
            source.relative_to(tmp_path),
            "cache/K-20260714-002.md",
            "K-20260714-002",
            expected_source_bytes=source_bytes,
        )

    target = branch_paper(
        tmp_path,
        source.relative_to(tmp_path),
        "cache/A/K-20260714-002.md",
        "K-20260714-002",
        expected_source_bytes=source_bytes,
    )

    assert read_paper(target).display_name == f"{'名' * 195} · 分支"
    assert not (tmp_path / "cache" / "K-20260714-003.md").exists()


def test_branch_copy_rolls_back_if_source_changes_during_create(
    tmp_path, monkeypatch
):
    source = write_paper(
        tmp_path,
        Paper(code="K-20260714-001", initial_summary="", summary="source"),
    )
    _paper, source_bytes = read_paper_snapshot(source)
    target = tmp_path / "cache" / "K-20260714-002.md"
    real_create = markdown_mod._create_regular_bytes_at
    edited = False

    def create_then_edit(*args, **kwargs):
        nonlocal edited
        identity = real_create(*args, **kwargs)
        if not edited:
            edited = True
            with source.open("ab") as handle:
                handle.write(b"source edit")
        return identity

    monkeypatch.setattr(
        markdown_mod,
        "_create_regular_bytes_at",
        create_then_edit,
    )
    with pytest.raises(ValueError, match="changed during branch copy"):
        branch_paper(
            tmp_path,
            source.relative_to(tmp_path),
            target.relative_to(tmp_path),
            "K-20260714-002",
            expected_source_bytes=source_bytes,
        )

    assert source.read_bytes().endswith(b"source edit")
    assert not target.exists()


def test_active_markdown_io_imports_no_gui_or_third_party_packages():
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.markdown_io, sys\n"
        "forbidden = {'yaml', 'flet', 'pydantic'}\n"
        "assert not (forbidden & set(sys.modules))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join([str(src), os.environ.get("PYTHONPATH", "")] )},
    )
    assert result.returncode == 0, result.stderr
