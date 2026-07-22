"""Headless Flet contracts for the Paper v3 editor and Library."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

import flet as ft
import pytest

from keikeu_app import main as app_main
from keikeu_app.local_state import get_card_index
from keikeu_app.main import AppContext
from keikeu_app.pages import flashcard_page as flashcard_page_mod
from keikeu_app.pages import library_page as library_page_mod
from keikeu_app.pages.flashcard_page import build_flashcard_page
from keikeu_app.pages.library_page import build_library_page
from keikeu_app.pages.paper_page import build_paper_page
from keikeu_core.indexer import rebuild_index
from keikeu_core.markdown_io import read_paper, update_paper, write_paper
from keikeu_core.models import Highlight, Paper
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
    for child in getattr(control, "items", []) or []:
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


def _ctx(page: FakePage, vault: Path, state_path: Path | None = None) -> AppContext:
    return AppContext(page=page, vault=vault, state_path=state_path)  # type: ignore[arg-type]


def test_shell_uses_paper_flashcard_and_library_navigation(tmp_path):
    init_vault(tmp_path)
    page = FakePage()

    app_main._build_shell(page, tmp_path)  # type: ignore[attr-defined, arg-type]

    assert page.scroll is None
    rail = next(control for control in _walk(page.controls[0]) if isinstance(control, ft.NavigationRail))
    labels = [destination.label for destination in rail.destinations]
    assert labels == ["纸片", "Flashcard", "本地文件库"]
    assert "配方票编辑" not in labels


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


def test_flashcard_is_summary_first_read_only_and_remembers_position(tmp_path):
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
    state_path = tmp_path / "device-state.json"
    page = FakePage()
    ctx = _ctx(page, tmp_path, state_path)
    opened: dict[str, Path] = {}
    ctx.open_paper = lambda opened_path: opened.update(path=opened_path)

    root = build_flashcard_page(ctx, paper.code)
    assert "Current Summary." in _texts(root)
    assert "1 / 3" in _texts(root)
    assert not [control for control in _walk(root) if isinstance(control, ft.TextField)]

    _button(root, "下一张").on_click(None)
    assert "First writing anchor." in _texts(root)
    assert "Window" in _texts(root)
    assert f"Night Train ({paper.code})" in _texts(root)
    assert "2 / 3" in _texts(root)
    assert _control_by_key(root, "flashcard-summary-context").visible is False

    _button(root, "查看当前 Summary").on_click(None)
    assert _control_by_key(root, "flashcard-summary-context").visible is True
    _button(root, "返回 Paper").on_click(None)
    assert opened["path"] == path

    reopened = build_flashcard_page(_ctx(FakePage(), tmp_path, state_path), paper.code)
    assert "2 / 3" in _texts(reopened)
    assert get_card_index(paper.code, 3, state_path) == 1

    state_path.unlink()
    reset_view = build_flashcard_page(_ctx(FakePage(), tmp_path, state_path), paper.code)
    assert "1 / 3" in _texts(reset_view)
    assert read_paper(path).summary == "Current Summary."


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
    root = build_flashcard_page(_ctx(FakePage(), vault), paper.code)

    assert reads == []
    assert "Outside secret summary." not in _texts(root)
    assert "尚未打开 Paper" in _texts(root)


def test_shell_flashcard_rejects_a_traversal_code_before_any_read(tmp_path, monkeypatch):
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
    rail = next(control for control in _walk(page.controls[0]) if isinstance(control, ft.NavigationRail))
    rail.selected_index = 2
    rail.on_change(SimpleNamespace(control=rail))

    captured[0].open_flashcards("../../outside")

    assert reads == []
    assert rail.selected_index == 1
    assert "尚未打开 Paper" in _texts(page.controls[0])


def test_library_opens_flashcard_with_the_selected_paper_code(tmp_path):
    init_vault(tmp_path)
    paper = _paper("K-20260714-001", "Focus this paper.")
    write_paper(tmp_path, paper)
    rebuild_index(tmp_path)
    ctx = _ctx(FakePage(), tmp_path)
    opened: list[str | None] = []
    ctx.open_flashcards = lambda code: opened.append(code)

    root = build_library_page(ctx)
    _button(root, "打开 Flashcard").on_click(None)

    assert opened == [paper.code]


def test_library_vault_switch_cancel_returns_to_the_current_shell(tmp_path):
    init_vault(tmp_path)
    page = FakePage()
    app_main._build_shell(page, tmp_path)  # type: ignore[attr-defined, arg-type]
    rail = next(control for control in _walk(page.controls[0]) if isinstance(control, ft.NavigationRail))
    rail.selected_index = 2
    rail.on_change(SimpleNamespace(control=rail))

    assert str(tmp_path.resolve()) in _texts(page.controls[0])
    assert "写入仅允许当前用户 Home 内路径；尚未启用 Apple App Sandbox。" in _texts(
        page.controls[0]
    )
    _button(page.controls[0], "更换 Vault…").on_click(None)
    assert _control_by_key(page.controls[0], "vault-picker-paper-card")
    assert _text_field(page.controls[0], "Vault 文件夹路径").value == str(tmp_path.resolve())

    _button(page.controls[0], "取消").on_click(None)
    rail = next(control for control in _walk(page.controls[0]) if isinstance(control, ft.NavigationRail))
    assert [destination.label for destination in rail.destinations] == [
        "纸片",
        "Flashcard",
        "本地文件库",
    ]


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
    _button(root, "打开").on_click(None)
    _button(root, "在文件夹中显示").on_click(None)
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

    def capture_library(ctx: AppContext) -> ft.Control:
        captured.append(ctx)
        return ft.Column()

    monkeypatch.setattr(app_main, "build_library_page", capture_library)
    app_main._build_shell(page, vault)  # type: ignore[attr-defined, arg-type]
    rail = next(control for control in _walk(page.controls[0]) if isinstance(control, ft.NavigationRail))
    rail.selected_index = 2
    rail.on_change(SimpleNamespace(control=rail))

    captured[0].open_paper(outside)

    assert rail.selected_index == 2
    assert outside.read_bytes() == b"outside sentinel"
    assert "outside the selected Vault" in _texts(page.overlay[-1])[0]


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
