"""Paper v2 model contracts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from keikeu_core.models import Paper, validate_paper_code


def test_paper_normalizes_optional_lists_without_rewriting_author_content():
    paper = Paper(
        code="K-20260714-001",
        initial_summary="first saved wording",
        summary="current wording",
        highlights=["first anchor", "", "  "],
        tags=["  train  ", "train", "Train", "", "  "],
        legacy_title="Old Cache title",
    )

    assert paper.highlights == ["first anchor", "  "]
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

    first.highlights.append("anchor")
    first.tags.append("tag")
    assert second.highlights == []
    assert second.tags == []


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
