import pytest

from keikeu.generator import make_ticket
from keikeu.models import Ticket


def test_empty_input_raises():
    with pytest.raises(ValueError):
        make_ticket("")


def test_whitespace_only_raises():
    with pytest.raises(ValueError):
        make_ticket("   \n\t  ")


def test_non_empty_returns_ticket_with_minimums():
    ticket = make_ticket("A 和 B 曾是一对 CP，某天 B 变成一只小虫。")
    assert isinstance(ticket, Ticket)
    assert ticket.raw == "A 和 B 曾是一对 CP，某天 B 变成一只小虫。"
    assert "同人" in ticket.tags
    assert len(ticket.jiaozi_cu) >= 3
    assert len(ticket.jiaozi) >= 3
    assert len(ticket.next_step) >= 3


def test_raw_preserved_verbatim():
    raw = "   多余空白测试   "
    ticket = make_ticket(raw)
    assert ticket.raw == raw


def test_au_keyword_adds_next_step():
    ticket = make_ticket("ABO 设定下 A 是 alpha，B 是 omega，想看初遇。")
    assert any("AU" in step for step in ticket.next_step)
