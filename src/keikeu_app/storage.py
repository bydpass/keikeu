"""Paths for durable, app-private Flet data."""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["app_data_path"]


def app_data_path() -> Path:
    """Return Flet's durable storage directory, or the user home for direct runs."""
    storage = os.environ.get("FLET_APP_STORAGE_DATA")
    return Path(storage) if storage else Path.home()
