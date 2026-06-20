"""Lightweight GUI page contract tests.

These do not launch Flet. They instantiate page builders with a fake page object
and click handlers directly so the cache -> outline workflow stays pinned.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import flet as ft

from keikeu_app import main as app_main
from keikeu_app.main import AppContext
from keikeu_app.pages.cache_page import build_cache_page
from keikeu_app.pages.outline_editor_page import build_outline_editor_page
from keikeu_core.markdown_io import read_cache, write_cache, write_outline
from keikeu_core.models import Cache, CacheStatus, Outline
from keikeu_core.vault import init_vault


class FakePage:
    """Small subset of ft.Page used by page handlers under test."""

    def __init__(self) -> None:
        self.controls: list[object] = []
        self.overlay: list[object] = []
        self.scroll = ft.ScrollMode.AUTO
        self.update_count = 0

    def add(self, *controls: object) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.update_count += 1


def _walk(control: object) -> Iterable[object]:
    yield control
    for attr in ("content", "leading"):
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
