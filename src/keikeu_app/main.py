"""keikeu Flet shell for the Paper v2 macOS flow.

The GUI only routes user actions to public ``keikeu_core`` APIs.  Markdown,
JSON, migration, and asset recovery remain in the pure-Python core layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import flet as ft

from keikeu_app.pages import build_flashcard_page, build_library_page, build_paper_page
from keikeu_app.theme import (
    ACCENT,
    ACCENT_ON,
    BG,
    FG,
    FONT_DISPLAY,
    MUTED,
    RADIUS_SM,
    SIDEBAR_WIDTH,
    SPACE_2,
    SPACE_4,
    SPACE_8,
    SURFACE_WARM,
    TEXT_SM,
    apply_theme,
)
from keikeu_app.widgets import notify, paper_card, primary_button, single_line_field
from keikeu_core.indexer import rebuild_index
from keikeu_core.vault import get_vault, init_vault, is_vault, set_vault

__all__ = ["main", "run", "AppContext", "CONFIG_PATH"]

CONFIG_PATH = Path.home() / ".keikeu_config.json"
INITIAL_WINDOW_WIDTH = 890
INITIAL_WINDOW_HEIGHT = 741

_NAV_PAPER = 0
_NAV_FLASHCARD = 1
_NAV_LIBRARY = 2


@dataclass
class AppContext:
    """The active vault and page-navigation callbacks shared by GUI builders."""

    page: ft.Page
    vault: Path
    state_path: Path | None = None
    open_paper: Callable[[Path | None], None] = field(default=lambda _path: None)
    open_flashcards: Callable[[str | None], None] = field(default=lambda _code: None)
    open_library: Callable[[], None] = field(default=lambda: None)


def _configure_window(page: ft.Page) -> None:
    page.window.width = INITIAL_WINDOW_WIDTH
    page.window.height = INITIAL_WINDOW_HEIGHT


def _build_shell(page: ft.Page, vault: Path) -> None:
    """Build the Paper / Flashcard / Library navigation shell."""
    apply_theme(page)
    page.controls.clear()
    page.scroll = None
    body = ft.Container(expand=True, padding=SPACE_8, bgcolor=BG)
    ctx = AppContext(page=page, vault=vault)

    def show_paper(open_path: Path | None = None) -> None:
        try:
            nav.selected_index = _NAV_PAPER
            body.content = build_paper_page(ctx, open_path)
            page.update()
        except Exception as ex:
            notify(page, f"无法打开 Paper：{ex}")

    def show_flashcards(code: str | None = None) -> None:
        try:
            nav.selected_index = _NAV_FLASHCARD
            body.content = build_flashcard_page(ctx, code)
            page.update()
        except Exception as ex:
            notify(page, f"无法打开 Flashcard：{ex}")

    def show_library() -> None:
        try:
            nav.selected_index = _NAV_LIBRARY
            body.content = build_library_page(ctx)
            page.update()
        except Exception as ex:
            notify(page, f"无法打开本地文件库：{ex}")

    ctx.open_paper = show_paper
    ctx.open_flashcards = show_flashcards
    ctx.open_library = show_library

    def on_nav_change(e: ft.ControlEvent) -> None:
        if e.control.selected_index == _NAV_PAPER:
            show_paper()
        elif e.control.selected_index == _NAV_FLASHCARD:
            show_flashcards()
        else:
            show_library()

    nav = ft.NavigationRail(
        selected_index=_NAV_PAPER,
        extended=True,
        min_width=72,
        min_extended_width=SIDEBAR_WIDTH,
        bgcolor=FG,
        indicator_color=ACCENT,
        use_indicator=True,
        elevation=0,
        leading=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "K",
                        color=ACCENT_ON,
                        size=18,
                        font_family=FONT_DISPLAY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=34,
                    height=34,
                    bgcolor=ACCENT,
                    border_radius=RADIUS_SM,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text("KEIKEU", size=22, color=ACCENT_ON, font_family=FONT_DISPLAY, weight=ft.FontWeight.W_700),
                ft.Text("PERSONAL PAPER DESK", size=10, color=SURFACE_WARM, font_family=FONT_DISPLAY),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_2,
        ),
        trailing=ft.Text(
            "LOCAL PAPER UNIT\nV0.2 · OFFLINE READY",
            size=TEXT_SM,
            color=SURFACE_WARM,
            text_align=ft.TextAlign.CENTER,
        ),
        pin_trailing_to_bottom=True,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.EDIT_NOTE, label="纸片"),
            ft.NavigationRailDestination(icon=ft.Icons.STYLE, label="Flashcard"),
            ft.NavigationRailDestination(icon=ft.Icons.FOLDER_OUTLINED, label="本地文件库"),
        ],
        on_change=on_nav_change,
    )
    page.add(
        ft.Row(
            controls=[nav, ft.VerticalDivider(width=3, color=ACCENT), body],
            expand=True,
        )
    )
    show_paper()


def _build_vault_picker(page: ft.Page) -> None:
    """Offer a minimal local folder picker when no valid vault is configured."""
    apply_theme(page)
    page.controls.clear()
    page.scroll = ft.ScrollMode.AUTO
    existing = get_vault(CONFIG_PATH)
    path_field = single_line_field("Vault 文件夹路径", str(existing) if existing is not None else "")
    path_field.hint_text = str(Path.home() / "keikeu-vault")
    path_field.expand = True
    error_text = ft.Text("", color=ft.Colors.ERROR)

    def on_open(_: ft.ControlEvent) -> None:
        raw = (path_field.value or "").strip()
        if not raw:
            error_text.value = "请输入文件夹路径。"
            page.update()
            return
        vault = Path(raw).expanduser()
        try:
            init_vault(vault)
            set_vault(vault, CONFIG_PATH)
            rebuild_index(vault)
        except (OSError, ValueError) as ex:
            error_text.value = f"无法打开 Vault：{ex}"
            page.update()
            return
        if not is_vault(vault):
            error_text.value = "该路径未能创建为有效 Vault。"
            page.update()
            return
        notify(page, "Vault 已就绪")
        _build_shell(page, vault)

    page.add(
        ft.Container(
            padding=SPACE_8,
            bgcolor=BG,
            expand=True,
            content=paper_card(
                controls=[
                    ft.Text("打开或创建 Vault", size=28, color=FG, font_family=FONT_DISPLAY, weight=ft.FontWeight.W_400),
                    ft.Text("Vault 保存你的 Paper Markdown；索引可随时从 Paper 重建。", color=MUTED),
                    path_field,
                    primary_button("创建 / 打开 Vault", on_open),
                    error_text,
                ],
                key="vault-picker-paper-card",
                spacing=SPACE_4,
            ),
        )
    )


def main(page: ft.Page) -> None:
    """Flet view builder: show the selected v2 vault or the local picker."""
    page.title = "keikeu"
    _configure_window(page)
    apply_theme(page)
    vault = get_vault(CONFIG_PATH)
    if vault is not None and is_vault(vault):
        _build_shell(page, vault)
    else:
        _build_vault_picker(page)


def run() -> None:
    """No-argument console entry point."""
    ft.run(main)


if __name__ == "__main__":
    run()
