"""Paper Library: local search, asset health, recovery, and OS handoff."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.theme import (
    BORDER,
    FG,
    FONT_DISPLAY,
    MUTED,
    SPACE_3,
    SPACE_4,
    SPACE_6,
)
from keikeu_app.widgets import (
    danger_button,
    notify,
    page_header,
    paper_card,
    single_line_field,
)
from keikeu_core.indexer import list_index_errors, list_papers, rebuild_index
from keikeu_core.vault import list_trashed_papers, restore_paper, soft_delete

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_library_page"]


def _open_command(path: Path) -> list[str]:
    """Return the platform command for opening a file with its default app."""
    system = platform.system()
    if system == "Darwin":
        return ["open", str(path)]
    if system == "Windows":
        return ["cmd", "/c", "start", "", str(path)]
    return ["xdg-open", str(path)]


def _reveal_command(path: Path) -> list[str]:
    """Return the platform command for showing a file in its file manager."""
    if platform.system() == "Darwin":
        return ["open", str(path)] if path.is_dir() else ["open", "-R", str(path)]
    return _open_command(path if path.is_dir() else path.parent)


def _run_system_command(page: ft.Page, command: list[str], action: str) -> None:
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.SubprocessError) as ex:
        notify(page, f"无法{action}：{ex}")


def _open_with_system(page: ft.Page, path: Path) -> None:
    _run_system_command(page, _open_command(path), "打开文件")


def _reveal_in_folder(page: ft.Page, path: Path) -> None:
    _run_system_command(page, _reveal_command(path), "在文件夹中显示")


def build_library_page(ctx: "AppContext") -> ft.Control:
    """Build one-search Paper Library with health and recovery sections."""
    page = ctx.page
    search_field = single_line_field("搜索代号、Summary 或 Tags")
    search_field.width = 420
    results = ft.Column(controls=[], scroll=ft.ScrollMode.AUTO, expand=True)

    def _paper_row(entry: dict[str, object]) -> ft.Control:
        rel_path = str(entry["path"])
        code = str(entry["code"])
        summary = str(entry["summary"])
        tags = [tag for tag in entry.get("tags", []) if isinstance(tag, str)]

        def on_edit(_: ft.ControlEvent) -> None:
            ctx.open_paper(ctx.vault / rel_path)

        def on_delete(_: ft.ControlEvent) -> None:
            try:
                soft_delete(ctx.vault, rel_path)
                rebuild_index(ctx.vault)
                notify(page, "已移入回收站")
                refresh()
            except (OSError, ValueError, FileExistsError) as ex:
                notify(page, f"无法删除 Paper：{ex}")

        tile = ft.ListTile(
            title=ft.Text(code),
            subtitle=ft.Text(summary),
            leading=ft.Icon(ft.Icons.EDIT_NOTE, color=MUTED),
            on_click=on_edit,
        )
        return ft.Container(
            content=ft.Column(
                controls=[
                    tile,
                    ft.Text("Tags：" + ("、".join(tags) if tags else "未添加"), size=12, color=MUTED),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(content=ft.Text("编辑"), on_click=on_edit),
                            ft.OutlinedButton(
                                content=ft.Text("打开 Flashcard"),
                                on_click=lambda _e: ctx.open_flashcards(code),
                            ),
                            ft.OutlinedButton(
                                content=ft.Text("打开"),
                                on_click=lambda _e: _open_with_system(page, ctx.vault / rel_path),
                            ),
                            ft.OutlinedButton(
                                content=ft.Text("在文件夹中显示"),
                                on_click=lambda _e: _reveal_in_folder(page, ctx.vault / rel_path),
                            ),
                            danger_button("删除", on_delete),
                        ],
                        wrap=True,
                        spacing=SPACE_3,
                    ),
                ],
                spacing=SPACE_3,
            ),
            padding=ft.Padding.only(bottom=SPACE_4),
            border=ft.Border.only(bottom=ft.BorderSide(width=1, color=BORDER)),
        )

    def _recovery_row(rel_path: Path) -> ft.Control:
        conflict_code = single_line_field("冲突时的新代号")
        conflict_code.width = 240
        message = ft.Text("", color=ft.Colors.ERROR, size=12)

        def on_restore(_: ft.ControlEvent) -> None:
            new_code = (conflict_code.value or "").strip() or None
            try:
                restore_paper(ctx.vault, str(rel_path), new_code=new_code)
                rebuild_index(ctx.vault)
                notify(page, "Paper 已恢复")
                refresh()
            except FileExistsError:
                message.value = "现有 Paper 代号冲突；输入未占用的新代号后再恢复，或取消。"
                page.update()
            except (OSError, ValueError) as ex:
                message.value = f"无法恢复 Paper：{ex}"
                page.update()

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(rel_path.name, color=FG),
                    ft.Row(
                        controls=[
                            conflict_code,
                            ft.OutlinedButton(content=ft.Text("恢复"), on_click=on_restore),
                        ],
                        wrap=True,
                        spacing=SPACE_3,
                    ),
                    message,
                ],
                spacing=SPACE_3,
            ),
            padding=ft.Padding.only(bottom=SPACE_4),
            border=ft.Border.only(bottom=ft.BorderSide(width=1, color=BORDER)),
        )

    def refresh(_: ft.ControlEvent | None = None, *, rebuild: bool = False) -> None:
        if rebuild:
            rebuild_index(ctx.vault)
        query = (search_field.value or "").strip().lower()
        papers = list_papers(ctx.vault)
        errors = list_index_errors(ctx.vault)
        trashed = list_trashed_papers(ctx.vault)
        visible = [
            entry
            for entry in papers
            if query in " ".join(
                [
                    str(entry.get("code", "")),
                    str(entry.get("summary", "")),
                    *[tag for tag in entry.get("tags", []) if isinstance(tag, str)],
                ]
            ).lower()
        ]

        results.controls.clear()
        results.controls.append(
            ft.Text(f"Paper · {len(visible)}", size=18, font_family=FONT_DISPLAY, color=FG)
        )
        results.controls.extend(_paper_row(entry) for entry in visible)
        if not visible:
            results.controls.append(ft.Text("暂无符合条件的 Paper", color=MUTED))

        results.controls.append(ft.Divider())
        results.controls.append(
            ft.Text(f"资产健康 · {len(errors)}", size=18, font_family=FONT_DISPLAY, color=FG)
        )
        if errors:
            for error in errors:
                results.controls.append(
                    ft.Text(
                        f"损坏 Paper：{error.get('path', '')} — {error.get('reason', '')}",
                        color=ft.Colors.ERROR,
                    )
                )
        else:
            results.controls.append(ft.Text("所有活动 Paper 都可读取。", color=MUTED))

        results.controls.append(ft.Divider())
        results.controls.append(
            ft.Text(f"回收站 · {len(trashed)}", size=18, font_family=FONT_DISPLAY, color=FG)
        )
        results.controls.extend(_recovery_row(path) for path in trashed)
        if not trashed:
            results.controls.append(ft.Text("回收站为空。", color=MUTED))
        page.update()

    search_field.on_change = refresh
    refresh()

    library_card = paper_card(
        [
            ft.Row(
                controls=[
                    search_field,
                    ft.OutlinedButton(
                        content=ft.Text("刷新"),
                        on_click=lambda _e: refresh(rebuild=True),
                    ),
                ],
                wrap=True,
                spacing=SPACE_3,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            ft.Divider(),
            results,
        ],
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
            page_header("本地文件库", "按代号、Summary 或 Tags 查找你的 Paper。", "VAULT · PAPER 资产"),
            library_card,
            vault_card,
        ],
        spacing=SPACE_6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
