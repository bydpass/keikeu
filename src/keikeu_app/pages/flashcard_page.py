"""Read-only Summary-first Flashcard projection for a single Paper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.local_state import get_card_index, set_card_index
from keikeu_app.theme import (
    FG,
    FONT_DISPLAY,
    MUTED,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SURFACE_WARM,
)
from keikeu_app.widgets import page_header, paper_card, primary_button
from keikeu_core.markdown_io import read_paper
from keikeu_core.models import Paper
from keikeu_core.vault import resolve_active_paper_path

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_flashcard_page", "project_cards"]


def project_cards(paper: Paper) -> list[str]:
    """Project a Paper into its immutable Summary-first read-only card order."""
    return [paper.summary, *[highlight.content for highlight in paper.highlights]]


def _unavailable_page(ctx: "AppContext", message: str) -> ft.Control:
    return ft.Column(
        controls=[
            page_header("Flashcard", "只读聚焦，不保存第三份创作资产。", "FLASHCARD · FOCUS"),
            paper_card(
                [
                    ft.Text("尚未打开 Paper", size=22, font_family=FONT_DISPLAY, color=FG),
                    ft.Text(message, color=MUTED),
                    ft.OutlinedButton(
                        content=ft.Text("返回文件库"), on_click=lambda _e: ctx.open_library()
                    ),
                ],
                key="flashcard-unavailable-card",
                spacing=SPACE_4,
            ),
        ],
        spacing=SPACE_6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def build_flashcard_page(
    ctx: "AppContext",
    open_path: Path | None = None,
) -> ft.Control:
    """Build one read-only Paper card deck and remember its local position."""
    if open_path is None:
        return _unavailable_page(ctx, "请从 Paper 或本地文件库打开一张 Paper。")

    try:
        path = resolve_active_paper_path(ctx.vault, open_path)
        paper = read_paper(path)
        if path.stem != paper.code:
            raise ValueError("Paper filename and frontmatter code do not match")
    except (OSError, ValueError):
        return _unavailable_page(ctx, "找不到可读取的 Paper；它可能已被删除、移动或损坏。")

    cards = project_cards(paper)
    card_titles = [
        "Summary",
        *[
            highlight.display_name or f"Highlight {index}"
            for index, highlight in enumerate(paper.highlights, start=1)
        ],
    ]
    index = get_card_index(paper.code, len(cards), ctx.state_path)
    page = ctx.page
    state: dict[str, int | bool] = {"index": index, "show_summary": False}

    card_kind = ft.Text("", size=12, color=MUTED, weight=ft.FontWeight.W_600)
    card_text = ft.Text("", size=24, color=FG, selectable=True, key="flashcard-current-card")
    position_text = ft.Text("", color=MUTED, key="flashcard-position")
    summary_context = ft.Container(
        visible=False,
        key="flashcard-summary-context",
        bgcolor=SURFACE_WARM,
        padding=SPACE_4,
        content=ft.Column(
            controls=[
                ft.Text("当前 Summary（仅供对照）", weight=ft.FontWeight.W_600),
                ft.Text(paper.summary, selectable=True),
            ],
            spacing=SPACE_3,
        ),
    )
    summary_button = ft.OutlinedButton(content=ft.Text("查看当前 Summary"), visible=False)
    previous_button = ft.OutlinedButton(content=ft.Text("上一张"))
    next_button = primary_button("下一张", lambda _e: None)

    def render() -> None:
        current_index = int(state["index"])
        is_highlight = current_index > 0
        state["show_summary"] = bool(state["show_summary"]) and is_highlight
        card_kind.value = card_titles[current_index]
        card_text.value = cards[current_index]
        position_text.value = f"{current_index + 1} / {len(cards)}"
        previous_button.disabled = current_index == 0
        next_button.disabled = current_index == len(cards) - 1
        summary_button.visible = is_highlight
        summary_context.visible = bool(state["show_summary"])
        page.update()

    def move(delta: int) -> None:
        next_index = min(max(int(state["index"]) + delta, 0), len(cards) - 1)
        if next_index == state["index"]:
            return
        state["index"] = set_card_index(paper.code, next_index, len(cards), ctx.state_path)
        state["show_summary"] = False
        render()

    def toggle_summary(_: ft.ControlEvent) -> None:
        state["show_summary"] = not bool(state["show_summary"])
        render()

    previous_button.on_click = lambda _e: move(-1)
    next_button.on_click = lambda _e: move(1)
    summary_button.on_click = toggle_summary
    render()

    return ft.Column(
        controls=[
            page_header(
                "Flashcard",
                "只显示当前写作锚点；位置仅保存在这台设备。",
                "FLASHCARD · FOCUS",
            ),
            paper_card(
                [
                    ft.Text(
                        f"{paper.display_name} ({paper.code})"
                        if paper.display_name is not None
                        else paper.code,
                        size=14,
                        color=MUTED,
                        selectable=True,
                    ),
                    card_kind,
                    card_text,
                    position_text,
                    summary_button,
                    summary_context,
                    ft.Row(
                        controls=[
                            previous_button,
                            next_button,
                            ft.OutlinedButton(
                                content=ft.Text("返回 Paper"),
                                on_click=lambda _e: ctx.open_paper(
                                    path.relative_to(ctx.vault)
                                ),
                            ),
                        ],
                        wrap=True,
                        spacing=SPACE_3,
                    ),
                ],
                key="flashcard-card",
                spacing=SPACE_4,
            ),
        ],
        spacing=SPACE_6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
