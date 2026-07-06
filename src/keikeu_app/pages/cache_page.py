"""Cache page: capture, edit, save, convert, and archive an inspiration cache.

GUI layer only. Every read/write goes through ``keikeu_core``:
``markdown_io`` for cache/outline files, ``indexer`` for the metadata index.
This module never builds Markdown or JSON by hand.

A cache is captured with low friction and its ``raw`` spark is preserved
verbatim (product invariant 1) — the page hands the field value straight to
``Cache`` and never summarizes it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.widgets import notify, section_field, single_line_field
from keikeu_core.indexer import rebuild_index
from keikeu_core.markdown_io import (
    read_cache,
    update_cache,
    write_cache,
)
from keikeu_core.models import Cache, CacheStatus, Outline
from keikeu_core.vault import soft_delete

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_cache_page"]

_STATUS_LABELS = {
    CacheStatus.RAW: "raw — 刚存，未处理",
    CacheStatus.DRAFTING: "drafting — 已开始转配方票",
    CacheStatus.OUTLINED: "outlined — 已生成大纲",
    CacheStatus.ARCHIVED: "archived — 封存",
}


def _status_label(status: CacheStatus) -> str:
    """Return the read-only cache status badge text."""
    return _STATUS_LABELS[status]


def build_cache_page(ctx: "AppContext", open_path: Path | None = None) -> ft.Control:
    """Build the cache editor.

    ``open_path`` is the cache Markdown file being edited, or ``None`` for a
    fresh capture. The page tracks the open path so Save dispatches to
    ``write_cache`` (new) or ``update_cache`` (existing).
    """
    page = ctx.page

    # Mutable per-page state, kept on a tiny holder so nested handlers can
    # reassign the tracked path after a first save.
    state: dict[str, object] = {
        "path": open_path,
        "created": datetime.now(),
        "linked_outline": None,
        "status": CacheStatus.RAW,
    }

    title_field = single_line_field("Title", "")
    raw_field = section_field("原始灵感 (raw)", "", min_lines=4, max_lines=16)
    notes_field = section_field("临时备注 (notes)", "", min_lines=2, max_lines=8)
    status_badge = ft.Text(_status_label(CacheStatus.RAW), size=12)

    if open_path is not None:
        existing = read_cache(open_path)
        title_field.value = existing.title
        raw_field.value = existing.raw
        notes_field.value = existing.notes
        state["created"] = existing.created
        state["linked_outline"] = existing.linked_outline
        state["status"] = existing.status
        status_badge.value = _status_label(existing.status)

    def _set_status(status: CacheStatus) -> None:
        state["status"] = status
        status_badge.value = _status_label(status)

    def _current_cache(status: CacheStatus | str | None = None) -> Cache:
        """Assemble a Cache from the live field values (verbatim raw)."""
        if status is None:
            status = state["status"]  # type: ignore[assignment]
        return Cache(
            title=title_field.value or "",
            raw=raw_field.value or "",
            notes=notes_field.value or "",
            status=status,
            created=state["created"],  # type: ignore[arg-type]
            updated=datetime.now(),
            linked_outline=state["linked_outline"],  # type: ignore[arg-type]
        )

    def _persist(cache: Cache) -> Path:
        """Write or update the cache via core, then refresh the index."""
        path = state["path"]
        if path is None:
            path = write_cache(ctx.vault, cache)
            state["path"] = path
        else:
            update_cache(path, cache)  # type: ignore[arg-type]
        rebuild_index(ctx.vault)
        return path  # type: ignore[return-value]

    def on_save(_: ft.ControlEvent) -> None:
        try:
            cache = _current_cache()
            _persist(cache)
            notify(page, "Cache saved")
            page.update()
        except Exception as ex:
            notify(page, f"Could not save cache: {ex}")

    def on_archive(_: ft.ControlEvent) -> None:
        try:
            cache = _current_cache(CacheStatus.ARCHIVED)
            _persist(cache)
            _set_status(CacheStatus.ARCHIVED)
            notify(page, "Cache archived")
            page.update()
        except Exception as ex:
            notify(page, f"Could not archive cache: {ex}")

    def on_delete(_: ft.ControlEvent) -> None:
        path = state["path"]
        if not isinstance(path, Path):
            notify(page, "Nothing to delete")
            return
        try:
            soft_delete(ctx.vault, str(path.relative_to(ctx.vault)))
            state["path"] = None
            rebuild_index(ctx.vault)
            notify(page, "已移入回收站")
            ctx.open_library()
        except Exception as ex:
            notify(page, f"Could not delete cache: {ex}")

    def on_convert(_: ft.ControlEvent) -> None:
        try:
            linked = state["linked_outline"]
            if isinstance(linked, str):
                outline_path = ctx.vault / linked
                if outline_path.exists():
                    cache = _current_cache()
                    _persist(cache)
                    ctx.open_outline(outline_path)
                    return

            cache = _current_cache(CacheStatus.DRAFTING)
            cache_path = _persist(cache)
            _set_status(CacheStatus.DRAFTING)

            # Pre-fill an unsaved outline draft. The outline file is written,
            # and this cache becomes OUTLINED, only when the user saves it.
            outline = Outline(
                title=cache.title,
                raw_inspiration=cache.raw,
            )
            notify(page, "Outline draft ready")
            ctx.start_outline_from_cache(outline, cache_path)
        except Exception as ex:
            notify(page, f"Could not convert cache: {ex}")

    header = ft.Text(
        "New cache" if open_path is None else "Edit cache",
        size=20,
        weight=ft.FontWeight.BOLD,
    )
    buttons = ft.Row(
        controls=[
            ft.Button(content=ft.Text("Save"), on_click=on_save),
            ft.Button(content=ft.Text("Convert to outline"), on_click=on_convert),
            ft.OutlinedButton(content=ft.Text("Archive"), on_click=on_archive),
            ft.OutlinedButton(content=ft.Text("Delete"), on_click=on_delete),
        ],
        wrap=True,
    )

    return ft.Column(
        controls=[
            header,
            title_field,
            raw_field,
            notes_field,
            status_badge,
            buttons,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
