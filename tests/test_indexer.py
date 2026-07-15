"""Rebuildable v2 Paper index contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from keikeu_core.indexer import (
    list_index_errors,
    list_papers,
    load_index,
    rebuild_index,
)
from keikeu_core.markdown_io import write_paper
from keikeu_core.models import Paper
from keikeu_core.vault import init_vault, soft_delete


def _paper(code: str, summary: str, tags: list[str] | None = None) -> Paper:
    return Paper(
        code=code,
        initial_summary="",
        summary=summary,
        highlights=[],
        tags=tags or [],
        created=datetime(2026, 7, 14, 9, 0),
        updated=datetime(2026, 7, 14, 9, 30),
    )


def _fresh_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    init_vault(vault)
    return vault


def test_rebuild_indexes_only_papers_in_a_deterministic_v2_shape(tmp_path):
    vault = _fresh_vault(tmp_path)
    second = write_paper(vault, _paper("K-20260714-002", "Second summary.", ["two"]))
    first = write_paper(vault, _paper("K-20260714-001", "First summary.", ["one", "two"]))

    index = rebuild_index(vault)

    assert index == {
        "version": 2,
        "papers": [
            {
                "code": "K-20260714-001",
                "path": str(first.relative_to(vault)),
                "summary": "First summary.",
                "tags": ["one", "two"],
                "created": "2026-07-14T09:00:00",
                "updated": "2026-07-14T09:30:00",
            },
            {
                "code": "K-20260714-002",
                "path": str(second.relative_to(vault)),
                "summary": "Second summary.",
                "tags": ["two"],
                "created": "2026-07-14T09:00:00",
                "updated": "2026-07-14T09:30:00",
            },
        ],
        "errors": [],
    }
    assert json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8")) == index
    assert list_papers(vault) == index["papers"]
    assert list_index_errors(vault) == []


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


def test_rebuild_excludes_trashed_papers_and_syncs_after_external_deletion(tmp_path):
    vault = _fresh_vault(tmp_path)
    first = write_paper(vault, _paper("K-20260714-001", "First."))
    second = write_paper(vault, _paper("K-20260714-002", "Second."))
    soft_delete(vault, "cache/K-20260714-002.md")

    assert [entry["code"] for entry in rebuild_index(vault)["papers"]] == ["K-20260714-001"]
    first.unlink()

    refreshed = rebuild_index(vault)

    assert refreshed == {"version": 2, "papers": [], "errors": []}
    assert (vault / ".trash" / "cache" / second.name).exists()


def test_load_index_rebuilds_missing_or_invalid_metadata_without_touching_papers(tmp_path):
    vault = _fresh_vault(tmp_path)
    paper_path = write_paper(vault, _paper("K-20260714-001", "Keep bytes."))
    original_bytes = paper_path.read_bytes()
    index_path = vault / "keikeu_index.json"

    index_path.unlink()
    assert [entry["code"] for entry in load_index(vault)["papers"]] == ["K-20260714-001"]
    assert paper_path.read_bytes() == original_bytes

    for payload in ("not json", "[]", '{"version": 1, "caches": []}', '{"version": 2, "papers": []}'):
        index_path.write_text(payload, encoding="utf-8")
        assert [entry["code"] for entry in load_index(vault)["papers"]] == ["K-20260714-001"]
        assert paper_path.read_bytes() == original_bytes


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
