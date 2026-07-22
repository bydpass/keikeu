"""Shared test isolation for device-local state."""

from __future__ import annotations

import pytest

from keikeu_app import main as app_main
from keikeu_app.local_state import claim_daily_card


@pytest.fixture(autouse=True)
def isolate_claimed_daily_state(tmp_path, monkeypatch):
    """Keep startup tests off real device state and past today's start card."""
    state_path = tmp_path / "claimed-device-state.json"
    claim_daily_card(state_path=state_path)
    monkeypatch.setattr(app_main, "DEVICE_STATE_PATH", state_path)
