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
from keikeu_app.pages.migration_page import build_migration_page
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
from keikeu_core.migration_v01 import is_v01_vault
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
    if not page.platform.is_desktop():
        return
    page.window.width = INITIAL_WINDOW_WIDTH
    page.window.height = INITIAL_WINDOW_HEIGHT


def _build_shell(page: ft.Page, vault: Path) -> None:
    """Build the Paper / Flashcard / Library navigation shell."""
    apply_theme(page)
    page.controls.clear()
    page.scroll = None
    is_desktop = page.platform.is_desktop()
    body = ft.Container(
        expand=True,
        padding=SPACE_8 if is_desktop else SPACE_4,
        bgcolor=BG,
    )
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

    if is_desktop:
        nav: ft.NavigationRail | ft.NavigationBar = ft.NavigationRail(
            selected_index=_NAV_PAPER,
            extended=True,
            min_width=72,
            min_extended_width=SIDEBAR_WIDTH,
            bgcolor=FG,
            indicator_color=ACCENT,
            use_indicator=True,
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
        page.navigation_bar = None
        page.add(
            ft.Row(
                controls=[nav, ft.VerticalDivider(width=3, color=ACCENT), body],
                expand=True,
            )
        )
    else:
        nav = ft.NavigationBar(
            selected_index=_NAV_PAPER,
            indicator_color=ACCENT,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.EDIT_NOTE, label="纸片"),
                ft.NavigationBarDestination(icon=ft.Icons.STYLE, label="Flashcard"),
                ft.NavigationBarDestination(icon=ft.Icons.FOLDER_OUTLINED, label="本地文件库"),
            ],
            on_change=on_nav_change,
        )
        page.navigation_bar = nav
        page.add(
            ft.SafeArea(
                content=body,
                avoid_intrusions_bottom=False,
                expand=True,
            )
        )
    show_paper()


def _build_migration_gate(page: ft.Page, vault: Path) -> None:
    """Show a no-write v0.1 preflight before allowing any v2 vault action."""
    apply_theme(page)
    page.controls.clear()
    page.scroll = None

    def open_migrated(_: object) -> None:
        set_vault(vault, CONFIG_PATH)
        _build_shell(page, vault)

    page.add(
        ft.Container(
            expand=True,
            padding=SPACE_8,
            bgcolor=BG,
            content=build_migration_page(
                page,
                vault,
                on_open_migrated=open_migrated,
                on_choose_other=lambda: _build_vault_picker(page, show_configured=False),
            ),
        )
    )


def _build_vault_picker(page: ft.Page, *, show_configured: bool = True) -> None:
    """Offer a system folder chooser with a path-entry fallback."""
    apply_theme(page)
    page.controls.clear()
    page.scroll = ft.ScrollMode.AUTO
    is_desktop = page.platform.is_desktop()
    existing = get_vault(CONFIG_PATH) if show_configured else None
    path_field = single_line_field("Vault 文件夹路径", str(existing) if existing is not None else "")
    path_field.hint_text = str(Path.home() / "keikeu-vault")
    path_field.expand = is_desktop
    error_text = ft.Text("", color=ft.Colors.ERROR)
    directory_picker = ft.FilePicker(key="vault-directory-picker")
    page.services.append(directory_picker)

    def open_vault(raw: str) -> None:
        raw = raw.strip()
        if not raw:
            error_text.value = "请输入文件夹路径。"
            page.update()
            return
        vault = Path(raw).expanduser()
        if is_v01_vault(vault):
            _build_migration_gate(page, vault)
            return
        try:
            if is_vault(vault):
                rebuild_index(vault)
            elif vault.exists() and any(vault.iterdir()):
                raise ValueError("该文件夹不是可用 Vault；请选择空文件夹或现有 Paper Vault")
            else:
                init_vault(vault)
                rebuild_index(vault)
            set_vault(vault, CONFIG_PATH)
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

    def on_open(_: ft.ControlEvent) -> None:
        open_vault(path_field.value or "")

    async def on_choose_directory(_: ft.ControlEvent) -> None:
        try:
            selected = await directory_picker.get_directory_path(
                dialog_title="选择 Vault 文件夹",
                initial_directory=str(existing or Path.home()),
            )
        except (OSError, ValueError) as ex:
            error_text.value = f"系统目录选择器不可用：{ex}；可改为手工输入路径。"
            page.update()
            return
        if selected is None:
            error_text.value = "未选择文件夹；可继续手工输入完整路径。"
            page.update()
            return
        path_field.value = selected
        open_vault(selected)

    page.add(
        ft.Container(
            padding=SPACE_8,
            bgcolor=BG,
            expand=is_desktop,
            content=paper_card(
                controls=[
                    ft.Text("打开或创建 Vault", size=28, color=FG, font_family=FONT_DISPLAY, weight=ft.FontWeight.W_400),
                    ft.Text("Vault 保存你的 Paper Markdown；索引可随时从 Paper 重建。", color=MUTED),
                    ft.OutlinedButton(
                        content=ft.Text("从系统选择文件夹"),
                        on_click=on_choose_directory,
                        key="vault-directory-chooser",
                    ),
                    ft.Text("系统选择器不可用或取消时，可手工输入完整路径。", color=MUTED),
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
    if vault is not None and is_v01_vault(vault):
        _build_migration_gate(page, vault)
    elif vault is not None and is_vault(vault):
        _build_shell(page, vault)
    else:
        _build_vault_picker(page)


def run() -> None:
    """No-argument console entry point."""
    ft.run(main)


if __name__ == "__main__":
    run()
