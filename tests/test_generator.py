import pytest

from keikeu.generator import generate_spec
from keikeu.models import KeikeuSpec


def test_empty_input_raises():
    with pytest.raises(ValueError):
        generate_spec("")


def test_whitespace_only_raises():
    with pytest.raises(ValueError):
        generate_spec("   \n\t  ")


def test_non_empty_returns_spec_with_minimums():
    spec = generate_spec("A 和 B 曾是一对 CP，某天 B 变成一只小虫。")
    assert isinstance(spec, KeikeuSpec)
    assert spec.raw_idea == "A 和 B 曾是一对 CP，某天 B 变成一只小虫。"
    assert "同人" in spec.tags
    assert len(spec.vinegar) >= 3
    assert len(spec.dumplings) >= 3
    assert len(spec.next_steps) >= 3


def test_raw_idea_preserved_verbatim():
    raw = "   多余空白测试   "
    spec = generate_spec(raw)
    assert spec.raw_idea == raw


def test_au_keyword_adds_next_step():
    spec = generate_spec("ABO 设定下 A 是 alpha，B 是 omega，想看初遇。")
    assert any("AU" in step for step in spec.next_steps)
