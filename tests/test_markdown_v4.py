"""Strict additive Paper v4 Markdown codec contracts."""

from __future__ import annotations

from datetime import datetime

import pytest

from keikeu_core.markdown_io import parse_paper_v4_bytes, render_paper_v4_bytes
from keikeu_core.models import CardPageV4, PaperV4


def make_paper(**overrides) -> PaperV4:
    values = {
        "code": "K-20260802-001",
        "pages": [CardPageV4(content="月光穿过夜行列车的车窗。", type="summary")],
        "created": datetime(2026, 8, 2, 10, 0),
        "updated": datetime(2026, 8, 2, 10, 30),
    }
    values.update(overrides)
    return PaperV4(**values)


def test_paper_v4_golden_bytes_and_unknown_frontmatter_order():
    paper = make_paper(
        display_name="夜车上的约定",
        pages=[
            CardPageV4(
                content=(
                    "月光穿过夜行列车的车窗。\n"
                    "<!-- /keikeu:page -->\n"
                    '\\<!-- keikeu:page {"name":null,"type":null} -->'
                ),
                type="summary",
            ),
            CardPageV4(name="橘-子", content="", type="snapshot"),
        ],
        tags=["夜车", "重逢,旧友"],
        legacy_title="旧标题",
        extra_frontmatter={"source": "hand\\made\nline", "mood": "quiet:blue"},
    )

    expected = (
        "---\n"
        "type: paper\n"
        "schema_version: 4\n"
        "code: K-20260802-001\n"
        "created: 2026-08-02T10:00:00\n"
        "updated: 2026-08-02T10:30:00\n"
        "display_name: 夜车上的约定\n"
        "legacy_title: 旧标题\n"
        "source: hand\\\\made\\nline\n"
        "mood: quiet:blue\n"
        "---\n"
        "# K-20260802-001\n\n"
        '<!-- keikeu:page {"name":null,"type":"summary"} -->\n'
        "月光穿过夜行列车的车窗。\n"
        "\\<!-- /keikeu:page -->\n"
        '\\\\<!-- keikeu:page {"name":null,"type":null} -->\n'
        "<!-- /keikeu:page -->\n\n"
        '<!-- keikeu:page {"name":"橘\\u002d子","type":"snapshot"} -->\n'
        "<!-- /keikeu:page -->\n\n"
        "## Tags\n\n"
        "- 夜车\n"
        "- 重逢,旧友\n"
    ).encode("utf-8")

    assert render_paper_v4_bytes(paper) == expected
    assert parse_paper_v4_bytes(expected) == paper
    assert list(parse_paper_v4_bytes(expected).extra_frontmatter) == ["source", "mood"]


@pytest.mark.parametrize(
    "content",
    [
        "plain",
        "\nleading and trailing\n",
        "<!-- /keikeu:page -->",
        "\\<!-- /keikeu:page -->",
        "\\\\<!-- /keikeu:page -->",
        '<!-- keikeu:page {"name":null,"type":null} -->',
        '\\<!-- keikeu:page {"name":null,"type":null} -->',
    ],
)
def test_paper_v4_content_marker_escape_round_trips_any_leading_slashes(content):
    paper = make_paper(pages=[CardPageV4(name="页", content=content)])

    rendered = render_paper_v4_bytes(paper)
    parsed = parse_paper_v4_bytes(rendered)

    assert parsed.pages[0].content == content
    assert render_paper_v4_bytes(parsed) == rendered


def test_paper_v4_named_empty_page_and_empty_tags_are_canonical():
    paper = make_paper(pages=[CardPageV4(name="只有标题", content="")], tags=[])
    rendered = render_paper_v4_bytes(paper)

    assert b'<!-- keikeu:page {"name":"\xe5\x8f\xaa\xe6\x9c\x89\xe6\xa0\x87\xe9\xa2\x98","type":null} -->\n<!-- /keikeu:page -->' in rendered
    assert rendered.endswith(b"\n\n## Tags\n")
    assert parse_paper_v4_bytes(rendered) == paper
    assert parse_paper_v4_bytes(rendered[:-1]) == paper


def test_paper_v4_parser_accepts_consistent_crlf_and_rejects_mixed_or_bare_cr():
    rendered = render_paper_v4_bytes(make_paper())
    crlf = rendered.replace(b"\n", b"\r\n")

    assert parse_paper_v4_bytes(crlf) == make_paper()
    with pytest.raises(ValueError, match="mix LF and CRLF"):
        parse_paper_v4_bytes(crlf.replace(b"\r\n", b"\n", 1))
    with pytest.raises(ValueError, match="bare CR"):
        parse_paper_v4_bytes(rendered.replace(b"\n", b"\r", 1))


def test_paper_v4_parser_rejects_bom_invalid_utf8_and_non_bytes():
    rendered = render_paper_v4_bytes(make_paper())

    with pytest.raises(ValueError, match="BOM"):
        parse_paper_v4_bytes(b"\xef\xbb\xbf" + rendered)
    with pytest.raises(ValueError, match="valid UTF-8"):
        parse_paper_v4_bytes(b"\xff")
    with pytest.raises(TypeError, match="must be bytes"):
        parse_paper_v4_bytes("text")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (b"code: K-20260802-001\n", b"code: K-20260802-001\ncode: K-20260802-001\n", "repeats key"),
        (b"updated: 2026-08-02T10:30:00\n", b"", "missing updated"),
        (b"schema_version: 4", b"schema_version: 3", "schema_version: 4"),
        (b"# K-20260802-001", b"# K-20260802-002", "heading"),
    ],
)
def test_paper_v4_parser_rejects_invalid_frontmatter_or_identity(old, new, message):
    rendered = render_paper_v4_bytes(make_paper())

    with pytest.raises(ValueError, match=message):
        parse_paper_v4_bytes(rendered.replace(old, new, 1))


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ('{"name":null,"name":null,"type":null}', "repeats JSON key"),
        ('{"name":null,"type":null,"extra":1}', "only name and type"),
        ('{"name":1,"type":null}', "name must be"),
        ('{"name":null,"type":"highlight"}', "invalid type"),
        ('{"name":null,"type":[]}', "invalid type"),
        ('{"name":"a--b","type":null}', "raw '--'"),
        ('not-json', "invalid JSON"),
    ],
)
def test_paper_v4_parser_rejects_invalid_page_marker_json(payload, message):
    rendered = render_paper_v4_bytes(make_paper())
    start = b'<!-- keikeu:page {"name":null,"type":"summary"} -->'
    replacement = f"<!-- keikeu:page {payload} -->".encode()

    with pytest.raises(ValueError, match=message):
        parse_paper_v4_bytes(rendered.replace(start, replacement, 1))


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (b"# K-20260802-001\n\n", b"# K-20260802-001\n\n\n", "page block"),
        (b"\n\n## Tags", b"\nstray\n\n## Tags", "separated by one blank"),
        (b"## Tags\n", b"## Tags\n\n", "empty Tags"),
        (b"## Tags\n", b"## Tags\n\n* wrong\n", "non-empty '- value'"),
    ],
)
def test_paper_v4_parser_rejects_noncanonical_outer_structure(old, new, message):
    rendered = render_paper_v4_bytes(make_paper())

    with pytest.raises(ValueError, match=message):
        parse_paper_v4_bytes(rendered.replace(old, new, 1))


def test_paper_v4_parser_normalizes_tags_and_renderer_canonicalizes_once():
    rendered = render_paper_v4_bytes(make_paper(tags=["夜车", "重逢,旧友"]))
    noncanonical = rendered.replace(
        b"- \xe5\xa4\x9c\xe8\xbd\xa6\n- \xe9\x87\x8d\xe9\x80\xa2,\xe6\x97\xa7\xe5\x8f\x8b\n",
        b"-  \xe5\xa4\x9c\xe8\xbd\xa6  \n- \xe5\xa4\x9c\xe8\xbd\xa6\n- \xe9\x87\x8d\xe9\x80\xa2,\xe6\x97\xa7\xe5\x8f\x8b\n",
    )

    parsed = parse_paper_v4_bytes(noncanonical)

    assert parsed.tags == ["夜车", "重逢,旧友"]
    assert render_paper_v4_bytes(parsed) == rendered


def test_paper_v4_renderer_rejects_reserved_or_noncanonical_extra_keys():
    with pytest.raises(ValueError, match="reserved key"):
        make_paper(extra_frontmatter={"type": "other"})
    with pytest.raises(ValueError, match="trimmed"):
        make_paper(extra_frontmatter={" source ": "value"})
    with pytest.raises(ValueError, match="key"):
        make_paper(extra_frontmatter={"bad\nkey": "value"})


def test_paper_v4_parse_render_parse_preserves_all_author_fields():
    papers = [
        make_paper(),
        make_paper(
            display_name="",
            pages=[
                CardPageV4(name="一", content="\n正文\n", type="whisper"),
                CardPageV4(name=None, content="# Markdown\n\n- list", type="snapshot"),
            ],
            tags=["a", "A", "逗号,是内容"],
            extra_frontmatter={"empty": "", "colon": "a:b", "slash": "a\\b"},
        ),
    ]

    for paper in papers:
        rendered = render_paper_v4_bytes(paper)
        parsed = parse_paper_v4_bytes(rendered)
        assert parsed == paper
        assert parse_paper_v4_bytes(render_paper_v4_bytes(parsed)) == parsed


def test_active_v3_codec_does_not_accept_v4_or_change_its_public_names():
    from keikeu_core.markdown_io import parse_paper_bytes, render_paper_bytes

    with pytest.raises(ValueError, match="schema_version: 2 or 3"):
        parse_paper_bytes(render_paper_v4_bytes(make_paper()))
    assert parse_paper_bytes.__name__ == "parse_paper_bytes"
    assert render_paper_bytes.__name__ == "render_paper_bytes"
