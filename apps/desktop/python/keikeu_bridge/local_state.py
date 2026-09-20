"""Disposable per-device state shared by desktop presentation adapters."""

from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import tempfile

from keikeu_core.vault import require_home_path

__all__ = [
    "STATE_PATH",
    "claim_daily_card",
    "load_last_daily_card_date",
]


STATE_PATH = Path.home() / ".keikeu_state.json"


def _resolve_path(state_path: Path | None) -> Path:
    return require_home_path(STATE_PATH if state_path is None else state_path)


def _read_last_daily_card_date(state_path: Path) -> date | None:
    """Return one valid stored local date; malformed state is empty state."""
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    raw_date = payload.get("last_daily_card_date")
    if not isinstance(raw_date, str):
        return None
    try:
        return date.fromisoformat(raw_date)
    except ValueError:
        return None


def _write_last_daily_card_date(local_date: date, state_path: Path) -> None:
    """Atomically replace the disposable state file without touching a Vault."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{state_path.name}.",
        suffix=".tmp",
        dir=state_path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {"last_daily_card_date": local_date.isoformat()},
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
        os.replace(temporary_path, state_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_last_daily_card_date(state_path: Path | None = None) -> date | None:
    """Read the last claimed daily-card date from device-local state."""
    return _read_last_daily_card_date(_resolve_path(state_path))


def claim_daily_card(
    local_date: date | None = None,
    state_path: Path | None = None,
) -> bool:
    """Atomically claim today's built-in start card for this device."""
    claimed_date = date.today() if local_date is None else local_date
    if type(claimed_date) is not date:
        raise ValueError("local_date must be a date")
    path = _resolve_path(state_path)
    if _read_last_daily_card_date(path) == claimed_date:
        return False
    _write_last_daily_card_date(claimed_date, path)
    return True
