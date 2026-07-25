"""Headless Flet contracts for the Paper v3 editor and Library."""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

import flet as ft
import pytest

from keikeu_app import main as app_main
from keikeu_app.local_state import load_last_daily_card_date
from keikeu_app.main import AppContext
from keikeu_app.pages import flashcard_page as flashcard_page_mod
from keikeu_app.pages import library_page as library_page_mod
from keikeu_app.pages.flashcard_page import build_flashcard_page
from keikeu_app.pages.library_page import build_library_page
from keikeu_app.pages.paper_page import build_paper_page
from keikeu_core.indexer import rebuild_index
from keikeu_core.markdown_io import (
    read_paper,
    render_paper_bytes,
    update_paper,
    write_paper as _write_paper,
)
from keikeu_core.models import Highlight, Paper
from keikeu_core.vault import (
    PathOperationResult,
    create_folder,
    init_vault,
    soft_delete,
    soft_delete_folder,
)


def write_paper(
    vault: Path,
    paper: Paper,
    *,
    destination: str | Path | None = None,
) -> Path:
    return _write_paper(
        vault,
        paper,
        destination=destination or Path("cache") / f"{paper.code}.md",
    )


class FakePage:
    """The small subset of ``ft.Page`` exercised by the page builders."""

    def __init__(self) -> None:
        self.controls: list[object] = []
        self.overlay: list[object] = []
        self.dialogs: list[ft.AlertDialog] = []
        self.services: list[object] = []
        self.scroll = ft.ScrollMode.AUTO
        self.update_count = 0
        self.theme: ft.Theme | None = None
        self.bgcolor: str | None = None
        self.title = ""
        self.window = SimpleNamespace(width=None, height=None)
        self.on_keyboard_event = None
        self.tasks: list[tuple[object, tuple[object, ...]]] = []

    def add(self, *controls: object) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.update_count += 1

    def show_dialog(self, dialog: ft.AlertDialog) -> None:
        if dialog in self.dialogs:
            raise RuntimeError("Dialog is already opened")
        dialog.open = True
        self.dialogs.append(dialog)
        self.update()

    def pop_dialog(self) -> ft.AlertDialog | None:
        for dialog in reversed(self.dialogs):
            if dialog.open:
                dialog.open = False
                self.update()
                return dialog
        return None

    def run_task(self, handler: object, *args: object) -> None:
        self.tasks.append((handler, args))


def _walk(control: object) -> Iterable[object]:
    yield control
    for attr in ("content", "leading", "trailing", "title", "subtitle"):
        child = getattr(control, attr, None)
        if child is not None:
            yield from _walk(child)
    for child in getattr(control, "actions", []) or []:
        yield from _walk(child)
    for attr in ("items", "secondary_items"):
        for child in getattr(control, attr, []) or []:
            yield from _walk(child)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def _text_field(root: object, label: str) -> ft.TextField:
    for control in _walk(root):
        if isinstance(control, ft.TextField) and control.label == label:
            return control
    raise AssertionError(f"TextField not found: {label}")


def _button(root: object, text: str) -> object:
    for control in _walk(root):
        content = getattr(control, "content", None)
        if getattr(content, "value", None) == text:
            return control
    raise AssertionError(f"Button not found: {text}")


def _control_by_key(root: object, key: str) -> object:
    for control in _walk(root):
        if getattr(control, "key", None) == key:
            return control
    raise AssertionError(f"Control not found: {key}")


def _popup_item(root: object, text: str) -> ft.PopupMenuItem:
    for control in _walk(root):
        if isinstance(control, ft.PopupMenuItem) and control.content == text:
            return control
    raise AssertionError(f"Popup item not found: {text}")


def _texts(root: object) -> list[str]:
    return [
        control.value
        for control in _walk(root)
        if isinstance(control, ft.Text) and isinstance(control.value, str)
    ]


def _paper(
    code: str,
    summary: str,
    tags: list[str] | None = None,
    highlights: list[str | Highlight] | None = None,
    display_name: str | None = None,
) -> Paper:
    return Paper(
        code=code,
        initial_summary="",
        summary=summary,
        display_name=display_name,
        highlights=[
            item if isinstance(item, Highlight) else Highlight(content=item)
            for item in highlights or []
        ],
        tags=tags or [],
        created=datetime(2026, 7, 14, 9, 0),
        updated=datetime(2026, 7, 14, 9, 0),
    )


def _ctx(page: FakePage, vault: Path) -> AppContext:
    return AppContext(page=page, vault=vault)  # type: ignore[arg-type]


def test_shell_uses_paper_flashcard_and_library_navigation(tmp_path):
    init_vault(tmp_path)
    page = FakePage()

    app_main._build_shell(page, tmp_path)  # type: ignore[attr-defined, arg-type]

    assert page.scroll is None
    assert not any(
        isinstance(control, ft.NavigationRail) for control in _walk(page.controls[0])
    )
    assert _control_by_key(page.controls[0], "shell-sidebar")
    labels = [
        _button(page.controls[0], "纸片"),
        _button(page.controls[0], "Flashcard"),
        _button(page.controls[0], "本地文件库"),
    ]
    assert all(labels)
    assert "配方票编辑" not in _texts(page.controls[0])

    labels[2].on_click(None)

    assert _control_by_key(page.controls[0], "shell-library-scopes")
    assert _control_by_key(page.controls[0], "library-scope-all")
    assert _control_by_key(page.controls[0], "library-scope-unfiled")
    assert _control_by_key(page.controls[0], "library-scope-trash")
    assert page.on_keyboard_event is not None

    labels[0].on_click(None)

    assert page.on_keyboard_event is not None


def test_daily_start_claims_before_display_and_enter_opens_blank_paper(tmp_path):
    init_vault(tmp_path)
    state_path = tmp_path / "fresh-device-state.json"
    page = FakePage()

    app_main._build_startup(  # type: ignore[attr-defined, arg-type]
        page,
        tmp_path,
        state_path=state_path,
    )

    assert _control_by_key(page.controls[0], "daily-start-card")
    assert "玛格丽特·阿特伍德（意译）" in _texts(page.controls[0])
    assert "写作像走迷宫。撞墙时，退回走错的路口，换一条路。" in _texts(
        page.controls[0]
    )
    assert load_last_daily_card_date(state_path) is not None
    assert page.tasks

    page.on_keyboard_event(SimpleNamespace(key="Enter", meta=False))

    assert _control_by_key(page.controls[0], "shell-sidebar")
    assert _control_by_key(page.controls[0], "paper-editor-card")
    assert _text_field(page.controls[0], "Summary").value == ""


def test_daily_start_is_same_day_once_and_three_second_task_is_idempotent(
    tmp_path, monkeypatch
):
    init_vault(tmp_path)
    state_path = tmp_path / "fresh-device-state.json"
    first_page = FakePage()
    app_main._build_startup(  # type: ignore[attr-defined, arg-type]
        first_page,
        tmp_path,
        state_path=state_path,
    )

    async def no_delay(_: float) -> None:
        return None

    monkeypatch.setattr(app_main.asyncio, "sleep", no_delay)
    handler, args = first_page.tasks[-1]
    asyncio.run(handler(*args))
    assert _control_by_key(first_page.controls[0], "paper-editor-card")

    second_page = FakePage()
    app_main._build_startup(  # type: ignore[attr-defined, arg-type]
        second_page,
        tmp_path,
        state_path=state_path,
    )
    assert _control_by_key(second_page.controls[0], "paper-editor-card")
    with pytest.raises(AssertionError, match="Control not found"):
        _control_by_key(second_page.controls[0], "daily-start-card")


def test_paper_page_exposes_v3_names_and_an_immutable_system_code(tmp_path):
    init_vault(tmp_path)
    root = build_paper_page(_ctx(FakePage(), tmp_path))

    assert _text_field(root, "系统编号").value.startswith("K-")
    assert _text_field(root, "系统编号").read_only is True
    assert _text_field(root, "Paper 名称（可选）")
    assert _text_field(root, "Summary")
    assert _text_field(root, "Tags（用逗号分隔）")
    assert "初稿副本会在首次保存后冻结，只读保留。" in _texts(root)
    assert not any(label in {"标题", "原始灵感", "临时备注"} for label in [
        field.label for field in _walk(root) if isinstance(field, ft.TextField)
    ])
    assert _control_by_key(root, "paper-editor-card")
    assert not any(text in {"新代号", "重命名"} for text in _texts(root))


def test_empty_summary_does_not_create_a_paper(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    root = build_paper_page(_ctx(page, tmp_path))

    _button(root, "保存").on_click(None)

    assert list((tmp_path / "cache").glob("*.md")) == []
    assert "Summary 不能为空。" in _texts(root)


def test_save_reopen_and_update_preserves_first_draft(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    root = build_paper_page(_ctx(page, tmp_path))
    code = _text_field(root, "系统编号").value
    _text_field(root, "Paper 名称（可选）").value = "  Night Bus  "
    _text_field(root, "Summary").value = "First draft summary."
    _text_field(root, "Tags（用逗号分隔）").value = "rain, station, rain"
    _button(root, "+ 添加 Highlight").on_click(None)
    _text_field(root, "Highlight 1 命名（可选）").value = "  Breath  "
    _text_field(root, "Highlight 1 内容").value = "A held breath."
    _button(root, "+ 添加 Highlight").on_click(None)
    _text_field(root, "Highlight 2 命名（可选）").value = "Discard me"
    _text_field(root, "Highlight 2 内容").value = "  \n "

    _button(root, "保存").on_click(None)
    path = tmp_path / "cache" / f"{code}.md"
    paper = read_paper(path)
    assert paper.initial_summary == "First draft summary."
    assert paper.display_name == "Night Bus"
    assert paper.highlights == [
        Highlight(content="A held breath.", display_name="Breath")
    ]
    assert paper.tags == ["rain", "station"]
    assert _text_field(root, "Tags（用逗号分隔）").value == "rain, station"

    reopened = build_paper_page(_ctx(page, tmp_path), path)
    assert _text_field(reopened, "系统编号").read_only is True
    assert _text_field(reopened, "Paper 名称（可选）").value == "Night Bus"
    _text_field(reopened, "Summary").value = "Edited current summary."
    _button(reopened, "保存").on_click(None)

    updated = read_paper(path)
    assert updated.initial_summary == "First draft summary."
    assert updated.summary == "Edited current summary."
    assert _text_field(reopened, "Summary").value == "Edited current summary."


def test_editor_refuses_to_overwrite_an_externally_changed_paper(tmp_path):
    init_vault(tmp_path)
    path = write_paper(tmp_path, _paper("K-20260714-001", "Original summary."))
    page = FakePage()
    root = build_paper_page(_ctx(page, tmp_path), path)
    _text_field(root, "Summary").value = "Local unsaved change."

    source_bytes = path.read_bytes()
    external = read_paper(path)
    external.summary = "External editor change."
    external.updated = datetime(2026, 7, 14, 10, 0)
    update_paper(
        tmp_path,
        path,
        external,
        expected_source_bytes=source_bytes,
    )

    _button(root, "保存").on_click(None)

    assert read_paper(path).summary == "External editor change."
    assert "Paper 已在外部修改；未覆盖。请重新打开后决定如何处理。" in _texts(root)


def test_editor_refuses_to_recreate_an_externally_deleted_paper(tmp_path):
    init_vault(tmp_path)
    path = write_paper(tmp_path, _paper("K-20260714-001", "Original summary."))
    root = build_paper_page(_ctx(FakePage(), tmp_path), path)
    _text_field(root, "Summary").value = "Local unsaved change."
    path.unlink()

    _button(root, "保存").on_click(None)

    assert not path.exists()
    assert "Paper 已在外部删除或移动；未保存。请返回本地文件库刷新。" in _texts(root)


def test_editor_refuses_mutation_after_cache_is_swapped_for_a_symlink(tmp_path):
    vault = tmp_path / "vault"
    outside_cache = tmp_path / "outside-cache"
    init_vault(vault)
    path = write_paper(vault, _paper("K-20260714-001", "Original summary."))
    page = FakePage()
    root = build_paper_page(_ctx(page, vault), path)
    _text_field(root, "Summary").value = "Must not escape the Vault."

    (vault / "cache").rename(vault / "cache-original")
    outside_cache.mkdir()
    outside_path = outside_cache / path.name
    outside_path.write_bytes(b"outside sentinel")
    (vault / "cache").symlink_to(outside_cache, target_is_directory=True)

    _button(root, "保存").on_click(None)

    assert outside_path.read_bytes() == b"outside sentinel"
    assert any("symlink" in text for text in _texts(root))


def test_highlight_reorder_is_saved_in_the_visible_order(tmp_path):
    init_vault(tmp_path)
    root = build_paper_page(_ctx(FakePage(), tmp_path))
    code = _text_field(root, "系统编号").value
    _text_field(root, "Summary").value = "Summary."
    _button(root, "+ 添加 Highlight").on_click(None)
    _button(root, "+ 添加 Highlight").on_click(None)
    _text_field(root, "Highlight 1 命名（可选）").value = "First"
    _text_field(root, "Highlight 1 内容").value = "First anchor."
    _text_field(root, "Highlight 2 命名（可选）").value = "Second"
    _text_field(root, "Highlight 2 内容").value = "Second anchor."

    _control_by_key(root, "highlight-move-up-1").on_click(None)
    _button(root, "保存").on_click(None)

    paper = read_paper(tmp_path / "cache" / f"{code}.md")
    assert paper.highlights == [
        Highlight(content="Second anchor.", display_name="Second"),
        Highlight(content="First anchor.", display_name="First"),
    ]


def test_saved_paper_keeps_its_immutable_code_and_has_no_rename_action(tmp_path):
    init_vault(tmp_path)
    source = write_paper(tmp_path, _paper("K-20260714-001", "Summary."))
    root = build_paper_page(_ctx(FakePage(), tmp_path), source)

    assert _text_field(root, "系统编号").value == "K-20260714-001"
    assert _text_field(root, "系统编号").read_only is True
    assert source.exists()
    with pytest.raises(AssertionError, match="TextField not found"):
        _text_field(root, "新代号")
    with pytest.raises(AssertionError, match="Button not found"):
        _button(root, "重命名")


def test_flashcard_is_summary_first_read_only_and_never_remembers_position(tmp_path):
    init_vault(tmp_path)
    paper = _paper(
        "K-20260714-001",
        "Current Summary.",
        display_name="Night Train",
        highlights=[
            Highlight(content="First writing anchor.", display_name="Window"),
            Highlight(content="Second writing anchor."),
        ],
    )
    path = write_paper(tmp_path, paper)
    page = FakePage()
    ctx = _ctx(page, tmp_path)
    opened: dict[str, Path] = {}
    ctx.open_paper = lambda opened_path: opened.update(path=opened_path)

    root = build_flashcard_page(ctx, path.relative_to(tmp_path))
    assert "Current Summary." in _texts(root)
    assert "1 / 3" in _texts(root)
    assert [
        control.key
        for control in _walk(root)
        if isinstance(control, ft.TextField)
    ] == ["flashcard-jump-page"]

    _button(root, "下一张").on_click(None)
    assert "First writing anchor." in _texts(root)
    assert "Window" in _texts(root)
    assert f"Night Train ({paper.code})" in _texts(root)
    assert "2 / 3" in _texts(root)
    assert _control_by_key(root, "flashcard-summary-context").visible is False

    _button(root, "查看当前 Summary").on_click(None)
    assert _control_by_key(root, "flashcard-summary-context").visible is True
    _button(root, "返回 Paper").on_click(None)
    assert opened["path"] == path.relative_to(tmp_path)

    reopened = build_flashcard_page(
        _ctx(FakePage(), tmp_path),
        path.relative_to(tmp_path),
    )
    assert "1 / 3" in _texts(reopened)
    assert read_paper(path).summary == "Current Summary."


def test_flashcard_list_jump_arrows_edges_and_paper_switch_reset(
    tmp_path,
    monkeypatch,
):
    init_vault(tmp_path)
    first = _paper(
        "K-20260714-001",
        "First Summary.",
        display_name="First Paper",
        highlights=[
            Highlight(content="First anchor.", display_name="Named anchor"),
            Highlight(content="Second anchor."),
        ],
    )
    second = _paper(
        "K-20260714-002",
        "Second Summary.",
        display_name="Second Paper",
        highlights=[Highlight(content="Other anchor.")],
    )
    first_path = write_paper(tmp_path, first)
    second_path = write_paper(tmp_path, second)
    page = FakePage()
    root = build_flashcard_page(
        _ctx(page, tmp_path),
        first_path.relative_to(tmp_path),
    )

    _control_by_key(root, "flashcard-list-2").on_click(None)
    assert "Second anchor." in _texts(root)
    assert "Highlight 2" in _texts(root)
    assert "3 / 3" in _texts(root)

    jump = _control_by_key(root, "flashcard-jump-page")
    jump.value = "0"
    _button(root, "跳转").on_click(None)
    assert "3 / 3" in _texts(root)
    assert _control_by_key(root, "flashcard-notice").value == "页码范围是 1..3。"

    jump.value = "2"
    jump.on_submit(None)
    assert "First anchor." in _texts(root)
    assert "2 / 3" in _texts(root)

    page.on_keyboard_event(SimpleNamespace(key="Arrow Left", meta=False))
    assert "First Summary." in _texts(root)
    page.on_keyboard_event(SimpleNamespace(key="Arrow Left", meta=False))
    feedback = _control_by_key(root, "flashcard-notice")
    assert feedback.value == "已经是第一张。"
    assert page.tasks

    async def no_delay(_: float) -> None:
        return None

    monkeypatch.setattr(flashcard_page_mod.asyncio, "sleep", no_delay)
    handler, args = page.tasks[-1]
    asyncio.run(handler(*args))
    assert feedback.value == ""

    selector = _control_by_key(root, "flashcard-paper-selector")
    assert [option.text for option in selector.options] == [
        f"First Paper ({first.code})",
        f"Second Paper ({second.code})",
    ]
    selector.value = str(second_path.relative_to(tmp_path))
    selector.on_select(None)
    assert "Second Summary." in _texts(root)
    assert "1 / 2" in _texts(root)


def test_flashcard_navigation_without_context_selects_the_first_paper(tmp_path):
    init_vault(tmp_path)
    paper = _paper("K-20260714-001", "First available Summary.")
    write_paper(tmp_path, paper)

    root = build_flashcard_page(_ctx(FakePage(), tmp_path))

    assert "First available Summary." in _texts(root)
    assert "1 / 1" in _texts(root)


def test_flashcard_rejects_a_symlinked_cache_before_reading_outside(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    outside_vault = tmp_path / "outside-vault"
    init_vault(vault)
    init_vault(outside_vault)
    paper = _paper("K-20260714-001", "Outside secret summary.")
    write_paper(outside_vault, paper)
    (vault / "cache").rename(vault / "cache-original")
    (vault / "cache").symlink_to(outside_vault / "cache", target_is_directory=True)
    reads: list[Path] = []
    real_read = flashcard_page_mod.read_paper

    def tracked_read(path: Path) -> Paper:
        reads.append(path)
        return real_read(path)

    monkeypatch.setattr(flashcard_page_mod, "read_paper", tracked_read)
    root = build_flashcard_page(
        _ctx(FakePage(), vault),
        Path("cache") / f"{paper.code}.md",
    )

    assert reads == []
    assert "Outside secret summary." not in _texts(root)
    assert "尚未打开 Paper" in _texts(root)


def test_shell_flashcard_rejects_a_traversal_path_before_any_read(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    init_vault(vault)
    page = FakePage()
    captured: list[AppContext] = []
    reads: list[Path] = []

    def capture_library(ctx: AppContext) -> ft.Control:
        captured.append(ctx)
        return ft.Column()

    def tracked_read(path: Path) -> Paper:
        reads.append(path)
        raise AssertionError("invalid code must not reach Paper I/O")

    monkeypatch.setattr(app_main, "build_library_page", capture_library)
    monkeypatch.setattr(flashcard_page_mod, "read_paper", tracked_read)
    app_main._build_shell(page, vault)  # type: ignore[attr-defined, arg-type]
    _control_by_key(page.controls[0], "shell-nav-2").on_click(None)

    captured[0].open_flashcards(Path("../../outside"))

    assert reads == []
    assert _control_by_key(page.controls[0], "shell-nav-2").bgcolor is not None


def test_library_opens_flashcard_with_the_selected_paper_path(tmp_path):
    init_vault(tmp_path)
    paper = _paper("K-20260714-001", "Focus this paper.")
    write_paper(tmp_path, paper)
    rebuild_index(tmp_path)
    ctx = _ctx(FakePage(), tmp_path)
    opened: list[Path | None] = []
    ctx.open_flashcards = lambda path: opened.append(path)

    root = build_library_page(ctx)
    _button(root, "打开 Flashcard").on_click(None)

    assert opened == [Path("cache") / f"{paper.code}.md"]


def test_folder_paper_round_trips_through_editor_library_and_flashcard(tmp_path):
    init_vault(tmp_path)
    folder = tmp_path / "cache" / "夜行列车"
    folder.mkdir()
    paper = _paper("K-20260714-001", "Folder summary.")
    path = write_paper(
        tmp_path,
        paper,
        destination="cache/夜行列车/K-20260714-001.md",
    )
    page = FakePage()
    ctx = _ctx(page, tmp_path)

    editor = build_paper_page(ctx, path.relative_to(tmp_path))
    _text_field(editor, "Summary").value = "Updated folder summary."
    _button(editor, "保存").on_click(None)
    assert read_paper(path).summary == "Updated folder summary."

    flashcard = build_flashcard_page(ctx, path.relative_to(tmp_path))
    assert "Updated folder summary." in _texts(flashcard)

    opened: list[Path | None] = []
    ctx.open_flashcards = lambda selected: opened.append(selected)
    library = build_library_page(ctx)
    _button(library, "打开 Flashcard").on_click(None)
    assert opened == [Path("cache/夜行列车/K-20260714-001.md")]


def test_library_vault_switch_cancel_returns_to_the_current_shell(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    app_main._build_shell(page, tmp_path)  # type: ignore[attr-defined, arg-type]
    _control_by_key(page.controls[0], "shell-nav-2").on_click(None)

    assert str(tmp_path.resolve()) in _texts(page.controls[0])
    assert "写入仅允许当前用户 Home 内路径；尚未启用 Apple App Sandbox。" in _texts(
        page.controls[0]
    )
    _button(page.controls[0], "更换 Vault…").on_click(None)
    assert _control_by_key(page.controls[0], "vault-picker-paper-card")
    assert _text_field(page.controls[0], "Vault 文件夹路径").value == str(tmp_path.resolve())

    _button(page.controls[0], "取消").on_click(None)
    assert _control_by_key(page.controls[0], "shell-sidebar")
    assert all(
        _button(page.controls[0], label)
        for label in ["纸片", "Flashcard", "本地文件库"]
    )


def test_library_opens_supported_vault_without_existing_trash(tmp_path):
    init_vault(tmp_path)
    path = write_paper(tmp_path, _paper("K-20260714-001", "Legacy layout."))
    rebuild_index(tmp_path)
    (tmp_path / ".trash" / "cache").rmdir()
    (tmp_path / ".trash").rmdir()

    root = build_library_page(_ctx(FakePage(), tmp_path))

    assert "Trash · 0" in _texts(root)
    _button(root, "删除").on_click(None)
    assert not path.exists()
    assert (tmp_path / ".trash/cache/K-20260714-001.md").is_file()
    assert "Trash · 1" in _texts(root)


def test_library_searches_code_summary_and_tags_and_opens_paper(tmp_path):
    init_vault(tmp_path)
    first = write_paper(tmp_path, _paper("K-20260714-001", "Platform farewell.", ["rain"]))
    write_paper(tmp_path, _paper("K-20260714-002", "Kitchen reunion.", ["home"]))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = _ctx(page, tmp_path)
    opened: dict[str, Path] = {}
    ctx.open_paper = lambda path: opened.update(path=path)
    root = build_library_page(ctx)
    search = _text_field(root, "搜索名称、代号、Summary、Tags 或 Highlight 名称")

    search.value = "rain"
    search.on_change(None)
    assert "Platform farewell." in _texts(root)
    assert "Kitchen reunion." not in _texts(root)

    search.value = "K-20260714-001"
    search.on_change(None)
    _button(root, "编辑").on_click(None)
    assert opened["path"] == first.relative_to(tmp_path)


def test_library_delete_and_restore_are_reachable_from_the_ui(tmp_path):
    init_vault(tmp_path)
    path = write_paper(tmp_path, _paper("K-20260714-001", "Keep this paper."))
    rebuild_index(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path))

    _button(root, "删除").on_click(None)
    assert not path.exists()
    assert "Trash · 1" in _texts(root)

    _button(root, "Trash · 1").on_click(None)
    _button(root, "恢复").on_click(None)
    assert path.exists()
    assert "Trash · 0" in _texts(root)


def test_library_recovery_blocks_code_collision_without_rewriting_history(tmp_path):
    init_vault(tmp_path)
    deleted = write_paper(tmp_path, _paper("K-20260714-001", "Deleted paper."))
    soft_delete(tmp_path, str(deleted.relative_to(tmp_path)))
    active = _paper("K-20260714-001", "Active paper.")
    active.initial_summary = active.summary
    (tmp_path / "cache" / "K-20260714-001.md").write_bytes(
        render_paper_bytes(active)
    )
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))

    _button(root, "Trash · 1").on_click(None)
    _button(root, "恢复").on_click(None)
    assert any("代号冲突" in text for text in _texts(root))
    assert not (tmp_path / "cache" / "K-20260714-002.md").exists()
    assert (tmp_path / ".trash" / "cache" / "K-20260714-001.md").exists()


def test_library_delegates_open_and_reveal_to_macos_system_commands(tmp_path, monkeypatch):
    init_vault(tmp_path)
    path = write_paper(tmp_path, _paper("K-20260714-001", "Open externally."))
    rebuild_index(tmp_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(library_page_mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        library_page_mod.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )
    root = build_library_page(_ctx(FakePage(), tmp_path))

    _control_by_key(root, f"paper-open-{path.relative_to(tmp_path)}").on_click(None)
    _control_by_key(root, f"paper-reveal-{path.relative_to(tmp_path)}").on_click(None)

    assert calls == [["open", str(path)], ["open", "-R", str(path)]]


def test_library_revalidates_the_vault_before_revealing_it(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    init_vault(vault)
    page = FakePage()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        library_page_mod.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )
    root = build_library_page(_ctx(page, vault))
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault / "late-link").symlink_to(outside, target_is_directory=True)

    _button(root, "在文件夹中显示").on_click(None)

    assert calls == []
    assert "symlink" in _texts(page.overlay[-1])[0]


def test_library_rejects_an_absolute_index_path_for_every_file_action(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    init_vault(vault)
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside sentinel")
    crafted_entry = {
        "code": "K-20260714-999",
        "path": str(outside),
        "summary": "Crafted index entry.",
        "tags": [],
        "created": "2026-07-14T09:00:00",
        "updated": "2026-07-14T09:00:00",
    }
    (vault / "keikeu_index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "papers": [crafted_entry],
                "errors": [],
            }
        ),
        encoding="utf-8",
    )
    page = FakePage()
    ctx = _ctx(page, vault)
    opened: list[Path | None] = []
    ctx.open_paper = lambda path: opened.append(path)
    # Exercise the UI boundary even though the core index loader also rejects
    # and rebuilds this crafted entry.
    monkeypatch.setattr(library_page_mod, "list_papers", lambda _vault: [crafted_entry])
    monkeypatch.setattr(
        library_page_mod.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("outside path must not reach the OS")
        ),
    )
    root = build_library_page(ctx)

    _button(root, "编辑").on_click(None)
    _control_by_key(root, f"paper-open-{outside}").on_click(None)
    _control_by_key(root, f"paper-reveal-{outside}").on_click(None)
    _button(root, "删除").on_click(None)

    assert opened == []
    assert outside.read_bytes() == b"outside sentinel"
    assert all("outside the selected Vault" in _texts(bar)[0] for bar in page.overlay[-4:])


def test_shell_show_paper_rejects_an_absolute_path_outside_the_vault(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    init_vault(vault)
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside sentinel")
    page = FakePage()
    captured: list[AppContext] = []
    library_handler = lambda _event: None

    def capture_library(ctx: AppContext) -> ft.Control:
        captured.append(ctx)
        assert ctx.library_scope_host is not None
        ctx.library_scope_host.controls = [
            ft.Text("scope sentinel", key="scope-sentinel")
        ]
        ctx.page.on_keyboard_event = library_handler
        return ft.Column(controls=[ft.Text("library sentinel")])

    monkeypatch.setattr(app_main, "build_library_page", capture_library)
    app_main._build_shell(page, vault)  # type: ignore[attr-defined, arg-type]
    _control_by_key(page.controls[0], "shell-nav-2").on_click(None)

    captured[0].open_paper(outside)

    assert _control_by_key(page.controls[0], "shell-nav-2").bgcolor is not None
    assert _control_by_key(page.controls[0], "scope-sentinel")
    assert page.on_keyboard_event is library_handler
    assert "library sentinel" in _texts(page.controls[0])
    assert outside.read_bytes() == b"outside sentinel"
    assert "outside the selected Vault" in _texts(page.overlay[-1])[0]


def test_library_displays_parse_errors_and_recovery_action(tmp_path):
    init_vault(tmp_path)
    broken = tmp_path / "cache" / "K-20260714-001.md"
    broken.write_text("---\ntype: paper\n---\nbroken", encoding="utf-8")
    trashed = write_paper(tmp_path, _paper("K-20260714-002", "Recoverable."))
    soft_delete(tmp_path, str(trashed.relative_to(tmp_path)))
    rebuild_index(tmp_path)

    root = build_library_page(_ctx(FakePage(), tmp_path))

    assert any("损坏 Paper" in text for text in _texts(root))
    assert "冲突时的新代号" not in [
        field.label for field in _walk(root) if isinstance(field, ft.TextField)
    ]
    _button(root, "Trash · 1").on_click(None)
    assert _button(root, "恢复")


def test_highlight_drag_handle_reorders_without_a_toast(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    root = build_paper_page(_ctx(page, tmp_path))
    code = _text_field(root, "系统编号").value
    _text_field(root, "Summary").value = "Summary."
    _button(root, "+ 添加 Highlight").on_click(None)
    _button(root, "+ 添加 Highlight").on_click(None)
    _text_field(root, "Highlight 1 内容").value = "First."
    _text_field(root, "Highlight 2 内容").value = "Second."

    _control_by_key(root, "highlight-drag-1").on_drag_start(None)
    _control_by_key(root, "highlight-drop-0").on_accept(None)
    _button(root, "保存").on_click(None)

    assert read_paper(tmp_path / "cache" / f"{code}.md").highlights == [
        Highlight(content="Second."),
        Highlight(content="First."),
    ]
    assert not any("顺序" in text for overlay in page.overlay for text in _texts(overlay))


def test_library_scopes_search_names_and_clear_selection_on_scope_change(
    tmp_path,
    monkeypatch,
):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    root_path = write_paper(
        tmp_path,
        _paper(
            "K-20260714-001",
            "Root summary.",
            display_name="Root Name",
            highlights=[Highlight(content="body", display_name="Signal")],
        ),
    )
    folder_path = write_paper(
        tmp_path,
        _paper("K-20260714-002", "Folder summary."),
        destination="cache/A/K-20260714-002.md",
    )
    rebuild_index(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path))
    search = _control_by_key(root, "library-search")

    search.value = "Signal"
    search.on_change(None)
    assert "Root Name" in _texts(root)
    assert "Folder summary." not in _texts(root)

    search.value = ""
    search.on_change(None)
    checkbox = _control_by_key(root, f"paper-select-{root_path.relative_to(tmp_path)}")
    checkbox.value = True
    checkbox.on_change(None)
    _control_by_key(root, "library-scope-folder:A").on_click(None)

    assert "已取消选择的 1 个 Paper" in _texts(root)
    assert "Folder summary." in _texts(root)
    assert "Root summary." not in _texts(root)
    assert folder_path.exists()
    assert len(page.tasks) == 1

    async def no_delay(_seconds: float) -> None:
        return None

    monkeypatch.setattr(library_page_mod.asyncio, "sleep", no_delay)
    handler, args = page.tasks[0]
    asyncio.run(handler(*args))
    assert "已取消选择的 1 个 Paper" not in _texts(root)


def test_library_search_normalizes_unicode_and_does_not_index_none(tmp_path):
    init_vault(tmp_path)
    write_paper(
        tmp_path,
        _paper(
            "K-20260714-001",
            "Named summary.",
            display_name="Cafe\u0301",
        ),
    )
    write_paper(tmp_path, _paper("K-20260714-002", "Ordinary unnamed summary."))
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))
    search = _control_by_key(root, "library-search")

    search.value = "Café"
    search.on_change(None)
    assert "Cafe\u0301" in _texts(root)
    assert "Ordinary unnamed summary." not in _texts(root)

    search.value = "none"
    search.on_change(None)
    assert "Ordinary unnamed summary." not in _texts(root)
    assert "当前范围没有符合搜索条件的 Paper。" in _texts(root)


def test_library_drag_and_menu_move_share_the_same_core_path(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    create_folder(tmp_path, "B")
    first = write_paper(tmp_path, _paper("K-20260714-001", "First."))
    second = write_paper(tmp_path, _paper("K-20260714-002", "Second."))
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))

    _control_by_key(
        root,
        f"paper-drag-{first.relative_to(tmp_path)}",
    ).on_drag_start(None)
    _control_by_key(root, "library-drop-folder:A").on_accept(None)
    assert (tmp_path / "cache" / "A" / first.name).exists()

    menu = _control_by_key(root, f"paper-menu-{second.relative_to(tmp_path)}")
    _popup_item(menu, "移动到：B").on_click(None)
    assert (tmp_path / "cache" / "B" / second.name).exists()
    context_menu = _control_by_key(
        root,
        f"paper-context-menu-{(Path('cache') / 'B' / second.name)}",
    )
    assert "移动到：A" in [item.content for item in context_menu.items]


def test_library_batch_unfiled_sentinel_does_not_hide_same_named_folder(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "__unfiled__")
    paper = write_paper(tmp_path, _paper("K-20260714-001", "Move me."))
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))

    checkbox = _control_by_key(
        root,
        f"paper-select-{paper.relative_to(tmp_path)}",
    )
    checkbox.value = True
    checkbox.on_change(None)
    destination = _control_by_key(root, "library-batch-destination")
    destination.value = "__unfiled__"
    _button(root, "移动所选").on_click(None)

    assert (tmp_path / "cache" / "__unfiled__" / paper.name).exists()


def test_library_stale_move_target_refreshes_instead_of_raising(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    paper = write_paper(tmp_path, _paper("K-20260714-001", "Stay safe."))
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))
    (tmp_path / "cache" / "A").rmdir()

    checkbox = _control_by_key(
        root,
        f"paper-select-{paper.relative_to(tmp_path)}",
    )
    checkbox.value = True
    checkbox.on_change(None)
    destination = _control_by_key(root, "library-batch-destination")
    destination.value = "A"
    _button(root, "移动所选").on_click(None)

    assert paper.exists()
    assert any("移动失败" in text and "已刷新 Library" in text for text in _texts(root))
    assert "A" not in [
        option.key
        for option in _control_by_key(
            root,
            "library-batch-destination",
        ).options
    ]


def test_library_batch_move_reports_partial_results(tmp_path, monkeypatch):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    first = write_paper(tmp_path, _paper("K-20260714-001", "First."))
    second = write_paper(tmp_path, _paper("K-20260714-002", "Second."))
    third = write_paper(tmp_path, _paper("K-20260714-003", "Third."))
    rebuild_index(tmp_path)
    calls: list[list[str]] = []

    def partial(_vault, paths, _folder):
        records = list(paths)
        calls.append(records)
        return [
            PathOperationResult(
                source=Path(records[0]),
                destination=Path("cache/A") / Path(records[0]).name,
            ),
            PathOperationResult(
                source=Path(records[1]),
                error="injected provider failure",
            ),
            PathOperationResult(
                source=Path(records[2]),
                error="second injected failure",
            ),
        ]

    monkeypatch.setattr(library_page_mod, "move_papers", partial)
    root = build_library_page(_ctx(FakePage(), tmp_path))
    _button(root, "全选当前").on_click(None)
    destination = _control_by_key(root, "library-batch-destination")
    destination.value = "A"
    _button(root, "移动所选").on_click(None)

    assert calls == [[
        str(first.relative_to(tmp_path)),
        str(second.relative_to(tmp_path)),
        str(third.relative_to(tmp_path)),
    ]]
    assert any("1 项成功，2 项失败" in text for text in _texts(root))
    assert any("injected provider failure" in text for text in _texts(root))
    assert any("second injected failure" in text for text in _texts(root))
    assert any(str(second.relative_to(tmp_path)) in text for text in _texts(root))
    assert any(str(third.relative_to(tmp_path)) in text for text in _texts(root))


def test_library_branch_copy_uses_saved_paper_and_stays_in_folder(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    source = write_paper(
        tmp_path,
        _paper(
            "K-20260714-001",
            "Saved summary.",
            display_name="Source",
        ),
        destination="cache/A/K-20260714-001.md",
    )
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))
    menu = _control_by_key(root, f"paper-menu-{source.relative_to(tmp_path)}")

    _popup_item(menu, "复制分支").on_click(None)

    papers = sorted((tmp_path / "cache" / "A").glob("*.md"))
    assert len(papers) == 2
    branch = next(path for path in papers if path != source)
    assert read_paper(branch).display_name == "Source · 分支"
    assert read_paper(branch).summary == "Saved summary."


def test_library_rename_to_existing_folder_requires_merge_confirmation(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    create_folder(tmp_path, "B")
    paper = write_paper(
        tmp_path,
        _paper("K-20260714-001", "Merge me."),
        destination="cache/A/K-20260714-001.md",
    )
    rebuild_index(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path))
    menu = _control_by_key(root, "folder-menu-A")
    context_menu = _control_by_key(root, "folder-context-menu-A")
    assert [item.content for item in context_menu.items] == [
        "重命名",
        "移至 Trash",
    ]

    _popup_item(menu, "重命名").on_click(None)
    rename_dialog = page.dialogs[-1]
    _text_field(rename_dialog, "文件夹新名称").value = "B"
    _button(rename_dialog, "重命名").on_click(None)
    merge_dialog = page.dialogs[-1]
    assert "合并同名文件夹" in _texts(merge_dialog)
    _button(merge_dialog, "确认合并").on_click(None)

    assert not (tmp_path / "cache" / "A").exists()
    assert (tmp_path / "cache" / "B" / paper.name).exists()
    assert any("1 项成功" in text for text in _texts(root))


def test_library_empty_folder_merge_reports_success(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    create_folder(tmp_path, "B")
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path))

    _popup_item(_control_by_key(root, "folder-menu-A"), "重命名").on_click(None)
    rename_dialog = page.dialogs[-1]
    _text_field(rename_dialog, "文件夹新名称").value = "B"
    _button(rename_dialog, "重命名").on_click(None)
    _button(page.dialogs[-1], "确认合并").on_click(None)

    assert not (tmp_path / "cache" / "A").exists()
    assert "合并文件夹：空文件夹已合并" in _texts(root)


def test_library_folder_mutation_clears_selection_from_all_scope(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    paper = write_paper(
        tmp_path,
        _paper("K-20260714-001", "Selected."),
        destination="cache/A/K-20260714-001.md",
    )
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))
    checkbox = _control_by_key(
        root,
        f"paper-select-{paper.relative_to(tmp_path)}",
    )
    checkbox.value = True
    checkbox.on_change(None)

    _popup_item(_control_by_key(root, "folder-menu-A"), "移至 Trash").on_click(None)

    assert "已选择 0" in _texts(root)
    assert "已取消选择的 1 个 Paper" in _texts(root)


def test_library_folder_mutation_keeps_notice_when_scope_falls_back(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    paper = write_paper(
        tmp_path,
        _paper("K-20260714-001", "Selected."),
        destination="cache/A/K-20260714-001.md",
    )
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))
    _control_by_key(root, "library-scope-folder:A").on_click(None)
    checkbox = _control_by_key(
        root,
        f"paper-select-{paper.relative_to(tmp_path)}",
    )
    checkbox.value = True
    checkbox.on_change(None)

    _popup_item(_control_by_key(root, "folder-menu-A"), "移至 Trash").on_click(None)

    assert "全部 Paper · 0" in _texts(root)
    assert "已取消选择的 1 个 Paper" in _texts(root)


def test_library_permanent_delete_threshold_requires_exact_execute(tmp_path):
    init_vault(tmp_path)
    paths = [
        write_paper(
            tmp_path,
            _paper(f"K-20260714-{index:03d}", f"Paper {index}."),
        )
        for index in range(1, 5)
    ]
    for path in paths:
        soft_delete(tmp_path, path.relative_to(tmp_path))
    rebuild_index(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path), initial_scope="trash")

    _button(root, "清空 Trash").on_click(None)
    dialog = page.dialogs[-1]
    execute = _text_field(dialog, "输入 execute")
    execute.value = " EXECUTE "
    _button(dialog, "永久删除").on_click(None)
    assert any("完全一致" in text for text in _texts(dialog))
    assert len(list((tmp_path / ".trash" / "cache").glob("*.md"))) == 4

    execute.value = " execute "
    _button(dialog, "永久删除").on_click(None)
    assert list((tmp_path / ".trash" / "cache").glob("*.md")) == []


def test_library_single_permanent_delete_uses_confirmation_without_execute(tmp_path):
    init_vault(tmp_path)
    path = write_paper(
        tmp_path,
        _paper("K-20260714-001", "One.", display_name="Named"),
    )
    soft_delete(tmp_path, path.relative_to(tmp_path))
    rebuild_index(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path), initial_scope="trash")

    _button(root, "永久删除").on_click(None)
    dialog = page.dialogs[-1]

    assert any(
        "Named (K-20260714-001)" in text for text in _texts(dialog)
    )
    assert not any(
        isinstance(control, ft.TextField) and control.label == "输入 execute"
        for control in _walk(dialog)
    )


def test_library_trash_folder_is_expandable(tmp_path):
    init_vault(tmp_path)
    create_folder(tmp_path, "A")
    write_paper(
        tmp_path,
        _paper("K-20260714-001", "Folder Trash."),
        destination="cache/A/K-20260714-001.md",
    )
    soft_delete_folder(tmp_path, "A")
    rebuild_index(tmp_path)

    root = build_library_page(_ctx(FakePage(), tmp_path), initial_scope="trash")
    folder = _control_by_key(root, "trash-folder-A")

    assert isinstance(folder, ft.ExpansionTile)
    assert _button(folder, "恢复文件夹")
    assert _button(folder, "永久删除文件夹")


def test_library_trash_scope_searches_and_sorts_visible_papers(tmp_path):
    init_vault(tmp_path)
    zulu = write_paper(
        tmp_path,
        _paper("K-20260714-001", "Zulu summary.", display_name="Zulu"),
    )
    alpha = write_paper(
        tmp_path,
        _paper("K-20260714-002", "Alpha summary.", display_name="Alpha"),
    )
    soft_delete(tmp_path, zulu.relative_to(tmp_path))
    soft_delete(tmp_path, alpha.relative_to(tmp_path))
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path), initial_scope="trash")

    sort = _control_by_key(root, "library-sort")
    sort.value = "name"
    sort.on_select(None)
    texts = _texts(root)
    assert texts.index("Alpha (K-20260714-002)") < texts.index(
        "Zulu (K-20260714-001)"
    )

    search = _control_by_key(root, "library-search")
    search.value = "Zulu"
    search.on_change(None)
    assert "Zulu (K-20260714-001)" in _texts(root)
    assert "Alpha (K-20260714-002)" not in _texts(root)
    search.value = "definitely-no-match"
    search.on_change(None)
    assert "Trash 中没有符合搜索条件的 Paper。" in _texts(root)


def test_library_cmd_f_focuses_search(tmp_path, monkeypatch):
    init_vault(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path))
    search = _control_by_key(root, "library-search")
    async def focus() -> None:
        return None

    monkeypatch.setattr(search, "focus", focus)

    page.on_keyboard_event(SimpleNamespace(key="F", meta=True))

    assert page.tasks[-1] == (focus, ())


def test_paper_cmd_s_saves_the_current_form(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    root = build_paper_page(_ctx(page, tmp_path))
    _text_field(root, "Summary").value = "Saved from keyboard."

    page.on_keyboard_event(SimpleNamespace(key="S", meta=True))

    saved = list((tmp_path / "cache").glob("*.md"))
    assert len(saved) == 1
    assert read_paper(saved[0]).summary == "Saved from keyboard."


def test_escape_closes_the_top_library_dialog(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    build_library_page(_ctx(page, tmp_path))
    first = ft.AlertDialog()
    second = ft.AlertDialog()
    page.show_dialog(first)
    page.show_dialog(second)

    page.on_keyboard_event(SimpleNamespace(key="Escape", meta=False))

    assert first.open is True
    assert second.open is False


def test_library_creates_two_folders_with_managed_dialogs(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path))

    _button(root, "新建文件夹").on_click(None)
    first_dialog = page.dialogs[-1]
    _text_field(first_dialog, "新文件夹名称").value = "First"
    _button(first_dialog, "创建").on_click(None)

    _button(root, "新建文件夹").on_click(None)
    second_dialog = page.dialogs[-1]
    _text_field(second_dialog, "新文件夹名称").value = "Second"
    _button(second_dialog, "创建").on_click(None)

    assert (tmp_path / "cache" / "First").is_dir()
    assert (tmp_path / "cache" / "Second").is_dir()
    assert first_dialog.open is False
    assert second_dialog.open is False
