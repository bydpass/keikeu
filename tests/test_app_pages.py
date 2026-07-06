"""Lightweight GUI page contract tests.

These do not launch Flet. They instantiate page builders with a fake page object
and click handlers directly so the cache -> outline workflow stays pinned.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable

import flet as ft

from keikeu_app import main as app_main
from keikeu_app.main import AppContext
from keikeu_app.pages.cache_page import build_cache_page
from keikeu_app.pages.library_page import build_library_page
from keikeu_app.pages.outline_editor_page import build_outline_editor_page
from keikeu_core.indexer import list_caches, list_outlines, rebuild_index
from keikeu_core.markdown_io import read_cache, read_outline, write_cache, write_outline
from keikeu_core.models import Cache, CacheStatus, Outline
from keikeu_core.vault import init_vault


class FakePage:
    """Small subset of ft.Page used by page handlers under test."""

    def __init__(self) -> None:
        self.controls: list[object] = []
        self.overlay: list[object] = []
        self.services: list[object] = []
        self.scroll = ft.ScrollMode.AUTO
        self.update_count = 0

    def add(self, *controls: object) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.update_count += 1


def _walk(control: object) -> Iterable[object]:
    yield control
    for attr in ("content", "leading", "trailing"):
        child = getattr(control, attr, None)
        if child is not None:
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


def _dropdown(root: object, label: str) -> ft.Dropdown:
    for control in _walk(root):
        if isinstance(control, ft.Dropdown) and control.label == label:
            return control
    raise AssertionError(f"Dropdown not found: {label}")


def _texts(root: object) -> list[str]:
    return [
        control.value
        for control in _walk(root)
        if isinstance(control, ft.Text) and isinstance(control.value, str)
    ]


def _file_picker(page: FakePage) -> ft.FilePicker:
    assert not any(isinstance(control, ft.FilePicker) for control in page.overlay)
    for control in page.services:
        if isinstance(control, ft.FilePicker):
            return control
    raise AssertionError("FilePicker not found in page services")


def test_navigation_shell_disables_page_level_scroll(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()

    app_main._build_shell(page, tmp_path)  # type: ignore[attr-defined, arg-type]

    assert page.scroll is None
    assert page.controls
    shell = page.controls[0]
    assert isinstance(shell, ft.Row)
    assert shell.expand is True
    assert any(isinstance(control, ft.NavigationRail) for control in shell.controls)


def test_custom_ending_field_accepts_multiline_input(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)

    field = _text_field(root, "Custom ending (custom_ending)")
    assert field.multiline is True
    assert field.min_lines and field.min_lines > 1


def test_outline_editor_exposes_split_warning_fields(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)

    assert _text_field(root, "原作 / AU / IF / PA").value == ""
    assert _text_field(root, "CP 结构").value == ""
    assert _text_field(root, "情节元素").value == ""


def test_export_saved_outline_copies_vault_file_bytes(tmp_path: Path):
    init_vault(tmp_path)
    outline_path = write_outline(
        tmp_path,
        Outline(title="export me", raw_inspiration="raw\n---\nbytes"),
    )
    target_path = tmp_path / "exported.md"
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx, outline_path)
    picker = _file_picker(page)
    calls: dict[str, object] = {}

    async def save_file(**kwargs: object) -> str:
        calls.update(kwargs)
        return str(target_path)

    picker.save_file = save_file  # type: ignore[method-assign]

    asyncio.run(_button(root, "导出 Markdown").on_click(None))

    assert target_path.read_bytes() == outline_path.read_bytes()
    assert calls["file_name"] == outline_path.name
    assert calls["allowed_extensions"] == ["md"]


def test_export_unsaved_outline_saves_then_exports(tmp_path: Path):
    init_vault(tmp_path)
    target_path = tmp_path / "draft-export.md"
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)
    _text_field(root, "Title").value = "new export"
    _text_field(root, "原始灵感 (raw_inspiration)").value = "raw words stay"
    picker = _file_picker(page)
    async def save_file(**_kwargs: object) -> str:
        return str(target_path)

    picker.save_file = save_file  # type: ignore[method-assign]

    asyncio.run(_button(root, "导出 Markdown").on_click(None))

    outline_files = list((tmp_path / "outlines").glob("*.md"))
    assert len(outline_files) == 1
    assert target_path.read_bytes() == outline_files[0].read_bytes()
    assert read_outline(outline_files[0]).raw_inspiration == "raw words stay"


def test_export_cancel_leaves_unsaved_outline_unwritten(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)
    _text_field(root, "Title").value = "cancel export"
    picker = _file_picker(page)
    async def save_file(**_kwargs: object) -> None:
        return None

    picker.save_file = save_file  # type: ignore[method-assign]

    asyncio.run(_button(root, "导出 Markdown").on_click(None))

    assert list((tmp_path / "outlines").glob("*.md")) == []


def test_convert_cache_opens_unsaved_outline_draft(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    captured: dict[str, object] = {}
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    def start_outline(outline: Outline, cache_path: Path) -> None:
        captured["outline"] = outline
        captured["cache_path"] = cache_path

    ctx.start_outline_from_cache = start_outline
    root = build_cache_page(ctx)
    _text_field(root, "Title").value = "train spark"
    _text_field(root, "原始灵感 (raw)").value = "raw words stay raw"

    _button(root, "Convert to outline").on_click(None)

    outline = captured["outline"]
    cache_path = captured["cache_path"]
    assert isinstance(outline, Outline)
    assert isinstance(cache_path, Path)
    assert outline.title == "train spark"
    assert outline.raw_inspiration == "raw words stay raw"
    assert list((tmp_path / "outlines").glob("*.md")) == []

    cache = read_cache(cache_path)
    assert cache.status is CacheStatus.DRAFTING
    assert cache.linked_outline is None


def test_cache_status_is_read_only_and_save_keeps_existing_status(tmp_path: Path):
    init_vault(tmp_path)
    cache_path = write_cache(
        tmp_path,
        Cache(title="old spark", raw="raw words", status=CacheStatus.ARCHIVED),
    )
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_cache_page(ctx, cache_path)
    _text_field(root, "临时备注 (notes)").value = "edited while archived"

    assert "archived — 封存" in _texts(root)
    try:
        _dropdown(root, "Status")
    except AssertionError:
        pass
    else:
        raise AssertionError("Cache status must not be user-selectable")

    _button(root, "Save").on_click(None)

    cache = read_cache(cache_path)
    assert cache.notes == "edited while archived"
    assert cache.status is CacheStatus.ARCHIVED


def test_archive_button_sets_cache_status_archived(tmp_path: Path):
    init_vault(tmp_path)
    cache_path = write_cache(
        tmp_path,
        Cache(title="old spark", raw="raw words", status=CacheStatus.RAW),
    )
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_cache_page(ctx, cache_path)
    _button(root, "Archive").on_click(None)

    assert read_cache(cache_path).status is CacheStatus.ARCHIVED


def test_convert_cache_with_existing_outline_keeps_status(tmp_path: Path):
    init_vault(tmp_path)
    outline_path = write_outline(tmp_path, Outline(title="existing"))
    cache_path = write_cache(
        tmp_path,
        Cache(
            title="train spark",
            raw="raw words",
            status=CacheStatus.OUTLINED,
            linked_outline=str(outline_path.relative_to(tmp_path)),
        ),
    )
    page = FakePage()
    opened: dict[str, Path] = {}
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    ctx.open_outline = lambda path: opened.update(path=path)  # type: ignore[assignment]

    root = build_cache_page(ctx, cache_path)
    _button(root, "Convert to outline").on_click(None)

    assert opened["path"] == outline_path
    cache = read_cache(cache_path)
    assert cache.status is CacheStatus.OUTLINED
    assert cache.linked_outline == str(outline_path.relative_to(tmp_path))


def test_saving_outline_from_cache_marks_cache_outlined(tmp_path: Path):
    init_vault(tmp_path)
    cache_path = write_cache(
        tmp_path,
        Cache(title="train spark", raw="raw words", status=CacheStatus.DRAFTING),
    )
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(
        ctx,
        initial_outline=Outline(title="train spark", raw_inspiration="raw words"),
        source_cache_path=cache_path,
    )
    _text_field(root, "整理后摘要 (summary)").value = "summary"

    _button(root, "Save").on_click(None)

    outline_files = list((tmp_path / "outlines").glob("*.md"))
    assert len(outline_files) == 1
    cache = read_cache(cache_path)
    assert cache.status is CacheStatus.OUTLINED
    assert cache.linked_outline == str(outline_files[0].relative_to(tmp_path))


def test_cache_editor_delete_moves_file_to_trash_and_opens_library(tmp_path: Path):
    init_vault(tmp_path)
    cache_path = write_cache(tmp_path, Cache(title="delete me", raw="exact bytes"))
    original = cache_path.read_bytes()
    page = FakePage()
    opened: dict[str, bool] = {}
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    ctx.open_library = lambda: opened.update(library=True)

    root = build_cache_page(ctx, cache_path)
    _button(root, "Delete").on_click(None)

    moved = tmp_path / ".trash" / "cache" / cache_path.name
    assert not cache_path.exists()
    assert moved.read_bytes() == original
    assert opened["library"] is True
    assert list_caches(tmp_path) == []


def test_outline_editor_delete_moves_file_to_trash_and_opens_library(tmp_path: Path):
    init_vault(tmp_path)
    outline_path = write_outline(
        tmp_path,
        Outline(title="delete outline", raw_inspiration="exact bytes"),
    )
    original = outline_path.read_bytes()
    page = FakePage()
    opened: dict[str, bool] = {}
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    ctx.open_library = lambda: opened.update(library=True)

    root = build_outline_editor_page(ctx, outline_path)
    _button(root, "Delete").on_click(None)

    moved = tmp_path / ".trash" / "outlines" / outline_path.name
    assert not outline_path.exists()
    assert moved.read_bytes() == original
    assert opened["library"] is True
    assert list_outlines(tmp_path) == []


def test_library_delete_moves_cache_to_trash_and_refreshes_results(tmp_path: Path):
    init_vault(tmp_path)
    cache_path = write_cache(tmp_path, Cache(title="library delete", raw="bytes"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_library_page(ctx)
    _button(root, "Delete").on_click(None)

    assert not cache_path.exists()
    assert (tmp_path / ".trash" / "cache" / cache_path.name).is_file()
    assert list_caches(tmp_path) == []
    assert "Caches (0)" in _texts(root)
