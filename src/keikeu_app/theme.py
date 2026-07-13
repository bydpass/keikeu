"""Showa stationery and home-computer design tokens for the app layer."""

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

# A late-80s Japanese word processor: khaki case, phosphor-green type,
# oxide-orange keys, and slightly yellowed stationery paper.
BG = "#e5dcc4"
SURFACE = "#fff8e7"
SURFACE_WARM = "#ded0aa"
FG = "#253d34"
MUTED = "#647168"
ACCENT = "#ad5e2f"
ACCENT_ON = "#fff8e7"
BORDER = "#84907c"
BORDER_SOFT = "#c9bea2"
SUCCESS = "#3f745d"
WARN = "#ad7628"
DANGER = "#a94b3f"

# System monospace keeps the interface legible without shipping web fonts.
FONT_DISPLAY = "Courier New"
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

RADIUS_SM = 2
RADIUS_MD = 4
RADIUS_LG = 6
SIDEBAR_WIDTH = 248
CONTENT_MAX_WIDTH = 1180


def build_theme() -> ft.Theme:
    """Build the shared CRT-and-stationery theme without external assets."""
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
                weight=ft.FontWeight.W_700,
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
            bgcolor=FG,
            indicator_color=ACCENT,
            elevation=0,
            min_extended_width=SIDEBAR_WIDTH,
            use_indicator=True,
            selected_label_text_style=ft.TextStyle(
                color=ACCENT_ON,
                size=TEXT_SM,
                weight=ft.FontWeight.W_600,
            ),
            unselected_label_text_style=ft.TextStyle(
                color=SURFACE_WARM,
                size=TEXT_SM,
            ),
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
    """Apply the shared Showa word-processor visual direction."""
    page.theme = build_theme()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG
    page.padding = 0
