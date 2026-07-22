"""Read-only Summary-first Flashcard projection with no position persistence."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.theme import (
    ACCENT,
    ACCENT_ON,
    BORDER,
    FG,
    FONT_DISPLAY,
    MUTED,
    RADIUS_SM,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SURFACE_WARM,
)
from keikeu_app.widgets import (
    close_top_dialog,
    page_header,
    paper_card,
    primary_button,
    single_line_field,
)
from keikeu_core.indexer import rebuild_index
from keikeu_core.markdown_io import read_paper
from keikeu_core.models import Paper
from keikeu_core.vault import resolve_active_paper_path

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_flashcard_page", "project_cards"]


def project_cards(paper: Paper) -> list[str]:
    """Project a Paper into its immutable Summary-first read-only card order."""
    return [paper.summary, *[highlight.content for highlight in paper.highlights]]


def _paper_label(paper: Paper) -> str:
    return (
        f"{paper.display_name} ({paper.code})"
        if paper.display_name is not None
        else paper.code
    )


def _card_titles(paper: Paper) -> list[str]:
    return [
        "Summary",
        *[
            highlight.display_name or f"Highlight {index}"
            for index, highlight in enumerate(paper.highlights, start=1)
        ],
    ]


def _unavailable_page(ctx: "AppContext", message: str) -> ft.Control:
    return ft.Column(
        controls=[
            page_header("Flashcard", "只读聚焦，不保存第三份创作资产。", "FLASHCARD · FOCUS"),
            paper_card(
                [
                    ft.Text("尚未打开 Paper", size=22, font_family=FONT_DISPLAY, color=FG),
                    ft.Text(message, color=MUTED),
                    ft.OutlinedButton(
                        content=ft.Text("返回文件库"),
                        on_click=lambda _e: ctx.open_library(),
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
    """Build a selector and one read-only card deck that always starts at page 1."""
    page = ctx.page
    try:
        entries = rebuild_index(ctx.vault)["papers"]
    except (OSError, ValueError):
        entries = []

    requested_path: Path | None = open_path
    if requested_path is None and entries:
        first_path = entries[0].get("path")
        requested_path = Path(first_path) if isinstance(first_path, str) else None
    if requested_path is None:
        return _unavailable_page(ctx, "Vault 中还没有可选择的 Paper。")

    def read_selected(relative_path: Path) -> tuple[Path, Paper]:
        path = resolve_active_paper_path(ctx.vault, relative_path)
        paper = read_paper(path)
        if path.stem != paper.code:
            raise ValueError("Paper filename and frontmatter code do not match")
        return path, paper

    try:
        initial_path, initial_paper = read_selected(requested_path)
    except (OSError, ValueError):
        return _unavailable_page(ctx, "找不到可读取的 Paper；它可能已被删除、移动或损坏。")

    relative_initial = initial_path.relative_to(ctx.vault)
    option_labels: dict[str, str] = {}
    for entry in entries:
        relative = entry.get("path")
        code = entry.get("code")
        display_name = entry.get("display_name")
        if not isinstance(relative, str) or not isinstance(code, str):
            continue
        option_labels[relative] = (
            f"{display_name} ({code})"
            if isinstance(display_name, str) and display_name
            else code
        )
    option_labels.setdefault(str(relative_initial), _paper_label(initial_paper))

    paper_selector = ft.Dropdown(
        label="Paper",
        value=str(relative_initial),
        width=430,
        dense=True,
        options=[
            ft.DropdownOption(key=path, text=label)
            for path, label in sorted(
                option_labels.items(),
                key=lambda item: (item[1].casefold(), item[0]),
            )
        ],
        key="flashcard-paper-selector",
    )
    card_kind = ft.Text(
        "",
        size=12,
        color=MUTED,
        weight=ft.FontWeight.W_600,
        key="flashcard-card-title",
    )
    card_text = ft.Text(
        "",
        size=24,
        color=FG,
        selectable=True,
        key="flashcard-current-card",
    )
    position_text = ft.Text("", color=MUTED, key="flashcard-position")
    boundary_notice = ft.Text("", color=MUTED, size=12, key="flashcard-notice")
    card_list = ft.Column(
        controls=[],
        spacing=SPACE_2,
        scroll=ft.ScrollMode.AUTO,
        key="flashcard-list",
    )
    jump_field = single_line_field("页码")
    jump_field.width = 90
    jump_field.key = "flashcard-jump-page"
    summary_context = ft.Container(
        visible=False,
        key="flashcard-summary-context",
        bgcolor=SURFACE_WARM,
        padding=SPACE_4,
        content=ft.Column(
            controls=[
                ft.Text("当前 Summary（仅供对照）", weight=ft.FontWeight.W_600),
                ft.Text(
                    initial_paper.summary,
                    selectable=True,
                    key="flashcard-summary-text",
                ),
            ],
            spacing=SPACE_3,
        ),
    )
    summary_button = ft.OutlinedButton(content=ft.Text("查看当前 Summary"), visible=False)
    previous_button = ft.OutlinedButton(content=ft.Text("上一张"))
    next_button = primary_button("下一张", lambda _e: None)
    paper_name = ft.Text("", size=14, color=MUTED, selectable=True)
    state: dict[str, object] = {
        "path": initial_path,
        "paper": initial_paper,
        "cards": project_cards(initial_paper),
        "titles": _card_titles(initial_paper),
        "index": 0,
        "show_summary": False,
    }
    notice_generation = 0

    async def clear_notice_after_delay(generation: int) -> None:
        await asyncio.sleep(2)
        if generation != notice_generation:
            return
        boundary_notice.value = ""
        page.update()

    def show_notice(message: str) -> None:
        nonlocal notice_generation
        notice_generation += 1
        boundary_notice.value = message
        page.run_task(clear_notice_after_delay, notice_generation)
        page.update()

    def select_card(index: int) -> None:
        state["index"] = index
        state["show_summary"] = False
        boundary_notice.value = ""
        render()

    def render(*, update: bool = True) -> None:
        paper = state["paper"]
        cards = state["cards"]
        titles = state["titles"]
        current_index = int(state["index"])
        if (
            not isinstance(paper, Paper)
            or not isinstance(cards, list)
            or not isinstance(titles, list)
        ):
            raise ValueError("Flashcard state is invalid")
        is_highlight = current_index > 0
        state["show_summary"] = bool(state["show_summary"]) and is_highlight
        paper_name.value = _paper_label(paper)
        card_kind.value = str(titles[current_index])
        card_text.value = str(cards[current_index])
        position_text.value = f"{current_index + 1} / {len(cards)}"
        jump_field.value = str(current_index + 1)
        summary_button.visible = is_highlight
        summary_context.visible = bool(state["show_summary"])
        summary_text = summary_context.content.controls[1]
        if isinstance(summary_text, ft.Text):
            summary_text.value = paper.summary
        card_list.controls = [
            ft.Button(
                content=ft.Text(f"{index + 1}. {title}"),
                key=f"flashcard-list-{index}",
                on_click=lambda _e, target=index: select_card(target),
                bgcolor=ACCENT if index == current_index else SURFACE_WARM,
                color=ACCENT_ON if index == current_index else FG,
                elevation=0,
                style=ft.ButtonStyle(
                    alignment=ft.Alignment.CENTER_LEFT,
                    shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                ),
            )
            for index, title in enumerate(titles)
        ]
        if update:
            page.update()

    def move(delta: int) -> None:
        cards = state["cards"]
        if not isinstance(cards, list):
            return
        current_index = int(state["index"])
        next_index = current_index + delta
        if next_index < 0:
            show_notice("已经是第一张。")
            return
        if next_index >= len(cards):
            show_notice("已经是最后一张。")
            return
        select_card(next_index)

    def switch_paper(_: object) -> None:
        selected = paper_selector.value
        previous_path = state["path"]
        if not isinstance(selected, str):
            return
        try:
            path, paper = read_selected(Path(selected))
        except (OSError, ValueError) as ex:
            paper_selector.value = str(
                previous_path.relative_to(ctx.vault)
                if isinstance(previous_path, Path)
                else relative_initial
            )
            show_notice(f"无法切换 Paper：{ex}")
            return
        state.update(
            {
                "path": path,
                "paper": paper,
                "cards": project_cards(paper),
                "titles": _card_titles(paper),
                "index": 0,
                "show_summary": False,
            }
        )
        boundary_notice.value = ""
        render()

    def jump(_: object) -> None:
        raw = (jump_field.value or "").strip()
        cards = state["cards"]
        if not isinstance(cards, list):
            return
        if not raw.isdecimal():
            show_notice(f"请输入 1..{len(cards)} 的整数页码。")
            return
        requested = int(raw)
        if requested < 1 or requested > len(cards):
            show_notice(f"页码范围是 1..{len(cards)}。")
            return
        select_card(requested - 1)

    def toggle_summary(_: object) -> None:
        state["show_summary"] = not bool(state["show_summary"])
        render()

    def return_to_paper(_: object) -> None:
        path = state["path"]
        if isinstance(path, Path):
            ctx.open_paper(path.relative_to(ctx.vault))

    def on_keyboard(event: object) -> None:
        key = str(getattr(event, "key", "")).upper().replace(" ", "").replace("_", "")
        if key in {"ESC", "ESCAPE"}:
            close_top_dialog(page)
        elif key in {"ARROWLEFT", "LEFT"}:
            move(-1)
        elif key in {"ARROWRIGHT", "RIGHT"}:
            move(1)

    paper_selector.on_select = switch_paper
    jump_field.on_submit = jump
    previous_button.on_click = lambda _e: move(-1)
    next_button.on_click = lambda _e: move(1)
    summary_button.on_click = toggle_summary
    page.on_keyboard_event = on_keyboard
    render(update=False)

    return ft.Column(
        controls=[
            page_header(
                "Flashcard",
                "选择 Paper 与写作锚点；每次打开都从第 1 页开始。",
                "FLASHCARD · FOCUS",
            ),
            paper_card(
                [
                    paper_selector,
                    paper_name,
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=card_list,
                                width=170,
                                padding=SPACE_3,
                                bgcolor=SURFACE_WARM,
                                border=ft.Border.all(1, BORDER),
                                border_radius=RADIUS_SM,
                            ),
                            ft.Column(
                                controls=[
                                    card_kind,
                                    card_text,
                                    position_text,
                                    boundary_notice,
                                    summary_button,
                                    summary_context,
                                ],
                                spacing=SPACE_3,
                                expand=True,
                            ),
                        ],
                        spacing=SPACE_4,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Row(
                        controls=[
                            previous_button,
                            next_button,
                            ft.Text("第"),
                            jump_field,
                            ft.Text("页"),
                            ft.OutlinedButton(content=ft.Text("跳转"), on_click=jump),
                            ft.OutlinedButton(
                                content=ft.Text("返回 Paper"),
                                on_click=return_to_paper,
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
