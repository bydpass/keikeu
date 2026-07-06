"""Library page: browse caches and outlines, search, filter, and open one.

GUI layer only. Listing comes from ``keikeu_core.indexer`` (``list_caches`` /
``list_outlines``), which reads the rebuildable index derived from the user's
Markdown. This module never parses Markdown or JSON itself; it only filters the
flat entry dicts and routes a click back to the right editor page.

No cloud, login, AI, database, or graph view (out of scope before MVP).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.widgets import notify
from keikeu_core.indexer import list_caches, list_outlines, rebuild_index
from keikeu_core.models import CacheStatus
from keikeu_core.vault import soft_delete

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_library_page"]

_ALL = "all"


def build_library_page(ctx: "AppContext") -> ft.Control:
    """Build the library browser with a title search and a status filter."""
    page = ctx.page

    search_field = ft.TextField(label="Search title", expand=True)
    status_dd = ft.Dropdown(
        label="Cache status",
        value=_ALL,
        options=[ft.dropdown.Option(_ALL)]
        + [ft.dropdown.Option(s.value) for s in CacheStatus],
        width=200,
    )

    results = ft.Column(controls=[], scroll=ft.ScrollMode.AUTO, expand=True)

    def _open_cache(rel_path: str) -> None:
        ctx.open_cache(ctx.vault / rel_path)

    def _open_outline(rel_path: str) -> None:
        ctx.open_outline(ctx.vault / rel_path)

    def _row(entry: dict, kind: str) -> ft.Control:
        title = entry.get("title") or "(untitled)"
        subtitle_bits = [kind]
        if kind == "cache":
            subtitle_bits.append(entry.get("status", ""))
        else:
            subtitle_bits.append(entry.get("ending_type", ""))
        subtitle_bits.append(entry.get("updated", ""))
        rel_path = entry["path"]

        def on_open(_: ft.ControlEvent, rp: str = rel_path, k: str = kind) -> None:
            if k == "cache":
                _open_cache(rp)
            else:
                _open_outline(rp)

        def on_delete(_: ft.ControlEvent, rp: str = rel_path) -> None:
            try:
                soft_delete(ctx.vault, rp)
                rebuild_index(ctx.vault)
                notify(page, "已移入回收站")
                refresh(None)
            except Exception as ex:
                notify(page, f"Could not delete item: {ex}")

        return ft.ListTile(
            title=ft.Text(title),
            subtitle=ft.Text("  ·  ".join(b for b in subtitle_bits if b)),
            leading=ft.Icon(
                ft.Icons.NOTE if kind == "cache" else ft.Icons.ARTICLE
            ),
            trailing=ft.OutlinedButton(content=ft.Text("Delete"), on_click=on_delete),
            on_click=on_open,
        )

    def refresh(_: ft.ControlEvent | None = None) -> None:
        query = (search_field.value or "").strip().lower()
        status_filter = status_dd.value or _ALL

        results.controls.clear()

        caches = list_caches(ctx.vault)
        outlines = list_outlines(ctx.vault)

        def matches_title(entry: dict) -> bool:
            return query in (entry.get("title") or "").lower()

        cache_rows = [
            _row(e, "cache")
            for e in caches
            if matches_title(e)
            and (status_filter == _ALL or e.get("status") == status_filter)
        ]
        # The status filter is cache-specific; when a concrete status is
        # selected, outlines (which have no status) are hidden.
        outline_rows = (
            [_row(e, "outline") for e in outlines if matches_title(e)]
            if status_filter == _ALL
            else []
        )

        results.controls.append(
            ft.Text(f"Caches ({len(cache_rows)})", weight=ft.FontWeight.BOLD)
        )
        results.controls.extend(cache_rows or [ft.Text("  (none)")])
        results.controls.append(ft.Divider())
        results.controls.append(
            ft.Text(f"Outlines ({len(outline_rows)})", weight=ft.FontWeight.BOLD)
        )
        results.controls.extend(outline_rows or [ft.Text("  (none)")])
        page.update()

    # TextField fires on_change; Dropdown (Flet 0.85) fires on_select.
    search_field.on_change = refresh
    status_dd.on_select = refresh

    refresh(None)

    return ft.Column(
        controls=[
            ft.Text("Library", size=20, weight=ft.FontWeight.BOLD),
            ft.Row(controls=[search_field, status_dd]),
            ft.OutlinedButton(
                content=ft.Text("Refresh"),
                icon=ft.Icons.REFRESH,
                on_click=refresh,
            ),
            ft.Divider(),
            results,
        ],
        expand=True,
    )
