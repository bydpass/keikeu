"""Flet pages for the keikeu GUI shell.

Each page is a builder function that takes the shared application context
(active vault path + navigation/open callbacks) and returns a Flet control.
All data logic is delegated to ``keikeu_core``; pages never serialize.
"""

from __future__ import annotations

from keikeu_app.pages.flashcard_page import build_flashcard_page
from keikeu_app.pages.library_page import build_library_page
from keikeu_app.pages.paper_page import build_paper_page

__all__ = [
    "build_flashcard_page",
    "build_paper_page",
    "build_library_page",
]
