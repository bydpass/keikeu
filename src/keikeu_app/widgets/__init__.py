"""Small shared GUI helpers for the keikeu Flet layer.

GUI-only. These helpers never touch Markdown / JSON / serialization; all data
logic stays in ``keikeu_core``. They exist purely so the three pages share one
way to build labelled multiline fields and to flash a transient message.
"""

from __future__ import annotations

import flet as ft

__all__ = ["section_field", "single_line_field", "notify"]


def single_line_field(label: str, value: str = "") -> ft.TextField:
    """A plain one-line labelled text field."""
    return ft.TextField(label=label, value=value)


def section_field(
    label: str, value: str = "", min_lines: int = 3, max_lines: int = 12
) -> ft.TextField:
    """A labelled multiline text field for free-text prose.

    Used for the verbatim spark, notes, summary, plot, etc. The body text is
    handed to ``keikeu_core`` untouched; this widget does no transformation.
    """
    return ft.TextField(
        label=label,
        value=value,
        multiline=True,
        min_lines=min_lines,
        max_lines=max_lines,
    )


def notify(page: ft.Page, message: str) -> None:
    """Flash a transient snackbar message on ``page``.

    Pure UI feedback (e.g. "Saved"). Flet 0.85 shows a snackbar by attaching it
    to ``page.overlay`` and toggling ``open``.
    """
    bar = ft.SnackBar(content=ft.Text(message))
    page.overlay.append(bar)
    bar.open = True
    page.update()
