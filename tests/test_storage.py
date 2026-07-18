"""Contracts for Flet's durable application-data path."""

from __future__ import annotations

from keikeu_app.storage import app_data_path


def test_app_data_path_prefers_flet_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))

    assert app_data_path() == tmp_path
