"""keikeu Flet GUI shell (appdesign.md Step 6).

This is the only layer allowed to import Flet. All data logic — Markdown,
JSON, serialization, the index — lives in ``keikeu_core`` and is reached only
through its public functions. This module wires three pages together and
resolves the active vault.

Config is an APP-layer concern: it lives at ``~/.keikeu_config.json``. The core
``vault`` functions take that path injected, so core never hardcodes a config
location.

Entry points:
    ``main(page)`` — the Flet view builder (``flet run src/keikeu_app/main.py``).
    ``run()``      — no-arg console entry: ``ft.app(target=main)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import flet as ft

from keikeu_app.pages import (
    build_cache_page,
    build_library_page,
    build_outline_editor_page,
)
from keikeu_app.theme import (
    ACCENT,
    ACCENT_ON,
    BG,
    FG,
    FONT_DISPLAY,
    MUTED,
    SIDEBAR_WIDTH,
    SPACE_2,
    SPACE_4,
    SPACE_8,
    SURFACE,
    SURFACE_WARM,
    TEXT_SM,
    apply_theme,
)
from keikeu_app.widgets import (
    notify,
    paper_card,
    primary_button,
    single_line_field,
)
from keikeu_core.indexer import rebuild_index
from keikeu_core.models import Outline
from keikeu_core.vault import get_vault, init_vault, is_vault, set_vault

__all__ = ["main", "run", "AppContext", "CONFIG_PATH"]

# App-layer config location (NOT decided by core).
CONFIG_PATH = Path.home() / ".keikeu_config.json"

# Navigation slots.
_NAV_CACHE = 0
_NAV_OUTLINE = 1
_NAV_LIBRARY = 2


@dataclass
class AppContext:
    """Shared state + callbacks handed to each page.

    Pages call back through here to navigate or open a specific file in its
    editor. ``vault`` is the resolved, validated active vault directory.
    """

    page: ft.Page
    vault: Path
    open_cache: Callable[[Path | None], None] = field(default=lambda _p: None)
    open_outline: Callable[[Path | None], None] = field(default=lambda _p: None)
    start_outline_from_cache: Callable[[Outline, Path], None] = field(
        default=lambda _outline, _cache_path: None
    )
    open_library: Callable[[], None] = field(default=lambda: None)


def _build_shell(page: ft.Page, vault: Path) -> None:
    """Build the navigation shell once a valid vault is active."""
    apply_theme(page)
    page.controls.clear()
    # NavigationRail requires a bounded height. Page-level scrolling makes the
    # shell's Row vertically unbounded, so scrolling lives inside each page body.
    page.scroll = None

    body = ft.Container(expand=True, padding=SPACE_8, bgcolor=BG)
    ctx = AppContext(page=page, vault=vault)

    def show_cache(open_path: Path | None = None) -> None:
        try:
            nav.selected_index = _NAV_CACHE
            body.content = build_cache_page(ctx, open_path)
            page.update()
        except Exception as ex:
            notify(page, f"无法打开灵感：{ex}")

    def show_outline(open_path: Path | None = None) -> None:
        try:
            nav.selected_index = _NAV_OUTLINE
            body.content = build_outline_editor_page(ctx, open_path)
            page.update()
        except Exception as ex:
            notify(page, f"无法打开大纲：{ex}")

    def start_outline_from_cache(outline: Outline, cache_path: Path) -> None:
        try:
            nav.selected_index = _NAV_OUTLINE
            body.content = build_outline_editor_page(
                ctx,
                None,
                initial_outline=outline,
                source_cache_path=cache_path,
            )
            page.update()
        except Exception as ex:
            notify(page, f"无法开始配方票：{ex}")

    def show_library() -> None:
        try:
            nav.selected_index = _NAV_LIBRARY
            body.content = build_library_page(ctx)
            page.update()
        except Exception as ex:
            notify(page, f"无法打开本地文件库：{ex}")

    ctx.open_cache = show_cache
    ctx.open_outline = show_outline
    ctx.start_outline_from_cache = start_outline_from_cache
    ctx.open_library = show_library

    def on_nav_change(e: ft.ControlEvent) -> None:
        idx = e.control.selected_index
        if idx == _NAV_CACHE:
            show_cache(None)
        elif idx == _NAV_OUTLINE:
            show_outline(None)
        else:
            show_library()

    nav = ft.NavigationRail(
        selected_index=_NAV_CACHE,
        extended=True,
        min_width=72,
        min_extended_width=SIDEBAR_WIDTH,
        bgcolor=SURFACE,
        indicator_color=SURFACE_WARM,
        use_indicator=True,
        elevation=0,
        leading=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "k",
                        color=ACCENT_ON,
                        size=18,
                        font_family=FONT_DISPLAY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=34,
                    height=34,
                    bgcolor=ACCENT,
                    border_radius=17,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    "keikeu",
                    size=20,
                    color=FG,
                    font_family=FONT_DISPLAY,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_2,
        ),
        trailing=ft.Text(
            "存住一瞬的灵光\nv0.1 · 本地优先",
            size=TEXT_SM,
            color=MUTED,
            text_align=ft.TextAlign.CENTER,
        ),
        pin_trailing_to_bottom=True,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.EDIT_NOTE, label="灵感缓存"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DESCRIPTION_OUTLINED, label="配方票编辑"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.FOLDER_OUTLINED, label="本地文件库"
            ),
        ],
        on_change=on_nav_change,
    )

    page.add(
        ft.Row(
            controls=[
                nav,
                ft.VerticalDivider(width=1, color=SURFACE_WARM),
                body,
            ],
            expand=True,
        )
    )

    # Land on a fresh capture — the 3-minute path starts here.
    show_cache(None)


def _build_vault_picker(page: ft.Page) -> None:
    """Show a minimal vault picker when no valid vault is configured.

    A text path field + "Create / Open vault" button: calls ``init_vault``
    (idempotent, non-destructive) then ``set_vault`` to record it, then enters
    the shell. A text path is the accepted MVP fallback (Flet 0.85's directory
    FilePicker uses a different async event model not needed here).
    """
    apply_theme(page)
    page.controls.clear()
    page.scroll = ft.ScrollMode.AUTO

    default = ""
    existing = get_vault(CONFIG_PATH)
    if existing is not None:
        default = str(existing)

    path_field = single_line_field("Vault 文件夹路径", default)
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
            init_vault(vault)  # idempotent; never clobbers existing data
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
                ft.Text(
                    "打开或创建 Vault",
                    size=28,
                    color=FG,
                    font_family=FONT_DISPLAY,
                    weight=ft.FontWeight.W_400,
                ),
                ft.Text(
                    "Vault 是保存灵感缓存与本地 Markdown 大纲的文件夹。",
                    color=MUTED,
                ),
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
    """Flet view builder. Resolves the vault, then shows shell or picker."""
    page.title = "keikeu"
    apply_theme(page)

    vault = get_vault(CONFIG_PATH)
    if vault is not None and is_vault(vault):
        _build_shell(page, vault)
    else:
        _build_vault_picker(page)


def run() -> None:
    """No-arg console entry point: launch the Flet app."""
    ft.run(main)


if __name__ == "__main__":
    run()
