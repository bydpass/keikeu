"""Filesystem contracts for the Paper v2 vault and its recovery bin."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core.markdown_io import read_paper, update_paper, write_paper
from keikeu_core.models import Paper
from keikeu_core.vault import (
    get_vault,
    init_vault,
    is_vault,
    list_trashed_papers,
    restore_paper,
    set_vault,
    soft_delete,
)


def _paper(code: str, summary: str = "A writing-ready summary.") -> Paper:
    return Paper(
        code=code,
        initial_summary="",
        summary=summary,
        highlights=["Keep this beat."],
        tags=["rain"],
        created=datetime(2026, 7, 14, 9, 0),
        updated=datetime(2026, 7, 14, 9, 0),
    )


def test_init_vault_creates_only_the_v2_layout_and_empty_index(tmp_path):
    vault = tmp_path / "vault"

    init_vault(vault)

    assert (vault / "cache").is_dir()
    assert (vault / ".trash" / "cache").is_dir()
    assert not (vault / "outlines").exists()
    assert not (vault / ".trash" / "outlines").exists()
    assert json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8")) == {
        "version": 2,
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


def test_is_vault_requires_only_cache_and_index_not_trash_or_outlines(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    (vault / ".trash" / "cache").rmdir()
    (vault / ".trash").rmdir()

    assert is_vault(vault) is True
    assert is_vault(tmp_path / "missing") is False
    assert is_vault(tmp_path) is False


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
    edited = read_paper(original)
    edited.summary = "Edited current summary."
    edited.updated = datetime(2026, 7, 14, 10, 0)
    update_paper(original, edited)
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


def test_set_then_get_vault_round_trips_and_bad_config_is_safe(tmp_path):
    vault = tmp_path / "vault"
    config = tmp_path / "config" / "keikeu_config.json"
    set_vault(vault, config)
    assert get_vault(config) == vault

    assert get_vault(tmp_path / "missing.json") is None
    for payload in ("not json", '{"vault": 1}', '{"vault": null}', "[]"):
        config.write_text(payload, encoding="utf-8")
        assert get_vault(config) is None


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
