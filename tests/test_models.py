"""Paper v3 model contracts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from keikeu_core.models import Highlight, Paper, validate_display_name, validate_paper_code


def test_paper_normalizes_optional_lists_without_rewriting_author_content():
    paper = Paper(
        code="K-20260714-001",
        initial_summary="first saved wording",
        summary="current wording",
        display_name="  夜行列车 🌙  ",
        highlights=[
            Highlight(content="first anchor", display_name="  车窗  "),
            Highlight(content="", display_name="删除我"),
            Highlight(content="  "),
        ],
        tags=["  train  ", "train", "Train", "", "  "],
        legacy_title="Old Cache title",
    )

    assert paper.display_name == "夜行列车 🌙"
    assert paper.highlights == [Highlight(content="first anchor", display_name="车窗")]
    assert paper.tags == ["train", "Train"]
    assert paper.legacy_title == "Old Cache title"


@pytest.mark.parametrize(
    "code",
    ["K-20260714-000", "K-20261314-001", "k-20260714-001", "paper-001"],
)
def test_paper_rejects_invalid_codes(code):
    with pytest.raises(ValueError, match="code"):
        Paper(code=code, initial_summary="first", summary="current")


@pytest.mark.parametrize("summary", ["", "   ", "\n\t"])
def test_paper_rejects_blank_summary(summary):
    with pytest.raises(ValueError, match="summary"):
        Paper(code="K-20260714-001", initial_summary="first", summary=summary)


def test_paper_list_defaults_are_independent():
    first = Paper(code="K-20260714-001", initial_summary="a", summary="a")
    second = Paper(code="K-20260714-002", initial_summary="b", summary="b")

    first.highlights.append(Highlight(content="anchor"))
    first.tags.append("tag")
    assert second.highlights == []
    assert second.tags == []


def test_display_names_allow_unicode_duplicates_and_exact_200_code_points():
    name = "雪" * 199 + "🌙"
    paper = Paper(
        code="K-20260714-001",
        initial_summary="first",
        summary="current",
        display_name=f"  {name}  ",
        highlights=[
            Highlight(content="one", display_name="重复"),
            Highlight(content="two", display_name="重复"),
        ],
    )

    assert paper.display_name == name
    assert [item.display_name for item in paper.highlights] == ["重复", "重复"]


@pytest.mark.parametrize("value", ["x" * 201, "line\nbreak", "tab\tname", "line\u2028break"])
def test_display_names_reject_overlength_or_multiline_control_text(value):
    with pytest.raises(ValueError, match="display_name"):
        validate_display_name(value)


def test_blank_names_become_none_and_blank_highlight_content_drops_the_whole_item():
    paper = Paper(
        code="K-20260714-001",
        initial_summary="first",
        summary="current",
        display_name="  ",
        highlights=[
            Highlight(content=" \n ", display_name="named but empty"),
            Highlight(content="kept\ncontent", display_name="  "),
        ],
    )

    assert paper.display_name is None
    assert paper.highlights == [Highlight(content="kept\ncontent")]


def test_paper_rejects_legacy_string_highlights():
    with pytest.raises(ValueError, match="Highlight"):
        Paper(
            code="K-20260714-001",
            initial_summary="first",
            summary="current",
            highlights=["legacy string"],  # type: ignore[list-item]
        )


def test_validate_paper_code_returns_the_canonical_value():
    assert validate_paper_code("K-20260714-001") == "K-20260714-001"


def test_active_model_imports_no_gui_or_third_party_packages():
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.models, sys\n"
        "forbidden = {'flet', 'pydantic', 'attr', 'attrs', 'yaml'}\n"
        "assert not (forbidden & set(sys.modules))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join([str(src), os.environ.get("PYTHONPATH", "")] )},
    )
    assert result.returncode == 0, result.stderr
