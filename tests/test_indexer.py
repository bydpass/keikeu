"""Rebuildable v3 Paper index contracts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core import indexer as indexer_mod
from keikeu_core.indexer import (
    list_index_errors,
    list_papers,
    load_index,
    rebuild_index,
    save_index,
)
from keikeu_core.markdown_io import write_paper
from keikeu_core.models import Highlight, Paper
from keikeu_core.vault import init_vault, soft_delete


def _paper(
    code: str,
    summary: str,
    tags: list[str] | None = None,
    *,
    display_name: str | None = None,
    highlight_name: str | None = None,
) -> Paper:
    return Paper(
        code=code,
        initial_summary="",
        summary=summary,
        display_name=display_name,
        highlights=(
            [Highlight(content="private anchor content", display_name=highlight_name)]
            if highlight_name is not None
            else []
        ),
        tags=tags or [],
        created=datetime(2026, 7, 14, 9, 0),
        updated=datetime(2026, 7, 14, 9, 30),
    )


def _fresh_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    init_vault(vault)
    return vault


def test_rebuild_indexes_paper_and_highlight_names_in_a_deterministic_v3_shape(
    tmp_path,
):
    vault = _fresh_vault(tmp_path)
    second = write_paper(vault, _paper("K-20260714-002", "Second summary.", ["two"]))
    first = write_paper(
        vault,
        _paper(
            "K-20260714-001",
            "First summary.",
            ["one", "two"],
            display_name="蓝伞",
            highlight_name="末班车",
        ),
    )

    index = rebuild_index(vault)

    assert index == {
        "version": 3,
        "papers": [
            {
                "code": "K-20260714-001",
                "display_name": "蓝伞",
                "path": str(first.relative_to(vault)),
                "folder": None,
                "summary": "First summary.",
                "tags": ["one", "two"],
                "highlight_names": ["末班车"],
                "created": "2026-07-14T09:00:00",
                "updated": "2026-07-14T09:30:00",
            },
            {
                "code": "K-20260714-002",
                "display_name": None,
                "path": str(second.relative_to(vault)),
                "folder": None,
                "summary": "Second summary.",
                "tags": ["two"],
                "highlight_names": [],
                "created": "2026-07-14T09:00:00",
                "updated": "2026-07-14T09:30:00",
            },
        ],
        "errors": [],
    }
    assert json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8")) == index
    assert list_papers(vault) == index["papers"]
    assert list_index_errors(vault) == []
    assert "private anchor content" not in json.dumps(index, ensure_ascii=False)


def test_rebuild_quarantines_one_broken_paper_and_keeps_other_assets(tmp_path):
    vault = _fresh_vault(tmp_path)
    valid = write_paper(vault, _paper("K-20260714-001", "Keep me."))
    broken = vault / "cache" / "K-20260714-002.md"
    broken_bytes = b"---\ntype: paper\nschema_version: 2\n---\n# broken\n"
    broken.write_bytes(broken_bytes)

    index = rebuild_index(vault)

    assert [entry["path"] for entry in index["papers"]] == [str(valid.relative_to(vault))]
    assert index["errors"] == [
        {"path": "cache/K-20260714-002.md", "reason": "Paper frontmatter is missing code"}
    ]
    assert broken.read_bytes() == broken_bytes


def test_rebuild_treats_v1_or_filename_mismatched_markdown_as_an_error(tmp_path):
    vault = _fresh_vault(tmp_path)
    legacy = vault / "cache" / "old-cache.md"
    legacy.write_text("---\ntype: cache\n---\nlegacy", encoding="utf-8")
    mismatched = write_paper(vault, _paper("K-20260714-001", "Mismatch."))
    mismatched.rename(vault / "cache" / "K-20260714-099.md")

    index = rebuild_index(vault)

    assert index["papers"] == []
    assert [item["path"] for item in index["errors"]] == [
        "cache/K-20260714-099.md",
        "cache/old-cache.md",
    ]
    assert "filename" in index["errors"][0]["reason"]
    assert "type: paper" in index["errors"][1]["reason"]


def test_rebuild_quarantines_a_conflict_copy_without_changing_the_active_paper(tmp_path):
    vault = _fresh_vault(tmp_path)
    active = write_paper(vault, _paper("K-20260714-001", "Active summary."))
    conflict_copy = vault / "cache" / "K-20260714-001 (conflicted copy).md"
    conflict_copy.write_bytes(active.read_bytes())
    active_before = active.read_bytes()
    copy_before = conflict_copy.read_bytes()

    index = rebuild_index(vault)

    assert [entry["code"] for entry in index["papers"]] == ["K-20260714-001"]
    assert index["errors"] == [
        {
            "path": "cache/K-20260714-001 (conflicted copy).md",
            "reason": "Paper filename must match frontmatter code",
        }
    ]
    assert active.read_bytes() == active_before
    assert conflict_copy.read_bytes() == copy_before


def test_rebuild_excludes_trashed_papers_and_syncs_after_external_deletion(tmp_path):
    vault = _fresh_vault(tmp_path)
    first = write_paper(vault, _paper("K-20260714-001", "First."))
    second = write_paper(vault, _paper("K-20260714-002", "Second."))
    soft_delete(vault, "cache/K-20260714-002.md")

    assert [entry["code"] for entry in rebuild_index(vault)["papers"]] == ["K-20260714-001"]
    first.unlink()

    refreshed = rebuild_index(vault)

    assert refreshed == {"version": 3, "papers": [], "errors": []}
    assert (vault / ".trash" / "cache" / second.name).exists()


def test_load_index_rebuilds_missing_or_invalid_metadata_without_touching_papers(tmp_path):
    vault = _fresh_vault(tmp_path)
    paper_path = write_paper(vault, _paper("K-20260714-001", "Keep bytes."))
    original_bytes = paper_path.read_bytes()
    index_path = vault / "keikeu_index.json"

    index_path.unlink()
    assert [entry["code"] for entry in load_index(vault)["papers"]] == ["K-20260714-001"]
    assert paper_path.read_bytes() == original_bytes

    for payload in (
        "not json",
        "[]",
        '{"version": 1, "caches": []}',
        '{"version": 2, "papers": []}',
        '{"version": 3, "papers": []}',
    ):
        index_path.write_text(payload, encoding="utf-8")
        assert [entry["code"] for entry in load_index(vault)["papers"]] == ["K-20260714-001"]
        assert paper_path.read_bytes() == original_bytes


def test_malicious_absolute_index_path_rebuilds_without_outside_access(
    tmp_path, monkeypatch
):
    vault = _fresh_vault(tmp_path)
    paper_path = write_paper(vault, _paper("K-20260714-001", "Safe Paper."))
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside bytes")
    malicious = {
        "version": 3,
        "papers": [
            {
                "code": "K-20260714-999",
                "display_name": None,
                "path": str(outside),
                "folder": None,
                "summary": "Outside",
                "tags": [],
                "highlight_names": [],
                "created": "2026-07-14T09:00:00",
                "updated": "2026-07-14T09:30:00",
            }
        ],
        "errors": [],
    }
    (vault / "keikeu_index.json").write_text(
        json.dumps(malicious),
        encoding="utf-8",
    )
    papers = list_papers(vault)

    assert [entry["path"] for entry in papers] == [
        str(paper_path.relative_to(vault))
    ]
    assert outside.read_bytes() == b"outside bytes"
    stored = json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8"))
    assert stored["papers"] == papers


def test_index_mutations_reject_symlink_index_without_touching_outside(tmp_path):
    vault = _fresh_vault(tmp_path)
    index_path = vault / "keikeu_index.json"
    outside = tmp_path / "outside-index.json"
    outside.write_bytes(b"outside index bytes")
    index_path.unlink()
    index_path.symlink_to(outside)

    for action in (
        lambda: load_index(vault),
        lambda: rebuild_index(vault),
        lambda: save_index(vault, {"version": 3, "papers": [], "errors": []}),
    ):
        with pytest.raises(ValueError, match="symlink"):
            action()

    assert index_path.is_symlink()
    assert outside.read_bytes() == b"outside index bytes"


def test_index_write_rejects_a_symlink_ancestor_without_touching_target(tmp_path):
    real_parent = tmp_path / "real-parent"
    vault = real_parent / "vault"
    init_vault(vault)
    index = vault / "keikeu_index.json"
    before = index.read_bytes()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        save_index(
            linked_parent / "vault",
            {"version": 3, "papers": [], "errors": []},
        )

    assert index.read_bytes() == before


@pytest.mark.parametrize("operation", ["save", "rebuild"])
def test_index_mutation_refuses_a_byte_identical_ordinary_root_replacement(
    tmp_path,
    monkeypatch,
    operation,
):
    vault = _fresh_vault(tmp_path)
    replacement = tmp_path / "replacement-vault"
    parked = tmp_path / "parked-vault"
    paper = write_paper(vault, _paper("K-20260714-001", "same bytes"))
    rebuild_index(vault)
    index_bytes = (vault / "keikeu_index.json").read_bytes()
    paper_bytes = paper.read_bytes()
    shutil.copytree(vault, replacement)
    real_exchange = indexer_mod.atomic_exchange_at_no_follow
    swapped = False

    def replace_root_then_exchange(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            vault.rename(parked)
            replacement.rename(vault)
        return real_exchange(*args, **kwargs)

    monkeypatch.setattr(
        indexer_mod,
        "atomic_exchange_at_no_follow",
        replace_root_then_exchange,
    )
    with pytest.raises(ValueError, match="directory path changed"):
        if operation == "save":
            save_index(vault, {"version": 3, "papers": [], "errors": []})
        else:
            rebuild_index(vault)

    for root in (parked, vault):
        assert (root / "keikeu_index.json").read_bytes() == index_bytes
        assert (root / "cache" / paper.name).read_bytes() == paper_bytes
        assert list(root.glob(".keikeu_index.json.*.tmp")) == []


def test_rebuild_rejects_symlink_paper_without_touching_outside(tmp_path):
    vault = _fresh_vault(tmp_path)
    outside = tmp_path / "outside-paper.md"
    outside.write_bytes(b"outside Paper bytes")
    linked = vault / "cache" / "K-20260714-001.md"
    linked.symlink_to(outside)
    index_before = (vault / "keikeu_index.json").read_bytes()

    with pytest.raises(ValueError, match="symlink"):
        rebuild_index(vault)

    assert linked.is_symlink()
    assert outside.read_bytes() == b"outside Paper bytes"
    assert (vault / "keikeu_index.json").read_bytes() == index_before


def test_module_imports_only_stdlib_dependencies():
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.indexer, sys\n"
        "forbidden = {'flet', 'pydantic', 'attr', 'attrs', 'yaml'}\n"
        "assert not (forbidden & set(sys.modules))\n"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(src), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr
