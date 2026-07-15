"""Headless Flet contracts for the Paper v2 editor and Library."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

import flet as ft

from keikeu_app import main as app_main
from keikeu_app.main import AppContext
from keikeu_app.pages import library_page as library_page_mod
from keikeu_app.pages.library_page import build_library_page
from keikeu_app.pages.paper_page import build_paper_page
from keikeu_core.indexer import rebuild_index
from keikeu_core.markdown_io import read_paper, write_paper
from keikeu_core.models import Paper
from keikeu_core.vault import init_vault, soft_delete


class FakePage:
    """The small subset of ``ft.Page`` exercised by the page builders."""

    def __init__(self) -> None:
        self.controls: list[object] = []
        self.overlay: list[object] = []
        self.services: list[object] = []
        self.scroll = ft.ScrollMode.AUTO
        self.update_count = 0
        self.theme: ft.Theme | None = None
        self.bgcolor: str | None = None
        self.title = ""
        self.window = SimpleNamespace(width=None, height=None)

    def add(self, *controls: object) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.update_count += 1


def _walk(control: object) -> Iterable[object]:
    yield control
    for attr in ("content", "leading", "trailing", "title", "subtitle"):
        child = getattr(control, attr, None)
        if child is not None:
            yield from _walk(child)
    for child in getattr(control, "actions", []) or []:
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


def _texts(root: object) -> list[str]:
    return [
        control.value
        for control in _walk(root)
        if isinstance(control, ft.Text) and isinstance(control.value, str)
    ]


def _paper(code: str, summary: str, tags: list[str] | None = None) -> Paper:
    return Paper(
        code=code,
        initial_summary="",
        summary=summary,
        highlights=[],
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
    rail = next(control for control in _walk(page.controls[0]) if isinstance(control, ft.NavigationRail))
    labels = [destination.label for destination in rail.destinations]
    assert labels == ["纸片", "Flashcard", "本地文件库"]
    assert "配方票编辑" not in labels


def test_paper_page_exposes_only_v2_fields(tmp_path):
    init_vault(tmp_path)
    root = build_paper_page(_ctx(FakePage(), tmp_path))

    assert _text_field(root, "Paper 代号").value.startswith("K-")
    assert _text_field(root, "Summary")
    assert _text_field(root, "Tags（用逗号分隔）")
    assert "初稿副本会在首次保存后冻结，只读保留。" in _texts(root)
    assert not any(label in {"标题", "原始灵感", "临时备注"} for label in [
        field.label for field in _walk(root) if isinstance(field, ft.TextField)
    ])
    assert _control_by_key(root, "paper-editor-card")


def test_empty_summary_does_not_create_a_paper(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    root = build_paper_page(_ctx(page, tmp_path))

    _text_field(root, "Paper 代号").value = "K-20260714-001"
    _button(root, "保存").on_click(None)

    assert list((tmp_path / "cache").glob("*.md")) == []
    assert "Summary 不能为空。" in _texts(root)


def test_save_reopen_and_update_preserves_first_draft(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    root = build_paper_page(_ctx(page, tmp_path))
    _text_field(root, "Paper 代号").value = "K-20260714-001"
    _text_field(root, "Summary").value = "First draft summary."
    _text_field(root, "Tags（用逗号分隔）").value = "rain, station, rain"
    _button(root, "+ 添加 Highlight").on_click(None)
    _text_field(root, "Highlight 1").value = "A held breath."

    _button(root, "保存").on_click(None)
    path = tmp_path / "cache" / "K-20260714-001.md"
    paper = read_paper(path)
    assert paper.initial_summary == "First draft summary."
    assert paper.highlights == ["A held breath."]
    assert paper.tags == ["rain", "station"]

    reopened = build_paper_page(_ctx(page, tmp_path), path)
    assert _text_field(reopened, "Paper 代号").read_only is True
    _text_field(reopened, "Summary").value = "Edited current summary."
    _button(reopened, "保存").on_click(None)

    updated = read_paper(path)
    assert updated.initial_summary == "First draft summary."
    assert updated.summary == "Edited current summary."


def test_highlight_reorder_is_saved_in_the_visible_order(tmp_path):
    init_vault(tmp_path)
    root = build_paper_page(_ctx(FakePage(), tmp_path))
    _text_field(root, "Paper 代号").value = "K-20260714-001"
    _text_field(root, "Summary").value = "Summary."
    _button(root, "+ 添加 Highlight").on_click(None)
    _button(root, "+ 添加 Highlight").on_click(None)
    _text_field(root, "Highlight 1").value = "First anchor."
    _text_field(root, "Highlight 2").value = "Second anchor."

    _control_by_key(root, "highlight-move-up-1").on_click(None)
    _button(root, "保存").on_click(None)

    paper = read_paper(tmp_path / "cache" / "K-20260714-001.md")
    assert paper.highlights == ["Second anchor.", "First anchor."]


def test_rename_is_explicit_and_rebuilds_the_library_index(tmp_path):
    init_vault(tmp_path)
    source = write_paper(tmp_path, _paper("K-20260714-001", "Summary."))
    rebuild_index(tmp_path)
    root = build_paper_page(_ctx(FakePage(), tmp_path), source)

    _text_field(root, "新代号").value = "K-20260714-002"
    _button(root, "重命名").on_click(None)

    target = tmp_path / "cache" / "K-20260714-002.md"
    assert not source.exists()
    assert read_paper(target).code == "K-20260714-002"
    assert "K-20260714-002" in [entry["code"] for entry in rebuild_index(tmp_path)["papers"]]


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
    search = _text_field(root, "搜索代号、Summary 或 Tags")

    search.value = "rain"
    search.on_change(None)
    assert "Platform farewell." in _texts(root)
    assert "Kitchen reunion." not in _texts(root)

    search.value = "K-20260714-001"
    search.on_change(None)
    tile = next(control for control in _walk(root) if isinstance(control, ft.ListTile))
    tile.on_click(None)
    assert opened["path"] == first


def test_library_delete_and_restore_are_reachable_from_the_ui(tmp_path):
    init_vault(tmp_path)
    path = write_paper(tmp_path, _paper("K-20260714-001", "Keep this paper."))
    rebuild_index(tmp_path)
    page = FakePage()
    root = build_library_page(_ctx(page, tmp_path))

    _button(root, "删除").on_click(None)
    assert not path.exists()
    assert "回收站 · 1" in _texts(root)

    _button(root, "恢复").on_click(None)
    assert path.exists()
    assert "回收站 · 0" in _texts(root)


def test_library_recovery_accepts_an_explicit_new_code_after_a_collision(tmp_path):
    init_vault(tmp_path)
    deleted = write_paper(tmp_path, _paper("K-20260714-001", "Deleted paper."))
    soft_delete(tmp_path, str(deleted.relative_to(tmp_path)))
    write_paper(tmp_path, _paper("K-20260714-001", "Active paper."))
    rebuild_index(tmp_path)
    root = build_library_page(_ctx(FakePage(), tmp_path))

    _button(root, "恢复").on_click(None)
    assert any("代号冲突" in text for text in _texts(root))
    _text_field(root, "冲突时的新代号").value = "K-20260714-002"
    _button(root, "恢复").on_click(None)

    assert read_paper(tmp_path / "cache" / "K-20260714-002.md").summary == "Deleted paper."


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

    _button(root, "打开").on_click(None)
    _button(root, "在文件夹中显示").on_click(None)

    assert calls == [["open", str(path)], ["open", "-R", str(path)]]


def test_library_displays_parse_errors_and_recovery_conflict_guidance(tmp_path):
    init_vault(tmp_path)
    broken = tmp_path / "cache" / "K-20260714-001.md"
    broken.write_text("---\ntype: paper\n---\nbroken", encoding="utf-8")
    trashed = write_paper(tmp_path, _paper("K-20260714-002", "Recoverable."))
    soft_delete(tmp_path, str(trashed.relative_to(tmp_path)))
    rebuild_index(tmp_path)

    root = build_library_page(_ctx(FakePage(), tmp_path))

    assert any("损坏 Paper" in text for text in _texts(root))
    assert "冲突时的新代号" in [
        field.label for field in _walk(root) if isinstance(field, ft.TextField)
    ]
