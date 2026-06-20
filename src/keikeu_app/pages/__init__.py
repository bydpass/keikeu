"""Flet pages for the keikeu GUI shell.

Each page is a builder function that takes the shared application context
(active vault path + navigation/open callbacks) and returns a Flet control.
All data logic is delegated to ``keikeu_core``; pages never serialize.
"""

from __future__ import annotations

from keikeu_app.pages.cache_page import build_cache_page
from keikeu_app.pages.library_page import build_library_page
from keikeu_app.pages.outline_editor_page import build_outline_editor_page

__all__ = [
    "build_cache_page",
    "build_library_page",
    "build_outline_editor_page",
]
