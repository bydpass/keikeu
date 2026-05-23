from keikeu.generator import generate_spec
from keikeu.renderers import render_brief, render_card, render_sop


SAMPLE = "A/B CP，某日 B 变成一只小虫。A 必须找到办法让 B 变回来，最想看到那个瞬间。"


def test_sop_contains_required_header():
    spec = generate_spec(SAMPLE)
    out = render_sop(spec)
    assert "# 饼胚 SOP" in out


def test_brief_contains_required_header():
    spec = generate_spec(SAMPLE)
    out = render_brief(spec)
    assert "# 约文 Brief" in out


def test_card_contains_required_header():
    spec = generate_spec(SAMPLE)
    out = render_card(spec)
    assert "# 灵感名片" in out


def test_sop_preserves_raw_idea():
    spec = generate_spec(SAMPLE)
    out = render_sop(spec)
    assert SAMPLE in out
