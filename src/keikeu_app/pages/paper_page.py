"""Paper editor page for the Road v0.3 macOS flow.

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
    close_top_dialog,
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
    read_paper_snapshot,
    update_paper,
    write_paper,
)
from keikeu_core.models import Highlight, Paper
from keikeu_core.vault import (
    resolve_active_paper_path,
    soft_delete,
)

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
    existing: Paper | None = None
    existing_bytes: bytes | None = None
    if open_path is not None:
        open_path = resolve_active_paper_path(ctx.vault, open_path)
        existing, existing_bytes = read_paper_snapshot(open_path)
    state: dict[str, object] = {
        "path": open_path,
        "paper": existing,
        "source_bytes": existing_bytes,
    }

    def validated_path(path: Path, *, must_exist: bool = True) -> Path:
        return resolve_active_paper_path(
            ctx.vault,
            path,
            must_exist=must_exist,
        )

    def rebuild_after_mutation(path: Path | None = None) -> None:
        if path is not None:
            resolve_active_paper_path(ctx.vault, path)
        rebuild_index(ctx.vault)

    code_field = single_line_field(
        "系统编号", existing.code if existing is not None else next_paper_code(ctx.vault)
    )
    code_field.read_only = True
    display_name_field = single_line_field(
        "Paper 名称（可选）",
        (existing.display_name or "") if existing is not None else "",
    )
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
    highlight_fields: list[tuple[ft.TextField, ft.TextField]] = []
    highlight_drag: dict[str, tuple[ft.TextField, ft.TextField] | None] = {
        "item": None
    }
    highlights_box = ft.Column(controls=[], key="highlights-container", spacing=SPACE_3)

    def _render_highlights() -> None:
        highlights_box.controls.clear()
        for index, fields in enumerate(highlight_fields):
            name_field, content_field = fields
            name_field.label = f"Highlight {index + 1} 命名（可选）"
            content_field.label = f"Highlight {index + 1} 内容"

            def move_up(
                _: ft.ControlEvent,
                item: tuple[ft.TextField, ft.TextField] = fields,
            ) -> None:
                position = highlight_fields.index(item)
                if position:
                    highlight_fields[position - 1], highlight_fields[position] = (
                        highlight_fields[position],
                        highlight_fields[position - 1],
                    )
                    _render_highlights()
                    page.update()

            def move_down(
                _: ft.ControlEvent,
                item: tuple[ft.TextField, ft.TextField] = fields,
            ) -> None:
                position = highlight_fields.index(item)
                if position < len(highlight_fields) - 1:
                    highlight_fields[position + 1], highlight_fields[position] = (
                        highlight_fields[position],
                        highlight_fields[position + 1],
                    )
                    _render_highlights()
                    page.update()

            def remove(
                _: ft.ControlEvent,
                item: tuple[ft.TextField, ft.TextField] = fields,
            ) -> None:
                highlight_fields.remove(item)
                _render_highlights()
                page.update()

            def start_drag(
                _: object,
                item: tuple[ft.TextField, ft.TextField] = fields,
            ) -> None:
                highlight_drag["item"] = item

            def accept_drop(
                _: object,
                target: tuple[ft.TextField, ft.TextField] = fields,
            ) -> None:
                dragged = highlight_drag.get("item")
                if dragged is None or dragged is target:
                    highlight_drag["item"] = None
                    return
                target_position = highlight_fields.index(target)
                highlight_fields.remove(dragged)
                highlight_fields.insert(target_position, dragged)
                highlight_drag["item"] = None
                _render_highlights()
                page.update()

            highlight_control = ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Draggable(
                                        group="paper-highlight",
                                        data=str(index),
                                        content=ft.Icon(
                                            ft.Icons.DRAG_INDICATOR,
                                            color=MUTED,
                                            tooltip="拖放排序手柄",
                                        ),
                                        content_feedback=ft.Text(
                                            f"Highlight {index + 1}"
                                        ),
                                        on_drag_start=start_drag,
                                        key=f"highlight-drag-{index}",
                                    ),
                                    ft.Text(
                                        f"Highlight {index + 1}",
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    ft.PopupMenuButton(
                                        icon=ft.Icons.MORE_HORIZ,
                                        tooltip=f"Highlight {index + 1} 排序菜单",
                                        key=f"highlight-menu-{index}",
                                        items=[
                                            ft.PopupMenuItem(
                                                content="上移",
                                                key=f"highlight-move-up-{index}",
                                                disabled=index == 0,
                                                on_click=move_up,
                                            ),
                                            ft.PopupMenuItem(
                                                content="下移",
                                                key=f"highlight-move-down-{index}",
                                                disabled=index == len(highlight_fields) - 1,
                                                on_click=move_down,
                                            ),
                                            ft.PopupMenuItem(
                                                content="删除 Highlight",
                                                key=f"highlight-remove-{index}",
                                                on_click=remove,
                                            ),
                                        ],
                                    ),
                                ],
                                spacing=SPACE_3,
                            ),
                            name_field,
                            content_field,
                        ],
                        spacing=SPACE_3,
                    ),
                    padding=ft.Padding.only(bottom=SPACE_3),
                    border=ft.Border.only(bottom=ft.BorderSide(1, BORDER_SOFT)),
                )
            highlights_box.controls.append(
                ft.DragTarget(
                    group="paper-highlight",
                    data=str(index),
                    content=highlight_control,
                    on_accept=accept_drop,
                    key=f"highlight-drop-{index}",
                )
            )

    def add_highlight(
        _: ft.ControlEvent | None = None,
        value: Highlight | None = None,
    ) -> None:
        highlight = value or Highlight(content="")
        highlight_fields.append(
            (
                single_line_field("", highlight.display_name or ""),
                section_field("", highlight.content, min_lines=2, max_lines=6),
            )
        )
        _render_highlights()
        if _ is not None:
            page.update()

    for highlight in existing.highlights if existing is not None else []:
        add_highlight(value=highlight)

    def apply_snapshot(path: Path, paper: Paper, source_bytes: bytes) -> None:
        state["path"] = path
        state["paper"] = paper
        state["source_bytes"] = source_bytes
        code_field.value = paper.code
        code_field.read_only = True
        display_name_field.value = paper.display_name or ""
        summary_field.value = paper.summary
        tags_field.value = ", ".join(paper.tags)
        initial_copy.value = paper.initial_summary
        highlight_fields[:] = [
            (
                single_line_field("", highlight.display_name or ""),
                section_field("", highlight.content, min_lines=2, max_lines=6),
            )
            for highlight in paper.highlights
        ]
        _render_highlights()

    def _build_paper() -> Paper:
        stored = state["paper"]
        paper = stored if isinstance(stored, Paper) else None
        return Paper(
            code=code_field.value or "",
            initial_summary=paper.initial_summary if paper is not None else "",
            summary=summary_field.value or "",
            display_name=display_name_field.value,
            highlights=[
                Highlight(
                    display_name=name_field.value,
                    content=content_field.value or "",
                )
                for name_field, content_field in highlight_fields
            ],
            tags=(tags_field.value or "").split(","),
            created=paper.created if paper is not None else datetime.now(),
            updated=datetime.now(),
            legacy_title=paper.legacy_title if paper is not None else None,
            extra_frontmatter=paper.extra_frontmatter.copy() if paper is not None else {},
        )

    def on_save(_: object) -> None:
        if not (summary_field.value or "").strip():
            save_error.value = "Summary 不能为空。"
            page.update()
            return
        try:
            paper = _build_paper()
            path = state["path"]
            if isinstance(path, Path):
                try:
                    path = validated_path(path)
                except FileNotFoundError:
                    save_error.value = "Paper 已在外部删除或移动；未保存。请返回本地文件库刷新。"
                    page.update()
                    return
                source_bytes = state["source_bytes"]
                if not isinstance(source_bytes, bytes):
                    raise ValueError("Paper source snapshot is unavailable")
                path = validated_path(path)
                try:
                    update_paper(
                        ctx.vault,
                        path,
                        paper,
                        expected_source_bytes=source_bytes,
                    )
                except ValueError as ex:
                    if "Paper changed externally; update refused" not in str(ex):
                        raise
                    save_error.value = "Paper 已在外部修改；未覆盖。请重新打开后决定如何处理。"
                    page.update()
                    return
            else:
                destination = Path("cache") / f"{paper.code}.md"
                validated_path(destination, must_exist=False)
                path = write_paper(
                    ctx.vault,
                    paper,
                    destination=destination,
                )
            path = validated_path(path)
            stored, source_bytes = read_paper_snapshot(path)
            apply_snapshot(path, stored, source_bytes)
            save_error.value = ""
            rebuild_after_mutation(path)
            notify(page, "Paper 已保存")
            page.update()
        except (OSError, ValueError, FileExistsError) as ex:
            save_error.value = f"无法保存 Paper：{ex}"
            page.update()

    def on_delete(_: ft.ControlEvent) -> None:
        path = state["path"]
        if not isinstance(path, Path):
            save_error.value = "尚未保存的 Paper 无法删除。"
            page.update()
            return
        try:
            path = validated_path(path)
            soft_delete(ctx.vault, str(path))
            rebuild_after_mutation()
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
        path = state["path"]
        if not isinstance(path, Path):
            save_error.value = "请先保存 Paper，再打开 Flashcard。"
            page.update()
            return
        ctx.open_flashcards(path.relative_to(ctx.vault))

    editor_card = paper_card(
        [
            ft.Text("新 Paper" if existing is None else "编辑 Paper", size=TEXT_LG, font_family=FONT_DISPLAY),
            code_field,
            display_name_field,
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

    def on_keyboard(event: object) -> None:
        key = str(getattr(event, "key", "")).upper()
        if key in {"ESC", "ESCAPE"}:
            close_top_dialog(page)
        elif key == "S" and bool(getattr(event, "meta", False)):
            on_save(event)

    page.on_keyboard_event = on_keyboard

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
