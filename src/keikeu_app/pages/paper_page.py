"""Paper editor page for the Road v0.2 macOS flow.

The page only gathers author input and calls public core APIs.  It never
renders Markdown, builds JSON, or decides how a Paper is serialized.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.theme import (
    BORDER_SOFT,
    FG,
    FONT_DISPLAY,
    MUTED,
    RADIUS_SM,
    SPACE_3,
    SPACE_6,
    SURFACE_WARM,
    TEXT_LG,
)
from keikeu_app.widgets import (
    danger_button,
    notify,
    page_header,
    paper_card,
    primary_button,
    section_field,
    single_line_field,
)
from keikeu_core.indexer import list_papers, rebuild_index
from keikeu_core.markdown_io import (
    next_paper_code,
    read_paper,
    rename_paper,
    update_paper,
    write_paper,
)
from keikeu_core.models import Paper
from keikeu_core.vault import soft_delete

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_paper_page"]


def _known_tags(vault: Path) -> list[str]:
    """Collect first-seen tags from the disposable index for a soft suggestion."""
    tags: list[str] = []
    try:
        entries = list_papers(vault)
    except (OSError, ValueError):
        return tags
    for entry in entries:
        for tag in entry.get("tags", []):
            if isinstance(tag, str) and tag not in tags:
                tags.append(tag)
    return tags


def build_paper_page(ctx: "AppContext", open_path: Path | None = None) -> ft.Control:
    """Build a Paper create/edit page for ``open_path`` or a fresh Paper."""
    page = ctx.page
    existing = read_paper(open_path) if open_path is not None else None
    state: dict[str, Path | Paper | None] = {"path": open_path, "paper": existing}

    code_field = single_line_field(
        "Paper 代号", existing.code if existing is not None else next_paper_code(ctx.vault)
    )
    code_field.read_only = existing is not None
    summary_field = section_field(
        "Summary", existing.summary if existing is not None else "", min_lines=4, max_lines=12
    )
    tags_field = single_line_field(
        "Tags（用逗号分隔）", ", ".join(existing.tags) if existing is not None else ""
    )
    tags_field.hint_text = "例如：末班车, 离别, 暧昧"
    known_tags = _known_tags(ctx.vault)
    tag_hint = ft.Text(
        "已有 Tags：" + ("、".join(known_tags) if known_tags else "还没有，直接输入即可。"),
        size=12,
        color=MUTED,
    )
    initial_copy = ft.Text(
        existing.initial_summary if existing is not None else "初稿副本会在首次保存后冻结，只读保留。",
        selectable=True,
    )
    save_error = ft.Text("", color=ft.Colors.ERROR)
    highlight_fields: list[ft.TextField] = []
    highlights_box = ft.Column(controls=[], key="highlights-container", spacing=SPACE_3)
    rename_field = single_line_field("新代号")
    rename_area = ft.Container(
        visible=existing is not None,
        content=ft.Row(
            controls=[rename_field, ft.OutlinedButton(content=ft.Text("重命名"))],
            wrap=True,
            spacing=SPACE_3,
        ),
    )

    def _render_highlights() -> None:
        highlights_box.controls.clear()
        for index, field in enumerate(highlight_fields):
            field.label = f"Highlight {index + 1}"

            def move_up(_: ft.ControlEvent, item: ft.TextField = field) -> None:
                position = highlight_fields.index(item)
                if position:
                    highlight_fields[position - 1], highlight_fields[position] = (
                        highlight_fields[position],
                        highlight_fields[position - 1],
                    )
                    _render_highlights()
                    page.update()

            def move_down(_: ft.ControlEvent, item: ft.TextField = field) -> None:
                position = highlight_fields.index(item)
                if position < len(highlight_fields) - 1:
                    highlight_fields[position + 1], highlight_fields[position] = (
                        highlight_fields[position],
                        highlight_fields[position + 1],
                    )
                    _render_highlights()
                    page.update()

            def remove(_: ft.ControlEvent, item: ft.TextField = field) -> None:
                highlight_fields.remove(item)
                _render_highlights()
                page.update()

            highlights_box.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            field,
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_UPWARD,
                                        tooltip="上移",
                                        key=f"highlight-move-up-{index}",
                                        on_click=move_up,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_DOWNWARD,
                                        tooltip="下移",
                                        key=f"highlight-move-down-{index}",
                                        on_click=move_down,
                                    ),
                                    ft.OutlinedButton(content=ft.Text("删除 Highlight"), on_click=remove),
                                ],
                                spacing=SPACE_3,
                            ),
                        ],
                        spacing=SPACE_3,
                    ),
                    padding=ft.Padding.only(bottom=SPACE_3),
                    border=ft.Border.only(bottom=ft.BorderSide(1, BORDER_SOFT)),
                )
            )

    def add_highlight(_: ft.ControlEvent | None = None, value: str = "") -> None:
        highlight_fields.append(section_field("", value, min_lines=2, max_lines=6))
        _render_highlights()
        if _ is not None:
            page.update()

    for highlight in existing.highlights if existing is not None else []:
        add_highlight(value=highlight)

    def _build_paper() -> Paper:
        stored = state["paper"]
        paper = stored if isinstance(stored, Paper) else None
        return Paper(
            code=code_field.value or "",
            initial_summary=paper.initial_summary if paper is not None else "",
            summary=summary_field.value or "",
            highlights=[field.value or "" for field in highlight_fields],
            tags=(tags_field.value or "").split(","),
            created=paper.created if paper is not None else datetime.now(),
            updated=datetime.now(),
            legacy_title=paper.legacy_title if paper is not None else None,
            extra_frontmatter=paper.extra_frontmatter.copy() if paper is not None else {},
        )

    def on_save(_: ft.ControlEvent) -> None:
        if not (summary_field.value or "").strip():
            save_error.value = "Summary 不能为空。"
            page.update()
            return
        try:
            paper = _build_paper()
            path = state["path"]
            if isinstance(path, Path):
                update_paper(path, paper)
            else:
                path = write_paper(ctx.vault, paper)
                state["path"] = path
                code_field.read_only = True
                rename_area.visible = True
            state["paper"] = read_paper(path)
            initial_copy.value = state["paper"].initial_summary  # type: ignore[union-attr]
            save_error.value = ""
            rebuild_index(ctx.vault)
            notify(page, "Paper 已保存")
            page.update()
        except (OSError, ValueError, FileExistsError) as ex:
            save_error.value = f"无法保存 Paper：{ex}"
            page.update()

    def on_rename(_: ft.ControlEvent) -> None:
        path = state["path"]
        stored = state["paper"]
        if not isinstance(path, Path) or not isinstance(stored, Paper):
            save_error.value = "请先保存 Paper，再进行重命名。"
            page.update()
            return
        try:
            target = rename_paper(ctx.vault, stored.code, rename_field.value or "")
            state["path"] = target
            state["paper"] = read_paper(target)
            code_field.value = state["paper"].code  # type: ignore[union-attr]
            rename_field.value = ""
            save_error.value = ""
            rebuild_index(ctx.vault)
            notify(page, "Paper 已重命名")
            page.update()
        except (OSError, ValueError, FileExistsError) as ex:
            save_error.value = f"无法重命名 Paper：{ex}"
            page.update()

    rename_button = rename_area.content.controls[1]  # type: ignore[union-attr]
    rename_button.on_click = on_rename  # type: ignore[attr-defined]

    def on_delete(_: ft.ControlEvent) -> None:
        path = state["path"]
        if not isinstance(path, Path):
            save_error.value = "尚未保存的 Paper 无法删除。"
            page.update()
            return
        try:
            soft_delete(ctx.vault, str(path.relative_to(ctx.vault)))
            rebuild_index(ctx.vault)
            notify(page, "已移入回收站")
            ctx.open_library()
        except (OSError, ValueError, FileExistsError) as ex:
            save_error.value = f"无法删除 Paper：{ex}"
            page.update()

    def on_flashcards(_: ft.ControlEvent) -> None:
        stored = state["paper"]
        if not isinstance(stored, Paper):
            save_error.value = "请先保存 Paper，再打开 Flashcard。"
            page.update()
            return
        ctx.open_flashcards(stored.code)

    editor_card = paper_card(
        [
            ft.Text("新 Paper" if existing is None else "编辑 Paper", size=TEXT_LG, font_family=FONT_DISPLAY),
            code_field,
            summary_field,
            ft.Container(
                content=ft.Column(
                    controls=[ft.Text("初稿副本（只读）", weight=ft.FontWeight.W_600), initial_copy],
                    spacing=SPACE_3,
                ),
                bgcolor=SURFACE_WARM,
                border=ft.Border.all(1, BORDER_SOFT),
                border_radius=RADIUS_SM,
                padding=SPACE_3,
            ),
            ft.Text("Highlights（可选）", weight=ft.FontWeight.W_600),
            ft.Text("留空也可保存；每条会成为一张 Flashcard。", size=12, color=MUTED),
            highlights_box,
            ft.OutlinedButton(content=ft.Text("+ 添加 Highlight"), on_click=add_highlight),
            tags_field,
            tag_hint,
            rename_area,
            save_error,
            ft.Row(
                controls=[
                    primary_button("保存", on_save),
                    ft.OutlinedButton(content=ft.Text("打开 Flashcard"), on_click=on_flashcards),
                    ft.OutlinedButton(content=ft.Text("返回文件库"), on_click=lambda _e: ctx.open_library()),
                    danger_button("删除", on_delete),
                ],
                wrap=True,
                spacing=SPACE_3,
            ),
        ],
        key="paper-editor-card",
        spacing=SPACE_3,
    )

    return ft.Column(
        controls=[
            page_header(
                "纸片",
                "保存当前 Summary；首次保存的初稿副本会永久保留。",
                "PAPER · 写作准备单元",
            ),
            editor_card,
        ],
        spacing=SPACE_6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
