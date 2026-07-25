"""Compatibility import until Flet is retired after Gate A."""

from keikeu_bridge.local_state import (
    STATE_PATH,
    claim_daily_card,
    load_last_daily_card_date,
)

__all__ = ["STATE_PATH", "claim_daily_card", "load_last_daily_card_date"]
