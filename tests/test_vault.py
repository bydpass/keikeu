"""Filesystem contracts for the Paper Vault and its recovery bin."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core import indexer as indexer_mod
from keikeu_core import markdown_io as markdown_mod
from keikeu_core import vault as vault_mod
from keikeu_core.markdown_io import read_paper, update_paper, write_paper
from keikeu_core.models import Highlight, Paper
from keikeu_core.vault import (
    atomic_exchange_at_no_follow,
    atomic_exchange_no_follow,
    capture_vault_selection_token,
    copy_vault_no_follow,
    get_vault,
    init_vault,
    is_vault,
    list_trashed_papers,
    open_directory_no_follow,
    open_regular_no_follow,
    require_home_path,
    require_atomic_exchange,
    resolve_active_paper_path,
    restore_paper,
    set_vault,
    snapshot_regular_tree_no_follow,
    soft_delete,
    validate_folder_name,
    validate_regular_tree_no_follow,
    validate_vault_tree_no_follow,
    validate_vault_papers,
    vault_index_version,
)


def _paper(code: str, summary: str = "A writing-ready summary.") -> Paper:
    return Paper(
        code=code,
        initial_summary="",
        summary=summary,
        highlights=[Highlight(content="Keep this beat.")],
        tags=["rain"],
        created=datetime(2026, 7, 14, 9, 0),
        updated=datetime(2026, 7, 14, 9, 0),
    )


def test_init_vault_creates_only_the_current_layout_and_empty_v3_index(tmp_path):
    vault = tmp_path / "vault"

    init_vault(vault)

    assert (vault / "cache").is_dir()
    assert (vault / ".trash" / "cache").is_dir()
    assert not (vault / "outlines").exists()
    assert not (vault / ".trash" / "outlines").exists()
    assert json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8")) == {
        "version": 3,
        "papers": [],
        "errors": [],
    }


def test_init_vault_is_idempotent_and_preserves_an_existing_index(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    index_path = vault / "keikeu_index.json"
    seeded = {"version": 2, "papers": [{"code": "K-20260714-001"}], "errors": []}
    index_path.write_text(json.dumps(seeded), encoding="utf-8")

    init_vault(vault)

    assert json.loads(index_path.read_text(encoding="utf-8")) == seeded


def test_init_rejects_an_ancestor_swapped_to_symlink_without_external_writes(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    preview = home / "preview"
    parked = home / "parked-preview"
    outside = tmp_path / "outside"
    home.mkdir()
    preview.mkdir()
    outside.mkdir()
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    real_open_child = vault_mod._open_child_directory_no_follow
    swapped = False

    def swap_preview(directory_fd: int, name: str, display_path: Path) -> int:
        nonlocal swapped
        if display_path == preview and not swapped:
            swapped = True
            preview.rename(parked)
            preview.symlink_to(outside, target_is_directory=True)
        return real_open_child(directory_fd, name, display_path)

    monkeypatch.setattr(
        vault_mod,
        "_open_child_directory_no_follow",
        swap_preview,
    )
    with pytest.raises(ValueError, match="symlink"):
        init_vault(preview / "vault")

    assert list(outside.iterdir()) == []
    assert not (parked / "vault").exists()


def test_init_writes_index_through_pinned_root_when_root_is_replaced(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    vault = home / "vault"
    parked = home / "parked-vault"
    home.mkdir()
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    real_save = indexer_mod.save_index_at

    def replace_root_before_index(directory_fd: int, index: dict[str, object]) -> None:
        vault.rename(parked)
        vault.mkdir()
        (vault / "sentinel").write_bytes(b"replacement")
        real_save(directory_fd, index)

    monkeypatch.setattr(indexer_mod, "save_index_at", replace_root_before_index)
    with pytest.raises(ValueError, match="directory path changed"):
        init_vault(vault)

    assert (parked / "keikeu_index.json").is_file()
    assert not (vault / "keikeu_index.json").exists()
    assert (vault / "sentinel").read_bytes() == b"replacement"


def test_is_vault_requires_only_cache_and_index_not_trash_or_outlines(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    (vault / ".trash" / "cache").rmdir()
    (vault / ".trash").rmdir()

    assert is_vault(vault) is True
    assert is_vault(tmp_path / "missing") is False
    assert is_vault(tmp_path) is False


def test_is_vault_accepts_rebuildable_v2_v3_but_rejects_newer_versions(
    tmp_path,
):
    vault = tmp_path / "vault"
    init_vault(vault)
    index = vault / "keikeu_index.json"

    index.write_bytes(b"not json")
    assert is_vault(vault) is True

    index.unlink()
    assert is_vault(vault) is True

    index.write_text('{"version": 3}\n', encoding="utf-8")
    assert is_vault(vault) is True

    index.write_text('{"version": 4}\n', encoding="utf-8")
    assert is_vault(vault) is False

    index.unlink()
    (vault / ".trash" / "cache").rmdir()
    (vault / ".trash").rmdir()
    assert is_vault(vault) is False


def test_full_chain_openers_reject_symlink_ancestors(tmp_path):
    real = tmp_path / "real"
    (real / "nested").mkdir(parents=True)
    paper = real / "nested" / "paper.md"
    paper.write_bytes(b"unchanged")
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        open_directory_no_follow(linked / "nested")
    with pytest.raises(ValueError, match="symlink"):
        open_regular_no_follow(linked / "nested" / "paper.md")

    assert paper.read_bytes() == b"unchanged"


@pytest.mark.parametrize("linked_entry", ["root", "cache", "index"])
def test_is_vault_rejects_symlink_required_entries(tmp_path, linked_entry):
    vault = tmp_path / "vault"
    outside = tmp_path / "outside"
    outside.mkdir()

    if linked_entry == "root":
        target = outside / "vault"
        (target / "cache").mkdir(parents=True)
        (target / "keikeu_index.json").write_text("{}", encoding="utf-8")
        vault.symlink_to(target, target_is_directory=True)
    else:
        vault.mkdir()
        if linked_entry == "cache":
            target = outside / "cache"
            target.mkdir()
            (vault / "cache").symlink_to(target, target_is_directory=True)
            (vault / "keikeu_index.json").write_text("{}", encoding="utf-8")
        else:
            (vault / "cache").mkdir()
            target = outside / "index.json"
            target.write_text("{}", encoding="utf-8")
            (vault / "keikeu_index.json").symlink_to(target)

    assert is_vault(vault) is False


def test_outside_regular_tree_can_be_classified_read_only(tmp_path, monkeypatch):
    home = tmp_path / "simulated-home"
    source = tmp_path / "outside" / "vault"
    home.mkdir()
    (source / "cache").mkdir(parents=True)
    (source / "keikeu_index.json").write_text(
        '{"version": 2, "papers": [], "errors": []}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)

    validate_regular_tree_no_follow(source)
    assert vault_index_version(source) == 2
    assert is_vault(source) is True
    with pytest.raises(ValueError, match="outside current user Home"):
        validate_vault_tree_no_follow(source)

    (source / "keikeu_index.json").write_text(
        '{"version": 3, "papers": [], "errors": []}\n',
        encoding="utf-8",
    )
    assert vault_index_version(source) == 3
    assert is_vault(source) is True

    (source / "keikeu_index.json").write_text(
        '{"version": 4, "papers": [], "errors": []}\n',
        encoding="utf-8",
    )
    assert is_vault(source) is False


def test_regular_tree_snapshot_is_deterministic_and_detects_byte_changes(tmp_path):
    source = tmp_path / "outside-source"
    (source / "b" / "empty").mkdir(parents=True)
    (source / "a.txt").write_bytes(b"alpha")
    (source / "b" / "z.bin").write_bytes(b"zeta")

    first = snapshot_regular_tree_no_follow(source)

    assert first == (
        (Path("b"), Path("b/empty")),
        (
            (Path("a.txt"), hashlib.sha256(b"alpha").hexdigest()),
            (Path("b/z.bin"), hashlib.sha256(b"zeta").hexdigest()),
        ),
    )
    assert snapshot_regular_tree_no_follow(source) == first

    (source / "a.txt").write_bytes(b"changed")
    assert snapshot_regular_tree_no_follow(source) != first

    (source / "linked").symlink_to(source / "a.txt")
    with pytest.raises(ValueError, match="symlink"):
        snapshot_regular_tree_no_follow(source)


def test_regular_tree_snapshot_rejects_a_file_replaced_after_hashing(
    tmp_path, monkeypatch
):
    source = tmp_path / "source"
    source.mkdir()
    paper = source / "paper.md"
    paper.write_bytes(b"original")
    replacement = tmp_path / "replacement.md"
    replacement.write_bytes(b"replacement")
    real_scan = vault_mod._scan_regular_tree_fd
    scans = 0

    def replace_before_final_scan(root_fd: int, root: Path):
        nonlocal scans
        scans += 1
        if scans == 2:
            replacement.replace(paper)
        return real_scan(root_fd, root)

    monkeypatch.setattr(
        vault_mod,
        "_scan_regular_tree_fd",
        replace_before_final_scan,
    )
    with pytest.raises(ValueError, match="changed after hashing"):
        snapshot_regular_tree_no_follow(source)

    assert paper.read_bytes() == b"replacement"


def test_native_exchange_swaps_regular_files_and_directories(tmp_path):
    require_atomic_exchange()
    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.txt"
    first_file.write_bytes(b"first")
    second_file.write_bytes(b"second")

    atomic_exchange_no_follow(first_file, second_file)

    assert first_file.read_bytes() == b"second"
    assert second_file.read_bytes() == b"first"

    first_directory = tmp_path / "first-directory"
    second_directory = tmp_path / "second-directory"
    first_directory.mkdir()
    second_directory.mkdir()
    (first_directory / "marker").write_bytes(b"first directory")
    (second_directory / "marker").write_bytes(b"second directory")

    atomic_exchange_no_follow(first_directory, second_directory)

    assert (first_directory / "marker").read_bytes() == b"second directory"
    assert (second_directory / "marker").read_bytes() == b"first directory"


def test_native_exchange_uses_caller_pinned_parent_descriptors(tmp_path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    parent_fd = open_directory_no_follow(tmp_path)
    try:
        atomic_exchange_at_no_follow(parent_fd, first.name, parent_fd, second.name)
    finally:
        os.close(parent_fd)

    assert first.read_bytes() == b"second"
    assert second.read_bytes() == b"first"


def test_atomic_exchange_rejects_symlinks_without_touching_targets(tmp_path):
    outside = tmp_path / "outside.txt"
    ordinary = tmp_path / "ordinary.txt"
    linked = tmp_path / "linked.txt"
    outside.write_bytes(b"outside")
    ordinary.write_bytes(b"ordinary")
    linked.symlink_to(outside)

    with pytest.raises(ValueError, match="unsupported exchange entry"):
        atomic_exchange_no_follow(linked, ordinary)

    assert linked.is_symlink()
    assert outside.read_bytes() == b"outside"
    assert ordinary.read_bytes() == b"ordinary"


def test_unsupported_atomic_exchange_fails_before_mutation(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    monkeypatch.setattr(vault_mod.sys, "platform", "unsupported-os")

    with pytest.raises(RuntimeError, match="atomic filesystem exchange is unavailable"):
        atomic_exchange_no_follow(first, second)

    assert first.read_bytes() == b"first"
    assert second.read_bytes() == b"second"


def test_active_resolver_accepts_only_direct_current_v2_papers(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    paper = write_paper(vault, _paper("K-20260714-001"))

    assert resolve_active_paper_path(vault, paper) == paper
    assert resolve_active_paper_path(vault, paper.relative_to(vault)) == paper
    assert resolve_active_paper_path(
        vault,
        "cache/K-20260714-002.md",
        must_exist=False,
    ) == vault / "cache" / "K-20260714-002.md"

    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside")
    for candidate in (
        outside,
        "../outside.md",
        "cache/../cache/K-20260714-001.md",
        "cache/nested/K-20260714-001.md",
        ".trash/cache/K-20260714-001.md",
    ):
        with pytest.raises((FileNotFoundError, ValueError)):
            resolve_active_paper_path(vault, candidate)


def test_soft_delete_moves_only_active_papers_and_preserves_bytes(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    source = write_paper(vault, _paper("K-20260714-001"))
    source_bytes = source.read_bytes()

    moved = soft_delete(vault, "cache/K-20260714-001.md")

    assert moved == vault / ".trash" / "cache" / "K-20260714-001.md"
    assert not source.exists()
    assert moved.read_bytes() == source_bytes

    for rel_path in (
        "outlines/old.md",
        ".trash/cache/K-20260714-001.md",
        "cache/nested/K-20260714-001.md",
        "../cache/K-20260714-001.md",
    ):
        with pytest.raises(ValueError, match=r"cache/\*\.md"):
            soft_delete(vault, rel_path)


def test_soft_delete_avoids_overwriting_an_existing_trash_file(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    source = write_paper(vault, _paper("K-20260714-001"))
    existing = vault / ".trash" / "cache" / source.name
    existing.write_bytes(b"older trash bytes")

    moved = soft_delete(vault, "cache/K-20260714-001.md")

    assert moved.parent == existing.parent
    assert moved.name.startswith("K-20260714-001-")
    assert moved.suffix == ".md"
    assert existing.read_bytes() == b"older trash bytes"


def test_soft_delete_does_not_overwrite_a_target_injected_at_move_time(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    init_vault(vault)
    source = write_paper(vault, _paper("K-20260714-001"))
    raced_target = vault / ".trash" / "cache" / source.name
    real_move = vault_mod._move_regular_no_overwrite_at
    first_call = True

    def inject_target_then_move(
        source_directory_fd: int,
        source_name: str,
        destination_directory_fd: int,
        destination_name: str,
        **kwargs,
    ) -> None:
        nonlocal first_call
        if first_call:
            first_call = False
            descriptor = os.open(
                destination_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=destination_directory_fd,
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(b"concurrent target")
        real_move(
            source_directory_fd,
            source_name,
            destination_directory_fd,
            destination_name,
            **kwargs,
        )

    monkeypatch.setattr(
        vault_mod,
        "_move_regular_no_overwrite_at",
        inject_target_then_move,
    )
    moved = soft_delete(vault, str(source.relative_to(vault)))

    assert raced_target.read_bytes() == b"concurrent target"
    assert moved != raced_target
    assert moved.read_bytes() != b"concurrent target"


def test_soft_delete_refuses_an_ordinary_vault_root_replacement(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    parked = tmp_path / "parked-vault"
    replacement = tmp_path / "replacement-vault"
    init_vault(vault)
    init_vault(replacement)
    original = write_paper(vault, _paper("K-20260714-001", "original"))
    replacement_paper = write_paper(
        replacement,
        _paper("K-20260714-001", "replacement"),
    )
    original_bytes = original.read_bytes()
    replacement_bytes = replacement_paper.read_bytes()
    real_move = vault_mod._move_regular_no_overwrite_at
    swapped = False

    def replace_root_then_move(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            vault.rename(parked)
            replacement.rename(vault)
        return real_move(*args, **kwargs)

    monkeypatch.setattr(
        vault_mod,
        "_move_regular_no_overwrite_at",
        replace_root_then_move,
    )
    with pytest.raises(ValueError, match="directory path changed"):
        soft_delete(vault, "cache/K-20260714-001.md")

    assert (parked / "cache" / original.name).read_bytes() == original_bytes
    assert not (parked / ".trash" / "cache" / original.name).exists()
    assert (vault / "cache" / replacement_paper.name).read_bytes() == replacement_bytes
    assert not (vault / ".trash" / "cache" / replacement_paper.name).exists()


def test_list_trashed_papers_is_sorted_and_uses_relative_paths(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    write_paper(vault, _paper("K-20260714-001"))
    write_paper(vault, _paper("K-20260714-002"))
    soft_delete(vault, "cache/K-20260714-002.md")
    soft_delete(vault, "cache/K-20260714-001.md")

    assert list_trashed_papers(vault) == [
        Path(".trash/cache/K-20260714-001.md"),
        Path(".trash/cache/K-20260714-002.md"),
    ]


def test_restore_paper_moves_original_bytes_back_when_there_is_no_collision(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    source = write_paper(vault, _paper("K-20260714-001"))
    source_bytes = source.read_bytes()
    trashed = soft_delete(vault, "cache/K-20260714-001.md")

    restored = restore_paper(vault, str(trashed.relative_to(vault)))

    assert restored == source
    assert restored.read_bytes() == source_bytes
    assert not trashed.exists()


def test_normal_restore_refuses_an_ordinary_vault_root_replacement(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    parked = tmp_path / "parked-vault"
    replacement = tmp_path / "replacement-vault"
    init_vault(vault)
    init_vault(replacement)
    original = write_paper(vault, _paper("K-20260714-001", "original"))
    original_trash = soft_delete(vault, str(original.relative_to(vault)))
    replacement_paper = write_paper(
        replacement,
        _paper("K-20260714-001", "replacement"),
    )
    replacement_trash = soft_delete(
        replacement,
        str(replacement_paper.relative_to(replacement)),
    )
    original_bytes = original_trash.read_bytes()
    replacement_bytes = replacement_trash.read_bytes()
    real_move = vault_mod._move_regular_no_overwrite_at
    swapped = False

    def replace_root_then_move(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            vault.rename(parked)
            replacement.rename(vault)
        return real_move(*args, **kwargs)

    monkeypatch.setattr(
        vault_mod,
        "_move_regular_no_overwrite_at",
        replace_root_then_move,
    )
    with pytest.raises(ValueError, match="directory path changed"):
        restore_paper(vault, ".trash/cache/K-20260714-001.md")

    assert (parked / ".trash/cache/K-20260714-001.md").read_bytes() == original_bytes
    assert not (parked / "cache/K-20260714-001.md").exists()
    assert (vault / ".trash/cache/K-20260714-001.md").read_bytes() == replacement_bytes
    assert not (vault / "cache/K-20260714-001.md").exists()


def test_restore_paper_requires_a_new_code_for_an_active_code_collision(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    deleted = write_paper(vault, _paper("K-20260714-001", "Original summary."))
    deleted_bytes = deleted.read_bytes()
    trashed = soft_delete(vault, "cache/K-20260714-001.md")
    active = write_paper(vault, _paper("K-20260714-001", "Current summary."))
    active_bytes = active.read_bytes()

    with pytest.raises(FileExistsError, match="choose a new Paper code"):
        restore_paper(vault, str(trashed.relative_to(vault)))

    assert trashed.read_bytes() == deleted_bytes
    assert active.read_bytes() == active_bytes


def test_restore_paper_with_new_code_preserves_frozen_draft_and_current_summary(
    tmp_path,
):
    vault = tmp_path / "vault"
    init_vault(vault)
    original = write_paper(vault, _paper("K-20260714-001", "First summary."))
    expected_source_bytes = original.read_bytes()
    edited = read_paper(original)
    edited.summary = "Edited current summary."
    edited.updated = datetime(2026, 7, 14, 10, 0)
    update_paper(
        vault,
        original,
        edited,
        expected_source_bytes=expected_source_bytes,
    )
    trashed = soft_delete(vault, "cache/K-20260714-001.md")
    write_paper(vault, _paper("K-20260714-001", "Current active paper."))

    restored = restore_paper(
        vault,
        str(trashed.relative_to(vault)),
        new_code="K-20260714-002",
    )

    paper = read_paper(restored)
    assert restored.name == "K-20260714-002.md"
    assert paper.code == "K-20260714-002"
    assert paper.initial_summary == "First summary."
    assert paper.summary == "Edited current summary."
    assert not trashed.exists()


def test_restore_with_new_code_refuses_a_byte_identical_ordinary_root_replacement(
    tmp_path,
    monkeypatch,
):
    vault = tmp_path / "vault"
    replacement = tmp_path / "replacement-vault"
    parked = tmp_path / "parked-vault"
    init_vault(vault)
    original = write_paper(vault, _paper("K-20260714-001", "original"))
    trashed = soft_delete(vault, str(original.relative_to(vault)))
    active = write_paper(vault, _paper("K-20260714-001", "active"))
    trashed_bytes = trashed.read_bytes()
    active_bytes = active.read_bytes()
    shutil.copytree(vault, replacement)
    real_move = markdown_mod._move_regular_no_overwrite_at
    swapped = False

    def replace_root_then_move(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            vault.rename(parked)
            replacement.rename(vault)
        return real_move(*args, **kwargs)

    monkeypatch.setattr(
        markdown_mod,
        "_move_regular_no_overwrite_at",
        replace_root_then_move,
    )
    with pytest.raises(ValueError, match="changed before restore cleanup"):
        restore_paper(
            vault,
            ".trash/cache/K-20260714-001.md",
            new_code="K-20260714-002",
        )

    for root in (parked, vault):
        assert (
            root / ".trash/cache/K-20260714-001.md"
        ).read_bytes() == trashed_bytes
        assert (root / "cache/K-20260714-001.md").read_bytes() == active_bytes
        assert not (root / "cache/K-20260714-002.md").exists()


def test_restore_paper_rejects_non_trash_paths_and_existing_new_code(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    write_paper(vault, _paper("K-20260714-001"))
    trashed = soft_delete(vault, "cache/K-20260714-001.md")
    write_paper(vault, _paper("K-20260714-001", "Current active paper."))
    write_paper(vault, _paper("K-20260714-002"))

    with pytest.raises(ValueError, match=r"\.trash/cache/\*\.md"):
        restore_paper(vault, "cache/K-20260714-001.md")
    with pytest.raises(FileExistsError):
        restore_paper(
            vault,
            str(trashed.relative_to(vault)),
            new_code="K-20260714-002",
        )


def test_strict_vault_validation_includes_recovery_papers(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    source = write_paper(vault, _paper("K-20260714-001"))
    soft_delete(vault, str(source.relative_to(vault)))

    validate_vault_papers(vault)

    broken = vault / ".trash" / "cache" / "broken.md"
    broken.write_text("not a Paper\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        validate_vault_papers(vault)


def test_restore_rollback_does_not_unlink_a_concurrently_replaced_target(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    init_vault(vault)
    original = write_paper(vault, _paper("K-20260714-001", "original"))
    trashed = soft_delete(vault, str(original.relative_to(vault)))
    write_paper(vault, _paper("K-20260714-001", "active"))
    target = vault / "cache" / "K-20260714-002.md"

    def fail_source_cleanup(*args, **kwargs) -> None:
        target.unlink()
        target.write_bytes(b"concurrent replacement")
        raise ValueError("injected source cleanup failure")

    monkeypatch.setattr(
        markdown_mod,
        "_move_regular_no_overwrite_at",
        fail_source_cleanup,
    )
    with pytest.raises(OSError, match="both files were preserved"):
        restore_paper(
            vault,
            str(trashed.relative_to(vault)),
            new_code="K-20260714-002",
        )

    assert trashed.exists()
    assert target.read_bytes() == b"concurrent replacement"


def test_restore_preserves_a_source_edited_in_place_before_cleanup(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    init_vault(vault)
    original = write_paper(vault, _paper("K-20260714-001", "original"))
    trashed = soft_delete(vault, str(original.relative_to(vault)))
    write_paper(vault, _paper("K-20260714-001", "active"))
    target = vault / "cache" / "K-20260714-002.md"
    original_bytes = trashed.read_bytes()
    real_move = markdown_mod._move_regular_no_overwrite_at
    edited = False

    def edit_source_before_cleanup(*args, **kwargs) -> None:
        nonlocal edited
        if not edited:
            edited = True
            with trashed.open("ab") as handle:
                handle.write(b"external edit")
        real_move(*args, **kwargs)

    monkeypatch.setattr(
        markdown_mod,
        "_move_regular_no_overwrite_at",
        edit_source_before_cleanup,
    )
    with pytest.raises(ValueError, match="changed before restore cleanup"):
        restore_paper(
            vault,
            str(trashed.relative_to(vault)),
            new_code="K-20260714-002",
        )

    assert trashed.read_bytes() == original_bytes + b"external edit"
    assert not target.exists()


def test_set_then_get_vault_round_trips_and_bad_config_is_safe(tmp_path):
    vault = tmp_path / "vault"
    config = tmp_path / "config" / "keikeu_config.json"
    vault.mkdir()
    set_vault(vault, config, capture_vault_selection_token(vault))
    assert get_vault(config) == vault.resolve()

    assert get_vault(tmp_path / "missing.json") is None
    for payload in ("not json", '{"vault": 1}', '{"vault": null}', "[]"):
        config.write_text(payload, encoding="utf-8")
        assert get_vault(config) is None


def test_set_vault_rejects_a_validated_token_for_a_replaced_non_vault_root(
    tmp_path,
    monkeypatch,
):
    home = tmp_path / "simulated-home"
    vault = home / "vault"
    parked = home / "parked-vault"
    config = home / "config.json"
    home.mkdir()
    vault.mkdir()
    (vault / "validated.txt").write_bytes(b"validated bytes")
    config.write_bytes(b'{"vault": "old"}\n')
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    selection = capture_vault_selection_token(vault)
    vault.rename(parked)
    vault.mkdir()
    (vault / "ordinary.txt").write_bytes(b"ordinary replacement")

    with pytest.raises(ValueError, match="validated selection"):
        set_vault(vault, config, selection)

    assert config.read_bytes() == b'{"vault": "old"}\n'
    assert (parked / "validated.txt").read_bytes() == b"validated bytes"
    assert (vault / "ordinary.txt").read_bytes() == b"ordinary replacement"
    assert list(home.glob(f".{config.name}.*.tmp")) == []


def test_home_guard_allows_home_and_rejects_outside_and_symlink_escape(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    outside = tmp_path / "outside-simulated-home"
    home.mkdir()
    outside.mkdir()
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)

    assert require_home_path(home / "new-vault") == (home / "new-vault").resolve()
    with pytest.raises(ValueError, match="outside current user Home"):
        init_vault(outside / "vault")
    assert not (outside / "vault").exists()

    escape = home / "escape"
    escape.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        init_vault(escape / "vault")
    assert not (outside / "vault").exists()

    bundle = home / "Applications" / "keikeu.app" / "vault"
    with pytest.raises(ValueError, match="application bundle"):
        init_vault(bundle)
    assert not bundle.exists()


def test_existing_vault_mutations_refuse_an_outside_home_source(tmp_path, monkeypatch):
    home = tmp_path / "simulated-home"
    vault = tmp_path / "outside-simulated-home" / "vault"
    active = vault / "cache" / "K-20260714-001.md"
    trashed = vault / ".trash" / "cache" / "K-20260714-002.md"
    home.mkdir()
    active.parent.mkdir(parents=True)
    trashed.parent.mkdir(parents=True)
    active.write_bytes(b"active bytes")
    trashed.write_bytes(b"trash bytes")
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)

    with pytest.raises(ValueError, match="outside current user Home"):
        soft_delete(vault, "cache/K-20260714-001.md")
    with pytest.raises(ValueError, match="outside current user Home"):
        restore_paper(vault, ".trash/cache/K-20260714-002.md")

    assert active.read_bytes() == b"active bytes"
    assert trashed.read_bytes() == b"trash bytes"


def test_root_symlink_is_rejected_by_init_set_and_paper_mutations(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    real_vault = home / "real-vault"
    linked_vault = home / "linked-vault"
    config = home / "config.json"
    home.mkdir()
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    init_vault(real_vault)
    active = write_paper(real_vault, _paper("K-20260714-001"))
    to_trash = write_paper(real_vault, _paper("K-20260714-002"))
    trashed = soft_delete(real_vault, str(to_trash.relative_to(real_vault)))
    linked_vault.symlink_to(real_vault, target_is_directory=True)
    config.write_bytes(b'{"vault": "old"}\n')
    before = {
        str(path.relative_to(real_vault)): path.read_bytes()
        for path in real_vault.rglob("*")
        if path.is_file()
    }

    for action in (
        lambda: init_vault(linked_vault),
        lambda: set_vault(
            linked_vault,
            config,
            capture_vault_selection_token(real_vault),
        ),
        lambda: soft_delete(linked_vault, str(active.relative_to(real_vault))),
        lambda: restore_paper(linked_vault, str(trashed.relative_to(real_vault))),
    ):
        with pytest.raises(ValueError, match="symlink"):
            action()

    assert config.read_bytes() == b'{"vault": "old"}\n'
    assert {
        str(path.relative_to(real_vault)): path.read_bytes()
        for path in real_vault.rglob("*")
        if path.is_file()
    } == before


def test_vault_tree_validator_accepts_empty_and_rejects_missing(tmp_path, monkeypatch):
    home = tmp_path / "simulated-home"
    empty = home / "empty-vault"
    empty.mkdir(parents=True)
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)

    validate_vault_tree_no_follow(empty)
    with pytest.raises(FileNotFoundError):
        validate_vault_tree_no_follow(home / "missing-vault")


@pytest.mark.parametrize("linked_entry", ["cache", "trash", "index"])
def test_init_rejects_internal_symlinks_without_changing_outside_or_config(
    tmp_path, monkeypatch, linked_entry
):
    home = tmp_path / "simulated-home"
    outside = tmp_path / "outside-simulated-home"
    vault = home / "vault"
    config = home / "config.json"
    home.mkdir()
    outside.mkdir()
    vault.mkdir()
    config.write_bytes(b'{"vault": "old"}\n')

    if linked_entry == "cache":
        target = outside / "cache"
        target.mkdir()
        (target / "outside.txt").write_bytes(b"outside cache bytes")
        (vault / "cache").symlink_to(target, target_is_directory=True)
    elif linked_entry == "trash":
        (vault / "cache").mkdir()
        target = outside / "trash"
        target.mkdir()
        (target / "outside.txt").write_bytes(b"outside trash bytes")
        (vault / ".trash").symlink_to(target, target_is_directory=True)
    else:
        (vault / "cache").mkdir()
        target = outside / "index.json"
        target.write_bytes(b"outside index bytes")
        (vault / "keikeu_index.json").symlink_to(target)

    before = {
        str(path.relative_to(outside)): path.read_bytes()
        for path in outside.rglob("*")
        if path.is_file()
    }
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    clean = home / "clean-selection"
    clean.mkdir()
    selection = capture_vault_selection_token(clean)

    with pytest.raises(ValueError, match="symlink"):
        init_vault(vault)
    with pytest.raises(ValueError, match="symlink"):
        set_vault(vault, config, selection)

    assert {
        str(path.relative_to(outside)): path.read_bytes()
        for path in outside.rglob("*")
        if path.is_file()
    } == before
    assert config.read_bytes() == b'{"vault": "old"}\n'


@pytest.mark.parametrize(
    ("operation", "linked_rel_path"),
    [
        ("soft-delete", Path("cache/K-20260714-001.md")),
        ("restore", Path(".trash/cache/K-20260714-001.md")),
    ],
)
def test_paper_mutations_reject_symlink_assets_without_changing_outside_or_config(
    tmp_path, monkeypatch, operation, linked_rel_path
):
    home = tmp_path / "simulated-home"
    outside = tmp_path / "outside-simulated-home"
    vault = home / "vault"
    config = home / "config.json"
    (vault / "cache").mkdir(parents=True)
    (vault / ".trash" / "cache").mkdir(parents=True)
    (vault / "keikeu_index.json").write_text("{}", encoding="utf-8")
    outside.mkdir()
    outside_paper = outside / "paper.md"
    outside_paper.write_bytes(b"outside Paper bytes")
    linked_path = vault / linked_rel_path
    linked_path.symlink_to(outside_paper)
    config.write_bytes(b'{"vault": "old"}\n')
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)

    if operation == "soft-delete":
        action = lambda: soft_delete(vault, str(linked_rel_path))
    else:
        action = lambda: restore_paper(vault, str(linked_rel_path))

    with pytest.raises(ValueError, match="symlink"):
        action()

    assert outside_paper.read_bytes() == b"outside Paper bytes"
    assert linked_path.is_symlink()
    assert config.read_bytes() == b'{"vault": "old"}\n'


def test_folder_name_validation_preserves_trimmed_text_and_exact_boundaries():
    assert validate_folder_name("  夜行列车 🚂  ") == "夜行列车 🚂"
    assert validate_folder_name("x" * 200) == "x" * 200
    assert validate_folder_name("家族\u200d剪影") == "家族\u200d剪影"

    for invalid in (
        "",
        " " * 4,
        "x" * 201,
        ".",
        "..",
        ".hidden",
        "bad/name",
        "bad:name",
        "two\nlines",
        "null\x00name",
        "TRASH",
        "全部 paper",
        "keikeu_INDEX.json",
    ):
        with pytest.raises(ValueError):
            validate_folder_name(invalid)


def test_set_vault_validates_both_home_paths_and_preserves_config_on_failure(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    outside = tmp_path / "outside-simulated-home"
    vault = home / "vault"
    config = home / "config" / "keikeu_config.json"
    vault.mkdir(parents=True)
    outside.mkdir()
    config.parent.mkdir()
    original = b'{"vault": "old"}\n'
    config.write_bytes(original)
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    selection = capture_vault_selection_token(vault)

    with pytest.raises(ValueError, match="outside current user Home"):
        set_vault(outside, config, selection)
    assert config.read_bytes() == original
    with pytest.raises(ValueError, match="outside current user Home"):
        set_vault(vault, outside / "config.json", selection)
    assert config.read_bytes() == original
    with pytest.raises(ValueError, match="existing directory"):
        set_vault(home / "missing", config, selection)
    assert config.read_bytes() == original

    def fail_replace(_source, _destination, **_kwargs) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(vault_mod.os, "replace", fail_replace)
    with pytest.raises(OSError, match="synthetic replace failure"):
        set_vault(vault, config, selection)
    assert config.read_bytes() == original
    assert list(config.parent.glob(f".{config.name}.*.tmp")) == []


def test_set_vault_rejects_an_ordinary_candidate_root_replacement(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    vault = home / "vault"
    parked = home / "parked-vault"
    config = home / "config" / "keikeu_config.json"
    vault.mkdir(parents=True)
    config.parent.mkdir()
    original = b'{"vault": "old"}\n'
    config.write_bytes(original)
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    selection = capture_vault_selection_token(vault)
    real_snapshot = vault_mod._snapshot_regular_tree_fd
    snapshots = 0

    def replace_after_revalidation(root_fd: int, root: Path):
        nonlocal snapshots
        result = real_snapshot(root_fd, root)
        if root == vault:
            snapshots += 1
            if snapshots == 2:
                vault.rename(parked)
                vault.mkdir()
                (vault / "sentinel").write_bytes(b"replacement")
        return result

    monkeypatch.setattr(
        vault_mod,
        "_snapshot_regular_tree_fd",
        replace_after_revalidation,
    )
    with pytest.raises(ValueError, match="directory path changed"):
        set_vault(vault, config, selection)

    assert config.read_bytes() == original
    assert (vault / "sentinel").read_bytes() == b"replacement"
    assert list(config.parent.glob(f".{config.name}.*.tmp")) == []


def test_copy_vault_no_follow_copies_exact_tree_and_bytes_without_source_changes(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    source = tmp_path / "outside-simulated-home" / "unsafe-vault"
    destination = home / "copied-vault"
    home.mkdir()
    (source / "cache" / "empty-folder").mkdir(parents=True)
    (source / "cache" / "paper.md").write_bytes(b"\x00synthetic Paper\n")
    (source / "keikeu_index.json").write_bytes(b'{"version": 2}\n')
    before = {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)

    copied = copy_vault_no_follow(source, destination)

    assert copied == destination.resolve()
    assert (destination / "cache" / "empty-folder").is_dir()
    assert {
        str(path.relative_to(destination)): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file()
    } == before
    assert {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    } == before


def test_copy_vault_no_follow_rejects_existing_symlink_and_special_entries(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    source = tmp_path / "outside-simulated-home" / "unsafe-vault"
    home.mkdir()
    source.mkdir(parents=True)
    (source / "regular.txt").write_bytes(b"unchanged")
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)

    existing = home / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        copy_vault_no_follow(source, existing)

    dangling = home / "dangling-destination"
    dangling.symlink_to(home / "missing-target")
    with pytest.raises(FileExistsError):
        copy_vault_no_follow(source, dangling)

    root_link = tmp_path / "source-link"
    root_link.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        copy_vault_no_follow(root_link, home / "root-link-copy")
    assert not (home / "root-link-copy").exists()

    descendant_link = source / "linked-file"
    descendant_link.symlink_to(source / "regular.txt")
    with pytest.raises(ValueError, match="symlink"):
        copy_vault_no_follow(source, home / "descendant-link-copy")
    descendant_link.unlink()
    assert not (home / "descendant-link-copy").exists()

    special = source / "named-pipe"
    os.mkfifo(special)
    try:
        with pytest.raises(ValueError, match="special filesystem entry"):
            copy_vault_no_follow(source, home / "special-copy")
    finally:
        special.unlink()
    assert not (home / "special-copy").exists()
    assert (source / "regular.txt").read_bytes() == b"unchanged"


def test_copy_rejects_a_destination_ancestor_swapped_to_symlink(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    source = tmp_path / "source"
    preview = home / "preview"
    parked = home / "parked-preview"
    outside = tmp_path / "outside"
    home.mkdir()
    source.mkdir()
    preview.mkdir()
    outside.mkdir()
    (source / "paper.md").write_bytes(b"source")
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    real_open_child = vault_mod._open_child_directory_no_follow
    swapped = False

    def swap_preview(directory_fd: int, name: str, display_path: Path) -> int:
        nonlocal swapped
        if display_path == preview and not swapped:
            swapped = True
            preview.rename(parked)
            preview.symlink_to(outside, target_is_directory=True)
        return real_open_child(directory_fd, name, display_path)

    monkeypatch.setattr(
        vault_mod,
        "_open_child_directory_no_follow",
        swap_preview,
    )
    with pytest.raises(ValueError, match="symlink"):
        copy_vault_no_follow(source, preview / "copy")

    assert list(outside.iterdir()) == []
    assert not (parked / "copy").exists()


def test_copy_root_swap_never_writes_through_the_replacement(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    source = tmp_path / "source"
    destination = home / "copy"
    parked = home / "parked-copy"
    outside = tmp_path / "outside"
    home.mkdir()
    source.mkdir()
    outside.mkdir()
    (source / "paper.md").write_bytes(b"source")
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    real_copy = vault_mod._copy_regular_file_at
    swapped = False

    def swap_destination_root(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            destination.rename(parked)
            destination.symlink_to(outside, target_is_directory=True)
        return real_copy(*args, **kwargs)

    monkeypatch.setattr(vault_mod, "_copy_regular_file_at", swap_destination_root)
    with pytest.raises(ValueError, match="symlink|destination path changed"):
        copy_vault_no_follow(source, destination)

    assert list(outside.iterdir()) == []
    assert destination.is_symlink()
    assert list(parked.iterdir()) == []


def test_leaf_copy_never_unlinks_a_destination_it_did_not_create(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(b"source bytes")
    destination.write_bytes(b"pre-existing bytes")

    with pytest.raises(FileExistsError):
        vault_mod._copy_regular_file(source, destination)

    assert source.read_bytes() == b"source bytes"
    assert destination.read_bytes() == b"pre-existing bytes"


def test_leaf_copy_removes_only_its_own_partial_file(tmp_path, monkeypatch):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(b"source bytes")

    def fail_copy(_source, destination_handle):
        destination_handle.write(b"partial")
        raise OSError("synthetic copy failure")

    monkeypatch.setattr(vault_mod.shutil, "copyfileobj", fail_copy)
    with pytest.raises(OSError, match="synthetic copy failure"):
        vault_mod._copy_regular_file(source, destination)

    assert source.read_bytes() == b"source bytes"
    assert not destination.exists()


def test_copy_verification_failure_keeps_source_config_and_destination_unchanged(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    source = tmp_path / "outside-simulated-home" / "unsafe-vault"
    destination = home / "copy"
    config = home / "config.json"
    home.mkdir()
    source.mkdir(parents=True)
    (source / "paper.md").write_bytes(b"source bytes")
    config.write_bytes(b'{"vault": "old"}\n')
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    real_snapshot = vault_mod._snapshot_regular_tree_fd
    snapshots = 0

    def corrupt_destination_snapshot(root_fd: int, root: Path):
        nonlocal snapshots
        snapshots += 1
        result = real_snapshot(root_fd, root)
        if snapshots == 3:
            return result[0], ((Path("paper.md"), "wrong digest"),)
        return result

    monkeypatch.setattr(
        vault_mod,
        "_snapshot_regular_tree_fd",
        corrupt_destination_snapshot,
    )

    with pytest.raises(ValueError, match="SHA snapshot"):
        copy_vault_no_follow(source, destination)

    assert (source / "paper.md").read_bytes() == b"source bytes"
    assert config.read_bytes() == b'{"vault": "old"}\n'
    assert not destination.exists()


def test_copy_verification_does_not_follow_a_source_swapped_after_manifest(
    tmp_path, monkeypatch
):
    home = tmp_path / "simulated-home"
    source = tmp_path / "outside-simulated-home" / "unsafe-vault"
    destination = home / "copy"
    external = tmp_path / "external-target"
    home.mkdir()
    source.mkdir(parents=True)
    paper = source / "paper.md"
    paper.write_bytes(b"original bytes")
    external.write_bytes(b"original bytes")
    monkeypatch.setattr(vault_mod, "_current_home", lambda: home)
    original_snapshot = vault_mod._snapshot_regular_tree_fd
    source_snapshots = 0

    def swap_after_manifest(root_fd: int, root: Path):
        nonlocal source_snapshots
        result = original_snapshot(root_fd, root)
        if root == source:
            source_snapshots += 1
            if source_snapshots == 1:
                paper.unlink()
                paper.symlink_to(external)
        return result

    monkeypatch.setattr(
        vault_mod,
        "_snapshot_regular_tree_fd",
        swap_after_manifest,
    )
    with pytest.raises(ValueError, match="symlink"):
        copy_vault_no_follow(source, destination)

    assert external.read_bytes() == b"original bytes"
    assert paper.is_symlink()
    assert not destination.exists()


def test_module_imports_only_stdlib_dependencies():
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.vault, sys\n"
        "forbidden = {'flet', 'pydantic', 'attr', 'attrs', 'yaml'}\n"
        "assert not (forbidden & set(sys.modules))\n"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(src), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr
