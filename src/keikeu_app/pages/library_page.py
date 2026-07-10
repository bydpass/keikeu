"""Library page: browse caches and outlines, search, filter, and open one.

GUI layer only. Listing comes from ``keikeu_core.indexer`` (``list_caches`` /
``list_outlines``), which reads the rebuildable index derived from the user's
Markdown. This module never parses Markdown or JSON itself; it only filters the
flat entry dicts and routes a click back to the right editor page.

No cloud, login, AI, database, or graph view (out of scope before MVP).
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.theme import (
    ACCENT,
    BORDER,
    FG,
    FONT_DISPLAY,
    MUTED,
    RADIUS_SM,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SURFACE,
)
from keikeu_app.widgets import (
    danger_button,
    notify,
    page_header,
    paper_card,
    single_line_field,
)
from keikeu_core.indexer import list_caches, list_outlines, rebuild_index
from keikeu_core.models import CacheStatus
from keikeu_core.vault import soft_delete

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_library_page"]

_ALL = "all"

_STATUS_FILTER_LABELS = {
    CacheStatus.RAW: "raw — 刚存，未处理",
    CacheStatus.DRAFTING: "drafting — 已开始转配方票",
    CacheStatus.OUTLINED: "outlined — 已生成大纲",
    CacheStatus.ARCHIVED: "archived — 封存",
}


def _open_command(path: Path) -> list[str]:
    """Return the platform command for opening ``path``."""
    system = platform.system()
    if system == "Darwin":
        return ["open", str(path)]
    if system == "Windows":
        return ["cmd", "/c", "start", "", str(path)]
    return ["xdg-open", str(path)]


def _reveal_command(path: Path) -> list[str]:
    """Return the platform command for revealing ``path`` in the file manager."""
    if platform.system() == "Darwin":
        if path.is_dir():
            return ["open", str(path)]
        return ["open", "-R", str(path)]
    target = path if path.is_dir() else path.parent
    return _open_command(target)


def _run_system_command(page: ft.Page, command: list[str], action: str) -> None:
    """Run a system launcher command, reporting failures without crashing."""
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.SubprocessError) as ex:
        notify(page, f"无法{action}：{ex}")


def _open_with_system(page: ft.Page, path: Path) -> None:
    """Open ``path`` with the OS default app."""
    _run_system_command(page, _open_command(path), "打开文件")


def _reveal_in_folder(page: ft.Page, path: Path) -> None:
    """Reveal ``path`` in the OS file manager, or open its folder fallback."""
    _run_system_command(page, _reveal_command(path), "在文件夹中显示")


def build_library_page(ctx: "AppContext") -> ft.Control:
    """Build the library browser with a title search and a status filter."""
    page = ctx.page

    search_field = single_line_field("搜索标题")
    search_field.width = 360
    status_dd = ft.Dropdown(
        label="状态筛选",
        value=_ALL,
        options=[ft.dropdown.Option(key=_ALL, text="全部")]
        + [
            ft.dropdown.Option(key=status.value, text=label)
            for status, label in _STATUS_FILTER_LABELS.items()
        ],
        width=240,
        bgcolor=SURFACE,
        border_color=BORDER,
        focused_border_color=ACCENT,
        border_radius=RADIUS_SM,
        color=FG,
    )

    results = ft.Column(controls=[], scroll=ft.ScrollMode.AUTO, expand=True)

    def _open_cache(rel_path: str) -> None:
        ctx.open_cache(ctx.vault / rel_path)

    def _open_outline(rel_path: str) -> None:
        ctx.open_outline(ctx.vault / rel_path)

    def _row(entry: dict, kind: str) -> ft.Control:
        title = entry.get("title") or "（无标题）"
        subtitle_bits = ["灵感" if kind == "cache" else "大纲"]
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
                notify(page, f"无法删除文件：{ex}")

        def on_system_open(_: ft.ControlEvent, rp: str = rel_path) -> None:
            _open_with_system(page, ctx.vault / rp)

        def on_reveal(_: ft.ControlEvent, rp: str = rel_path) -> None:
            _reveal_in_folder(page, ctx.vault / rp)

        tile = ft.ListTile(
            title=ft.Text(title),
            subtitle=ft.Text("  ·  ".join(b for b in subtitle_bits if b)),
            leading=ft.Icon(
                ft.Icons.EDIT_NOTE if kind == "cache" else ft.Icons.DESCRIPTION_OUTLINED,
                color=MUTED,
            ),
            on_click=on_open,
        )
        actions = ft.Row(
                controls=[
                    ft.OutlinedButton(content=ft.Text("打开"), on_click=on_system_open),
                    ft.OutlinedButton(content=ft.Text("在文件夹中显示"), on_click=on_reveal),
                    danger_button("删除", on_delete),
                ],
                wrap=True,
                spacing=SPACE_3,
                alignment=ft.MainAxisAlignment.END,
        )
        return ft.Container(
            content=ft.Column(controls=[tile, actions], spacing=4),
            padding=ft.Padding.only(bottom=SPACE_3),
            border=ft.Border.only(bottom=ft.BorderSide(width=1, color=BORDER)),
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
            ft.Text(
                f"灵感缓存 · {len(cache_rows)}",
                size=18,
                font_family=FONT_DISPLAY,
                color=FG,
            )
        )
        results.controls.extend(cache_rows or [ft.Text("暂无灵感缓存", color=MUTED)])
        results.controls.append(ft.Divider())
        results.controls.append(
            ft.Text(
                f"大纲 · {len(outline_rows)}",
                size=18,
                font_family=FONT_DISPLAY,
                color=FG,
            )
        )
        results.controls.extend(outline_rows or [ft.Text("暂无大纲", color=MUTED)])
        page.update()

    # TextField fires on_change; Dropdown (Flet 0.85) fires on_select.
    search_field.on_change = refresh
    status_dd.on_select = refresh

    refresh(None)

    filters = ft.Row(
        controls=[
            search_field,
            status_dd,
            ft.OutlinedButton(content=ft.Text("刷新"), on_click=refresh),
        ],
        wrap=True,
        spacing=SPACE_3,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )
    library_card = paper_card(
        [filters, ft.Divider(), results],
        key="library-paper-card",
        spacing=SPACE_4,
        expand=True,
    )
    vault_card = paper_card(
        [
            ft.Text("Vault 路径", size=18, font_family=FONT_DISPLAY, color=FG),
            ft.Row(
                controls=[
                    ft.Text(
                        str(ctx.vault),
                        width=360,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        tooltip=str(ctx.vault),
                        color=MUTED,
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("在文件夹中显示"),
                        on_click=lambda _e: _reveal_in_folder(page, ctx.vault),
                    ),
                ],
                wrap=True,
                spacing=SPACE_3,
            ),
        ],
        key="library-vault-card",
        spacing=SPACE_3,
    )

    return ft.Column(
        controls=[
            page_header(
                "本地文件库",
                "所有灵感与大纲，都在你的 keikeu vault 里。",
                "VAULT · 本地资产",
            ),
            library_card,
            vault_card,
        ],
        spacing=SPACE_6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
