"""Small shared GUI helpers for the keikeu Flet layer.

GUI-only. These helpers never touch Markdown / JSON / serialization; all data
logic stays in ``keikeu_core``. They exist purely so the three pages share one
way to build labelled multiline fields and to flash a transient message.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from keikeu_app.theme import (
    ACCENT,
    ACCENT_ON,
    BORDER,
    BORDER_SOFT,
    DANGER,
    FG,
    FONT_DISPLAY,
    MUTED,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SUCCESS,
    SURFACE,
    SURFACE_WARM,
    TEXT_BASE,
    TEXT_SM,
    TEXT_XL,
    TEXT_XS,
)

__all__ = [
    "danger_button",
    "notify",
    "page_header",
    "paper_card",
    "primary_button",
    "section_field",
    "single_line_field",
    "status_badge",
]


def _field_style() -> dict[str, object]:
    """Return the shared warm-paper TextField styling."""
    return {
        "bgcolor": SURFACE,
        "border_color": BORDER,
        "focused_border_color": ACCENT,
        "border_radius": RADIUS_SM,
        "border_width": 1,
        "focused_border_width": 1,
        "color": FG,
        "text_size": TEXT_BASE,
        "label_style": ft.TextStyle(size=TEXT_SM, color=FG),
        "hint_style": ft.TextStyle(size=TEXT_SM, color=MUTED),
        "content_padding": ft.Padding.symmetric(horizontal=SPACE_4, vertical=SPACE_3),
    }


def single_line_field(label: str, value: str = "") -> ft.TextField:
    """A plain one-line labelled text field."""
    return ft.TextField(label=label, value=value, **_field_style())


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
        **_field_style(),
    )


def page_header(title: str, subtitle: str, eyebrow: str) -> ft.Control:
    """Build the compact editorial header shared by all three pages."""
    return ft.Column(
        controls=[
            ft.Text(
                eyebrow.upper(),
                size=TEXT_XS,
                color=ACCENT,
                weight=ft.FontWeight.W_600,
            ),
            ft.Text(
                title,
                size=TEXT_XL,
                color=FG,
                font_family=FONT_DISPLAY,
                weight=ft.FontWeight.W_400,
            ),
            ft.Text(subtitle, size=TEXT_SM, color=MUTED),
        ],
        spacing=SPACE_2,
    )


def paper_card(
    controls: list[ft.Control],
    *,
    key: str,
    spacing: int = SPACE_4,
    expand: bool = False,
) -> ft.Container:
    """Wrap related controls in a flat bordered paper surface."""
    return ft.Container(
        key=key,
        content=ft.Column(controls=controls, spacing=spacing),
        padding=SPACE_6,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER_SOFT),
        border_radius=RADIUS_MD,
        expand=expand,
    )


def status_badge(text: str | ft.Text, tone: str = "meta") -> ft.Container:
    """Build a quiet read-only status ticket."""
    palette = {
        "meta": (SURFACE_WARM, MUTED),
        "success": ("#edf4ea", SUCCESS),
        "danger": ("#f8e9e6", DANGER),
    }
    bgcolor, color = palette.get(tone, palette["meta"])
    content = text if isinstance(text, ft.Text) else ft.Text(text)
    content.size = TEXT_XS
    content.color = color
    content.weight = ft.FontWeight.W_600
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        padding=ft.Padding.symmetric(horizontal=SPACE_3, vertical=6),
        border_radius=999,
    )


def primary_button(text: str, on_click: Callable[..., object]) -> ft.Button:
    """Build the single high-emphasis action used on each page."""
    return ft.Button(
        content=ft.Text(text),
        on_click=on_click,
        bgcolor=ACCENT,
        color=ACCENT_ON,
        elevation=0,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADIUS_SM)),
    )


def danger_button(text: str, on_click: Callable[..., object]) -> ft.OutlinedButton:
    """Build a low-emphasis destructive action."""
    return ft.OutlinedButton(
        content=ft.Text(text),
        on_click=on_click,
        style=ft.ButtonStyle(
            color=DANGER,
            side=ft.BorderSide(width=1, color=BORDER),
            shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
        ),
    )


def notify(page: ft.Page, message: str) -> None:
    """Flash a transient snackbar message on ``page``.

    Pure UI feedback (e.g. "Saved"). Flet 0.85 shows a snackbar by attaching it
    to ``page.overlay`` and toggling ``open``.
    """
    bar = ft.SnackBar(content=ft.Text(message), bgcolor=FG)
    page.overlay.append(bar)
    bar.open = True
    page.update()
