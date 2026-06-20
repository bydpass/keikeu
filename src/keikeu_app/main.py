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
from keikeu_app.widgets import notify
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
    page.controls.clear()
    # NavigationRail requires a bounded height. Page-level scrolling makes the
    # shell's Row vertically unbounded, so scrolling lives inside each page body.
    page.scroll = None

    body = ft.Container(expand=True, padding=16)
    ctx = AppContext(page=page, vault=vault)

    def show_cache(open_path: Path | None = None) -> None:
        try:
            nav.selected_index = _NAV_CACHE
            body.content = build_cache_page(ctx, open_path)
            page.update()
        except Exception as ex:
            notify(page, f"Could not open cache: {ex}")

    def show_outline(open_path: Path | None = None) -> None:
        try:
            nav.selected_index = _NAV_OUTLINE
            body.content = build_outline_editor_page(ctx, open_path)
            page.update()
        except Exception as ex:
            notify(page, f"Could not open outline: {ex}")

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
            notify(page, f"Could not start outline: {ex}")

    def show_library() -> None:
        try:
            nav.selected_index = _NAV_LIBRARY
            body.content = build_library_page(ctx)
            page.update()
        except Exception as ex:
            notify(page, f"Could not open library: {ex}")

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
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.NOTE_ADD, label="Cache"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ARTICLE, label="Outline"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.LIST, label="Library"
            ),
        ],
        on_change=on_nav_change,
    )

    page.add(
        ft.Row(
            controls=[
                nav,
                ft.VerticalDivider(width=1),
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
    page.controls.clear()
    page.scroll = ft.ScrollMode.AUTO

    default = ""
    existing = get_vault(CONFIG_PATH)
    if existing is not None:
        default = str(existing)

    path_field = ft.TextField(
        label="Vault folder path",
        value=default,
        hint_text=str(Path.home() / "keikeu-vault"),
        expand=True,
    )
    error_text = ft.Text("", color=ft.Colors.ERROR)

    def on_open(_: ft.ControlEvent) -> None:
        raw = (path_field.value or "").strip()
        if not raw:
            error_text.value = "Enter a folder path."
            page.update()
            return
        vault = Path(raw).expanduser()
        try:
            init_vault(vault)  # idempotent; never clobbers existing data
            set_vault(vault, CONFIG_PATH)
            rebuild_index(vault)
        except (OSError, ValueError) as ex:
            error_text.value = f"Could not open vault: {ex}"
            page.update()
            return
        if not is_vault(vault):
            error_text.value = "Path did not become a valid vault."
            page.update()
            return
        notify(page, "Vault ready")
        _build_shell(page, vault)

    page.add(
        ft.Column(
            controls=[
                ft.Text("Open or create a vault", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "A vault is a folder holding your caches and outlines.",
                    color=ft.Colors.OUTLINE,
                ),
                path_field,
                ft.Button(content=ft.Text("Create / Open vault"), on_click=on_open),
                error_text,
            ],
        )
    )


def main(page: ft.Page) -> None:
    """Flet view builder. Resolves the vault, then shows shell or picker."""
    page.title = "keikeu"

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
