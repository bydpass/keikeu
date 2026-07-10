"""Warm paper design tokens and Flet theme for the keikeu app layer."""

from __future__ import annotations

import flet as ft

__all__ = [
    "ACCENT",
    "ACCENT_ON",
    "BG",
    "BORDER",
    "BORDER_SOFT",
    "DANGER",
    "FG",
    "FONT_DISPLAY",
    "MUTED",
    "RADIUS_LG",
    "RADIUS_MD",
    "RADIUS_SM",
    "SIDEBAR_WIDTH",
    "SPACE_1",
    "SPACE_2",
    "SPACE_3",
    "SPACE_4",
    "SPACE_5",
    "SPACE_6",
    "SPACE_8",
    "SPACE_12",
    "SUCCESS",
    "SURFACE",
    "SURFACE_WARM",
    "TEXT_BASE",
    "TEXT_LG",
    "TEXT_SM",
    "TEXT_XL",
    "TEXT_XS",
    "WARN",
    "apply_theme",
    "build_theme",
]

# Storytelling palette from WI-6 and the accepted "inspiration folio" prototype.
BG = "#fbf6ee"
SURFACE = "#fffdf8"
SURFACE_WARM = "#f1e3cf"
FG = "#201914"
MUTED = "#7a6d63"
ACCENT = "#9b5b32"
ACCENT_ON = "#ffffff"
BORDER = "#ded2c3"
BORDER_SOFT = "#eee4d7"
SUCCESS = "#4f8a4f"
WARN = "#c9822f"
DANGER = "#b33a3a"

FONT_DISPLAY = "Georgia"
TEXT_XS = 12
TEXT_SM = 14
TEXT_BASE = 17
TEXT_LG = 20
TEXT_XL = 28

SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32
SPACE_12 = 48

RADIUS_SM = 10
RADIUS_MD = 16
RADIUS_LG = 24
SIDEBAR_WIDTH = 220
CONTENT_MAX_WIDTH = 1180


def build_theme() -> ft.Theme:
    """Build the shared light theme without introducing external assets."""
    return ft.Theme(
        use_material3=True,
        scaffold_bgcolor=BG,
        canvas_color=BG,
        card_bgcolor=SURFACE,
        divider_color=BORDER_SOFT,
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            on_primary=ACCENT_ON,
            primary_container=SURFACE_WARM,
            on_primary_container=FG,
            secondary=SUCCESS,
            on_secondary=ACCENT_ON,
            error=DANGER,
            on_error=ACCENT_ON,
            surface=SURFACE,
            on_surface=FG,
            on_surface_variant=MUTED,
            outline=BORDER,
            outline_variant=BORDER_SOFT,
        ),
        text_theme=ft.TextTheme(
            body_large=ft.TextStyle(size=TEXT_BASE, color=FG, height=1.5),
            body_medium=ft.TextStyle(size=TEXT_SM, color=FG, height=1.5),
            body_small=ft.TextStyle(size=TEXT_XS, color=MUTED, height=1.45),
            title_large=ft.TextStyle(
                size=TEXT_XL,
                color=FG,
                font_family=FONT_DISPLAY,
                weight=ft.FontWeight.W_400,
            ),
            title_medium=ft.TextStyle(
                size=TEXT_LG,
                color=FG,
                font_family=FONT_DISPLAY,
                weight=ft.FontWeight.W_400,
            ),
        ),
        divider_theme=ft.DividerTheme(color=BORDER_SOFT, thickness=1, space=1),
        navigation_rail_theme=ft.NavigationRailTheme(
            bgcolor=SURFACE,
            indicator_color=SURFACE_WARM,
            elevation=0,
            min_extended_width=SIDEBAR_WIDTH,
            use_indicator=True,
            selected_label_text_style=ft.TextStyle(
                color=ACCENT,
                size=TEXT_SM,
                weight=ft.FontWeight.W_600,
            ),
            unselected_label_text_style=ft.TextStyle(color=MUTED, size=TEXT_SM),
        ),
        filled_button_theme=ft.FilledButtonTheme(
            style=ft.ButtonStyle(
                bgcolor=ACCENT,
                color=ACCENT_ON,
                elevation=0,
                padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            )
        ),
        outlined_button_theme=ft.OutlinedButtonTheme(
            style=ft.ButtonStyle(
                color=FG,
                elevation=0,
                padding=ft.Padding.symmetric(horizontal=16, vertical=11),
                side=ft.BorderSide(width=1, color=BORDER),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            )
        ),
        snackbar_theme=ft.SnackBarTheme(
            bgcolor=FG,
            content_text_style=ft.TextStyle(color=ACCENT_ON, size=TEXT_SM),
            elevation=0,
            show_close_icon=True,
            close_icon_color=ACCENT_ON,
        ),
    )


def apply_theme(page: ft.Page) -> None:
    """Apply the accepted Phase 6 visual direction to a page-like object."""
    page.theme = build_theme()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG
    page.padding = 0
