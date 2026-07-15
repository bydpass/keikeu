"""Paper v2 Markdown read/write contracts."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core.markdown_io import (
    next_paper_code,
    read_paper,
    rename_paper,
    update_paper,
    write_paper,
)
from keikeu_core.models import Paper


def test_paper_complete_cjk_and_multiline_round_trip(tmp_path):
    created = datetime(2026, 7, 14, 9, 30)
    paper = Paper(
        code="K-20260714-001",
        initial_summary="not persisted before the first save",
        summary="深夜的末班公交上，两个人隔着一个空位假装睡着。\nA 明早离开。",
        highlights=["旧打火机被塞回手里。\n谁也没有解释。", "", "公交驶过平时下车的站。"],
        tags=["  末班车 ", "离别", "末班车", "离别 ", "暧昧"],
        created=created,
        updated=created,
        legacy_title="旧 Cache 标题",
    )

    path = write_paper(tmp_path, paper)
    back = read_paper(path)
    assert back.initial_summary == paper.summary
    assert back.summary == paper.summary
    assert back.highlights == ["旧打火机被塞回手里。\n谁也没有解释。", "公交驶过平时下车的站。"]
    assert back.tags == ["末班车", "离别", "暧昧"]
    assert back.legacy_title == "旧 Cache 标题"


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
    edited.summary = "new current summary"
    edited.initial_summary = "attempted rewrite"
    edited.legacy_title = "attempted rewrite"
    update_paper(path, edited)

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
        update_paper(path, edited)
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


def test_explicit_rename_preserves_content_without_overwrite(tmp_path):
    source = write_paper(
        tmp_path,
        Paper(
            code="K-20260714-001",
            initial_summary="",
            summary="first summary",
            highlights=["anchor"],
            tags=["tag"],
        ),
    )
    before = source.read_bytes()
    write_paper(
        tmp_path, Paper(code="K-20260714-002", initial_summary="", summary="occupied")
    )
    with pytest.raises(FileExistsError):
        rename_paper(tmp_path, "K-20260714-001", "K-20260714-002")
    assert source.read_bytes() == before

    target = rename_paper(tmp_path, "K-20260714-001", "K-20260714-003")
    back = read_paper(target)
    assert not source.exists()
    assert back.code == "K-20260714-003"
    assert back.initial_summary == "first summary"
    assert back.highlights == ["anchor"]


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
