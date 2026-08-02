"""Additive Paper v4 model contracts."""

from __future__ import annotations

from datetime import datetime

import pytest

from keikeu_core.models import CardPageV4, PaperV4


def make_paper(**overrides) -> PaperV4:
    values = {
        "code": "K-20260802-001",
        "pages": [CardPageV4(content="一条真实灵感")],
        "created": datetime(2026, 8, 2, 10, 0),
        "updated": datetime(2026, 8, 2, 10, 30),
    }
    values.update(overrides)
    return PaperV4(**values)


def test_paper_v4_normalizes_names_tags_and_preserves_page_content():
    paper = make_paper(
        display_name="  夜行列车 🌙  ",
        pages=[
            CardPageV4(name="  车窗  ", content="  正文首尾空格不变  ", type="summary"),
            CardPageV4(name="只有标题", content="", type="snapshot"),
        ],
        tags=["  夜车  ", "夜车", "夜车,重逢", "", "  "],
    )

    assert paper.display_name == "夜行列车 🌙"
    assert paper.pages[0].name == "车窗"
    assert paper.pages[0].content == "  正文首尾空格不变  "
    assert paper.tags == ["夜车", "夜车,重逢"]


def test_paper_v4_requires_at_least_one_saved_page():
    with pytest.raises(ValueError, match="at least one"):
        make_paper(pages=[])


@pytest.mark.parametrize("content", ["", " ", "\n\t"])
def test_page_v4_requires_a_name_or_non_whitespace_content(content):
    with pytest.raises(ValueError, match="non-empty name or content"):
        CardPageV4(content=content)


def test_named_page_may_have_empty_or_whitespace_content_without_rewriting_it():
    empty = CardPageV4(name="标题", content="")
    whitespace = CardPageV4(name="标题", content=" \n\t")

    assert empty.content == ""
    assert whitespace.content == " \n\t"


@pytest.mark.parametrize("page_type", [None, "summary", "snapshot", "whisper"])
def test_page_v4_accepts_only_the_locked_type_values(page_type):
    assert CardPageV4(content="text", type=page_type).type == page_type


@pytest.mark.parametrize("page_type", ["highlight", "总结", "", 1, []])
def test_page_v4_rejects_unknown_type_values(page_type):
    with pytest.raises(ValueError, match="page type"):
        CardPageV4(content="text", type=page_type)  # type: ignore[arg-type]


def test_paper_v4_allows_only_one_summary_but_unlimited_other_types():
    with pytest.raises(ValueError, match="at most one summary"):
        make_paper(
            pages=[
                CardPageV4(content="one", type="summary"),
                CardPageV4(content="two", type="summary"),
            ]
        )

    paper = make_paper(
        pages=[
            CardPageV4(content="one", type="snapshot"),
            CardPageV4(content="two", type="snapshot"),
            CardPageV4(content="three", type="whisper"),
        ]
    )
    assert len(paper.pages) == 3


def test_v4_names_count_unicode_code_points_and_do_not_normalize():
    exact = "雪" * 199 + "🌙"
    decomposed = "e\u0301"

    paper = make_paper(
        display_name=exact,
        pages=[CardPageV4(name=decomposed, content="text")],
    )

    assert len(paper.display_name or "") == 200
    assert paper.pages[0].name == decomposed
    with pytest.raises(ValueError, match="200 Unicode code points"):
        make_paper(display_name=exact + "x")


@pytest.mark.parametrize("value", ["line\nbreak", "tab\tname", "x\u2028y", "\ud800"])
def test_v4_names_reject_control_surrogate_and_line_separator_values(value):
    with pytest.raises(ValueError, match="control characters"):
        CardPageV4(name=value, content="text")


@pytest.mark.parametrize("tag", ["line\nbreak", "tab\tvalue", "x\u2029y", "\ud800"])
def test_v4_tags_reject_control_surrogate_and_line_separator_values(tag):
    with pytest.raises(ValueError, match="single-line"):
        make_paper(tags=[tag])


def test_paper_v4_mutable_defaults_are_independent():
    first = make_paper()
    second = make_paper(code="K-20260802-002")

    first.tags.append("tag")
    first.pages.append(CardPageV4(content="second"))

    assert second.tags == []
    assert len(second.pages) == 1


def test_paper_v4_rejects_wrong_container_and_metadata_types():
    with pytest.raises(ValueError, match="CardPageV4"):
        make_paper(pages=["text"])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="datetime"):
        make_paper(created="2026-08-02")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="map strings"):
        make_paper(extra_frontmatter={"source": 1})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="trimmed"):
        make_paper(extra_frontmatter={" source ": "value"})
    with pytest.raises(ValueError, match="reserved key"):
        make_paper(extra_frontmatter={"type": "other"})
