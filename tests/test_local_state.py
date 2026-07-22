"""Contracts for disposable per-device daily-card state."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from keikeu_app.local_state import (
    claim_daily_card,
    load_last_daily_card_date,
)


_TODAY = date(2026, 7, 22)


def test_missing_state_claims_today_before_display(tmp_path):
    state_path = tmp_path / "device-state.json"

    assert claim_daily_card(_TODAY, state_path) is True
    assert load_last_daily_card_date(state_path) == _TODAY
    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "last_daily_card_date": "2026-07-22",
    }


def test_same_day_is_claimed_only_once(tmp_path):
    state_path = tmp_path / "device-state.json"
    assert claim_daily_card(_TODAY, state_path) is True
    original_bytes = state_path.read_bytes()

    assert claim_daily_card(_TODAY, state_path) is False
    assert state_path.read_bytes() == original_bytes


def test_next_local_day_claims_again(tmp_path):
    state_path = tmp_path / "device-state.json"
    claim_daily_card(_TODAY, state_path)
    tomorrow = _TODAY + timedelta(days=1)

    assert claim_daily_card(tomorrow, state_path) is True
    assert load_last_daily_card_date(state_path) == tomorrow


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"last_daily_card_date": "not-a-date"}',
        '{"version": 1, "card_positions": {"K-OLD": 2}}',
    ],
)
def test_corrupt_or_legacy_state_is_empty_and_replaced(tmp_path, content):
    state_path = tmp_path / "device-state.json"
    state_path.write_text(content, encoding="utf-8")

    assert load_last_daily_card_date(state_path) is None
    assert claim_daily_card(_TODAY, state_path) is True
    assert load_last_daily_card_date(state_path) == _TODAY
    assert "card_positions" not in state_path.read_text(encoding="utf-8")


def test_state_path_outside_current_home_is_rejected():
    outside = Path("/private/tmp/keikeu-device-state.json")

    with pytest.raises(ValueError, match="outside current user Home"):
        claim_daily_card(_TODAY, outside)
