"""Contracts for disposable per-device Flashcard state."""

from __future__ import annotations

from keikeu_app.local_state import (
    get_card_index,
    load_card_positions,
    move_card_position,
    set_card_index,
)


_CODE = "K-20260714-001"


def test_missing_or_corrupt_state_starts_from_summary(tmp_path):
    state_path = tmp_path / "device-state.json"

    assert get_card_index(_CODE, 3, state_path) == 0
    state_path.write_text("not json", encoding="utf-8")
    assert get_card_index(_CODE, 3, state_path) == 0


def test_card_position_survives_reload_and_clamps_after_highlights_shrink(tmp_path):
    state_path = tmp_path / "device-state.json"
    set_card_index(_CODE, 3, 4, state_path)

    assert get_card_index(_CODE, 4, state_path) == 3
    assert get_card_index(_CODE, 2, state_path) == 1
    assert load_card_positions(state_path) == {_CODE: 1}


def test_position_moves_to_the_new_code_on_rename(tmp_path):
    state_path = tmp_path / "device-state.json"
    replacement = "K-20260714-002"
    set_card_index(_CODE, 2, 4, state_path)
    set_card_index(replacement, 0, 4, state_path)

    move_card_position(_CODE, replacement, state_path)

    assert load_card_positions(state_path) == {replacement: 2}


def test_deleting_state_only_resets_the_view(tmp_path):
    state_path = tmp_path / "device-state.json"
    set_card_index(_CODE, 1, 3, state_path)
    state_path.unlink()

    assert get_card_index(_CODE, 3, state_path) == 0
    assert not state_path.exists()
