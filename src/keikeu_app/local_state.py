"""Disposable per-device UI state for the Flashcard page.

This module deliberately lives in the app layer: Paper Markdown remains the
source of truth, while this small JSON file only remembers where one macOS
device last stopped reading.  A missing or unreadable state file is treated as
an empty state, never as a problem with a user's Paper.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

__all__ = [
    "STATE_PATH",
    "get_card_index",
    "load_card_positions",
    "move_card_position",
    "set_card_index",
]


STATE_PATH = Path.home() / ".keikeu_state.json"
_STATE_VERSION = 1


def _resolve_path(state_path: Path | None) -> Path:
    return STATE_PATH if state_path is None else state_path


def _require_code(code: str) -> str:
    if not isinstance(code, str) or not code:
        raise ValueError("paper code must be a non-empty string")
    return code


def _require_card_count(card_count: int) -> int:
    if isinstance(card_count, bool) or not isinstance(card_count, int) or card_count < 1:
        raise ValueError("card_count must be a positive integer")
    return card_count


def _read_card_positions(state_path: Path) -> dict[str, int]:
    """Read valid stored positions, treating every malformed shape as empty."""
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("version") != _STATE_VERSION:
        return {}
    raw_positions = payload.get("card_positions")
    if not isinstance(raw_positions, dict):
        return {}
    return {
        code: index
        for code, index in raw_positions.items()
        if isinstance(code, str)
        and isinstance(index, int)
        and not isinstance(index, bool)
        and index >= 0
    }


def _write_card_positions(positions: dict[str, int], state_path: Path) -> None:
    """Atomically replace the disposable state file without touching any vault."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{state_path.name}.", suffix=".tmp", dir=state_path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {"version": _STATE_VERSION, "card_positions": positions},
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
        os.replace(temporary_path, state_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_card_positions(state_path: Path | None = None) -> dict[str, int]:
    """Return a copy of valid positions from the selected device-local file."""
    return _read_card_positions(_resolve_path(state_path))


def get_card_index(code: str, card_count: int, state_path: Path | None = None) -> int:
    """Return this Paper's valid current card, clamping a stale position.

    A removed Highlight can make a previously stored index out of range.  In
    that case the clamped last-card position is persisted so it stays valid if
    Highlights are later added again.
    """
    code = _require_code(code)
    card_count = _require_card_count(card_count)
    path = _resolve_path(state_path)
    positions = _read_card_positions(path)
    stored = positions.get(code, 0)
    index = min(stored, card_count - 1)
    if code in positions and positions[code] != index:
        positions[code] = index
        _write_card_positions(positions, path)
    return index


def set_card_index(
    code: str, card_index: int, card_count: int, state_path: Path | None = None
) -> int:
    """Store a valid card position and return its clamped value."""
    code = _require_code(code)
    card_count = _require_card_count(card_count)
    if isinstance(card_index, bool) or not isinstance(card_index, int):
        raise ValueError("card_index must be an integer")
    index = min(max(card_index, 0), card_count - 1)
    path = _resolve_path(state_path)
    positions = _read_card_positions(path)
    positions[code] = index
    _write_card_positions(positions, path)
    return index


def move_card_position(
    old_code: str, new_code: str, state_path: Path | None = None
) -> None:
    """Move a remembered position after a successful explicit Paper rename."""
    old_code = _require_code(old_code)
    new_code = _require_code(new_code)
    if old_code == new_code:
        return
    path = _resolve_path(state_path)
    positions = _read_card_positions(path)
    if old_code not in positions:
        return
    positions[new_code] = positions.pop(old_code)
    _write_card_positions(positions, path)
