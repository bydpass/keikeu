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
from keikeu_app import theme as app_theme
from keikeu_app.main import AppContext
from keikeu_app.pages import library_page as library_page_mod
from keikeu_app.pages.cache_page import build_cache_page
from keikeu_app.pages.library_page import build_library_page
from keikeu_app.pages.outline_editor_page import build_outline_editor_page
from keikeu_core.indexer import list_caches, list_outlines, rebuild_index
from keikeu_core.markdown_io import read_cache, read_outline, write_cache, write_outline
from keikeu_core.models import Cache, CacheStatus, Outline, Relation, RelationType
from keikeu_core.vault import init_vault, soft_delete


class FakePage:
    """Small subset of ft.Page used by page handlers under test."""

    def __init__(self) -> None:
        self.controls: list[object] = []
        self.overlay: list[object] = []
        self.services: list[object] = []
        self.scroll = ft.ScrollMode.AUTO
        self.update_count = 0
        self.theme: ft.Theme | None = None
        self.bgcolor: str | None = None
        self.title = ""

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


def _list_tile(root: object, title: str) -> ft.ListTile:
    for control in _walk(root):
        if (
            isinstance(control, ft.ListTile)
            and getattr(control.title, "value", None) == title
        ):
            return control
    raise AssertionError(f"ListTile not found: {title}")


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


def _labels(root: object, control_type: type) -> list[str | None]:
    return [
        getattr(control, "label", None)
        for control in _walk(root)
        if isinstance(control, control_type)
    ]


def _control_by_key(root: object, key: str) -> object:
    for control in _walk(root):
        if getattr(control, "key", None) == key:
            return control
    raise AssertionError(f"Control not found: {key}")


def _icon_button(root: object, icon: str) -> ft.IconButton:
    for control in _walk(root):
        if isinstance(control, ft.IconButton) and control.icon == icon:
            return control
    raise AssertionError(f"IconButton not found: {icon}")


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


def test_phase6_theme_tokens_match_wi6_contract():
    assert app_theme.BG == "#fbf6ee"
    assert app_theme.SURFACE == "#fffdf8"
    assert app_theme.SURFACE_WARM == "#f1e3cf"
    assert app_theme.FG == "#201914"
    assert app_theme.MUTED == "#7a6d63"
    assert app_theme.ACCENT == "#9b5b32"
    assert app_theme.BORDER == "#ded2c3"
    assert app_theme.BORDER_SOFT == "#eee4d7"
    assert (app_theme.TEXT_XS, app_theme.TEXT_SM, app_theme.TEXT_BASE) == (12, 14, 17)
    assert (app_theme.RADIUS_SM, app_theme.RADIUS_MD, app_theme.RADIUS_LG) == (
        10,
        16,
        24,
    )
    assert app_theme.SIDEBAR_WIDTH == 220


def test_shell_uses_warm_theme_and_chinese_navigation(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()

    app_main._build_shell(page, tmp_path)  # type: ignore[attr-defined, arg-type]

    shell = page.controls[0]
    rail = next(control for control in shell.controls if isinstance(control, ft.NavigationRail))
    assert page.bgcolor == app_theme.BG
    assert page.theme is not None
    assert page.theme.color_scheme is not None
    assert page.theme.color_scheme.primary == app_theme.ACCENT
    assert rail.extended is True
    assert rail.min_extended_width == app_theme.SIDEBAR_WIDTH
    assert [destination.label for destination in rail.destinations] == [
        "灵感缓存",
        "配方票编辑",
        "本地文件库",
    ]
    assert any("存住一瞬的灵光" in text for text in _texts(rail))


def test_cache_page_uses_phase6_copy_and_paper_surface(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_cache_page(ctx)

    assert "新灵感" in _texts(root)
    assert "原文保留，不会被整理改写" in _texts(root)
    assert "raw — 刚存，未处理" in _texts(root)
    for label in ("保存", "炼成大纲", "封存", "删除"):
        assert _button(root, label)
    assert not any(isinstance(control, ft.Dropdown) for control in _walk(root))
    card = _control_by_key(root, "cache-paper-card")
    assert isinstance(card, ft.Container)
    assert card.bgcolor == app_theme.SURFACE
    assert card.border_radius == app_theme.RADIUS_MD


def test_cache_status_strip_does_not_expand_inside_wrapping_row(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_cache_page(ctx)
    status_copy = next(
        control
        for control in _walk(root)
        if isinstance(control, ft.Text)
        and control.value == "状态由保存、炼成与封存动作自动推进。"
    )

    assert status_copy.expand is not True


def test_outline_page_exposes_phase6_hint_and_check_action(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)

    expected_hint = "Optional，还有空白字段：整理后摘要 · 流水账"
    assert expected_hint in _texts(root)
    for label in ("保存大纲", "导出 Markdown", "检查缺什么", "+ 添加关联", "删除"):
        assert _button(root, label)

    _button(root, "检查缺什么").on_click(None)

    assert expected_hint in _texts(page.overlay[-1])


def test_check_missing_fields_never_blocks_outline_save(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    root = build_outline_editor_page(ctx)
    _text_field(root, "标题").value = "仍可保存的空白配方票"

    _button(root, "检查缺什么").on_click(None)
    _button(root, "保存大纲").on_click(None)

    assert len(list((tmp_path / "outlines").glob("*.md"))) == 1


def test_library_page_uses_phase6_copy_and_paper_surface(tmp_path: Path):
    init_vault(tmp_path)
    write_cache(tmp_path, Cache(title="票夹里的灵感", raw="原文"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_library_page(ctx)

    search = _text_field(root, "搜索标题")
    assert search.expand is not True
    assert search.width == 360
    assert _dropdown(root, "状态筛选")
    for label in ("刷新", "打开", "在文件夹中显示", "删除"):
        assert _button(root, label)
    assert "灵感缓存 · 1" in _texts(root)
    assert "大纲 · 0" in _texts(root)
    card = _control_by_key(root, "library-paper-card")
    assert isinstance(card, ft.Container)
    assert card.bgcolor == app_theme.SURFACE
    assert card.border_radius == app_theme.RADIUS_MD


def test_custom_ending_field_accepts_multiline_input(tmp_path: Path):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)

    field = _text_field(root, "自定义结局")
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


def test_relation_picker_adds_index_backed_relation_without_path_input(tmp_path: Path):
    init_vault(tmp_path)
    target_path = write_cache(tmp_path, Cache(title="target cache", raw="raw words"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)
    _text_field(root, "标题").value = "outline with relation"

    _button(root, "+ 添加关联").on_click(None)
    dialog = page.overlay[-1]

    assert "target path" not in _labels(dialog, ft.TextField)
    _button(dialog, "target cache").on_click(None)
    _dropdown(dialog, "关系类型").value = RelationType.IF.value
    _text_field(dialog, "说明").value = "branch note"
    _button(dialog, "确认添加").on_click(None)

    assert "target path" not in _labels(root, ft.TextField)
    assert "IF" in _texts(root)
    assert "target cache" in _texts(root)
    assert "branch note" in _texts(root)

    _button(root, "保存大纲").on_click(None)

    outline_files = list((tmp_path / "outlines").glob("*.md"))
    assert len(outline_files) == 1
    relations = read_outline(outline_files[0]).relations
    assert len(relations) == 1
    assert relations[0].relation_type is RelationType.IF
    assert relations[0].target_path == str(target_path.relative_to(tmp_path))
    assert relations[0].note == "branch note"


def test_relation_picker_dialog_keeps_asset_list_bounded(tmp_path: Path):
    init_vault(tmp_path)
    for i in range(25):
        write_cache(tmp_path, Cache(title=f"target cache {i:02d}", raw="raw words"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)
    _button(root, "+ 添加关联").on_click(None)
    dialog = page.overlay[-1]

    content = _control_by_key(dialog, "relation-picker-content")
    assets_viewport = _control_by_key(dialog, "relation-picker-assets")

    assert getattr(content, "width", None) == 520
    assert getattr(assets_viewport, "height", None) == 220


def test_relation_picker_does_not_preview_target_raw_text(tmp_path: Path):
    init_vault(tmp_path)
    write_cache(
        tmp_path,
        Cache(
            title="target cache",
            raw="raw body should not become a relation thumbnail",
        ),
    )
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx)
    _button(root, "+ 添加关联").on_click(None)
    dialog = page.overlay[-1]

    assert "target cache" in _texts(dialog)
    assert "raw body should not become a relation thumbnail" not in _texts(dialog)


def test_existing_relation_displays_title_then_falls_back_to_path(tmp_path: Path):
    init_vault(tmp_path)
    target_path = write_cache(tmp_path, Cache(title="target cache", raw="raw words"))
    rel_path = str(target_path.relative_to(tmp_path))
    outline_path = write_outline(
        tmp_path,
        Outline(
            title="related outline",
            relations=[
                Relation(
                    relation_type=RelationType.SEQUEL,
                    target_path=rel_path,
                    note="next piece",
                )
            ],
        ),
    )
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx, outline_path)

    assert "target cache" in _texts(root)
    assert rel_path not in _texts(root)

    soft_delete(tmp_path, rel_path)
    rebuild_index(tmp_path)
    page_after_delete = FakePage()
    ctx_after_delete = AppContext(page=page_after_delete, vault=tmp_path)  # type: ignore[arg-type]

    root_after_delete = build_outline_editor_page(ctx_after_delete, outline_path)

    assert rel_path in _texts(root_after_delete)


def test_missing_relation_target_row_is_not_clickable(tmp_path: Path):
    init_vault(tmp_path)
    target_path = write_cache(tmp_path, Cache(title="target cache", raw="raw words"))
    rel_path = str(target_path.relative_to(tmp_path))
    outline_path = write_outline(
        tmp_path,
        Outline(
            title="related outline",
            relations=[
                Relation(relation_type=RelationType.SEQUEL, target_path=rel_path)
            ],
        ),
    )
    soft_delete(tmp_path, rel_path)
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx, outline_path)

    assert rel_path in _texts(root)
    missing_target = next(
        control
        for control in _walk(root)
        if isinstance(control, ft.Text) and control.value == rel_path
    )
    assert missing_target.expand is not True
    button_labels = [
        getattr(control.content, "value", None)
        for control in _walk(root)
        if isinstance(control, ft.Button)
    ]
    assert rel_path not in button_labels


def test_existing_relation_target_buttons_open_linked_assets(tmp_path: Path):
    init_vault(tmp_path)
    cache_path = write_cache(tmp_path, Cache(title="target cache", raw="cache raw"))
    outline_target_path = write_outline(tmp_path, Outline(title="target outline"))
    outline_path = write_outline(
        tmp_path,
        Outline(
            title="related outline",
            relations=[
                Relation(
                    relation_type=RelationType.SEQUEL,
                    target_path=str(cache_path.relative_to(tmp_path)),
                ),
                Relation(
                    relation_type=RelationType.SAME_SERIES,
                    target_path=str(outline_target_path.relative_to(tmp_path)),
                ),
            ],
        ),
    )
    rebuild_index(tmp_path)
    page = FakePage()
    opened: dict[str, Path] = {}
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    ctx.open_cache = lambda path: opened.update(cache=path)  # type: ignore[assignment]
    ctx.open_outline = lambda path: opened.update(outline=path)  # type: ignore[assignment]

    root = build_outline_editor_page(ctx, outline_path)
    _button(root, "target cache").on_click(None)
    _button(root, "target outline").on_click(None)

    assert opened["cache"] == cache_path
    assert opened["outline"] == outline_target_path


def test_existing_relation_remove_button_drops_relation_before_save(tmp_path: Path):
    init_vault(tmp_path)
    target_path = write_cache(tmp_path, Cache(title="target cache", raw="raw words"))
    outline_path = write_outline(
        tmp_path,
        Outline(
            title="related outline",
            relations=[
                Relation(
                    relation_type=RelationType.SEQUEL,
                    target_path=str(target_path.relative_to(tmp_path)),
                    note="remove me",
                )
            ],
        ),
    )
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]

    root = build_outline_editor_page(ctx, outline_path)
    _icon_button(root, ft.Icons.DELETE_OUTLINE).on_click(None)
    _button(root, "保存大纲").on_click(None)

    assert read_outline(outline_path).relations == []


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
    _text_field(root, "标题").value = "new export"
    _text_field(root, "原始灵感").value = "raw words stay"
    picker = _file_picker(page)

    async def save_file(**_kwargs: object) -> str:
        assert list((tmp_path / "outlines").glob("*.md")) == []
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
    _text_field(root, "标题").value = "cancel export"
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
    _text_field(root, "标题").value = "train spark"
    _text_field(root, "原始灵感").value = "raw words stay raw"

    _button(root, "炼成大纲").on_click(None)

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
    _text_field(root, "临时备注").value = "edited while archived"

    assert "archived — 封存" in _texts(root)
    try:
        _dropdown(root, "Status")
    except AssertionError:
        pass
    else:
        raise AssertionError("Cache status must not be user-selectable")

    _button(root, "保存").on_click(None)

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
    _button(root, "封存").on_click(None)

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
    _button(root, "炼成大纲").on_click(None)

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
    _text_field(root, "整理后摘要").value = "summary"

    _button(root, "保存大纲").on_click(None)

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
    _button(root, "删除").on_click(None)

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
    _button(root, "删除").on_click(None)

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
    _button(root, "删除").on_click(None)

    assert not cache_path.exists()
    assert (tmp_path / ".trash" / "cache" / cache_path.name).is_file()
    assert list_caches(tmp_path) == []
    assert "灵感缓存 · 0" in _texts(root)


def test_library_row_clicks_still_open_app_editors(tmp_path: Path):
    init_vault(tmp_path)
    cache_path = write_cache(tmp_path, Cache(title="library cache", raw="bytes"))
    outline_path = write_outline(tmp_path, Outline(title="library outline"))
    rebuild_index(tmp_path)
    page = FakePage()
    opened: dict[str, Path] = {}
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    ctx.open_cache = lambda path: opened.update(cache=path)  # type: ignore[assignment]
    ctx.open_outline = lambda path: opened.update(outline=path)  # type: ignore[assignment]

    root = build_library_page(ctx)
    _list_tile(root, "library cache").on_click(None)
    _list_tile(root, "library outline").on_click(None)

    assert opened["cache"] == cache_path
    assert opened["outline"] == outline_path


def test_library_open_button_uses_system_default_app(tmp_path: Path, monkeypatch):
    init_vault(tmp_path)
    cache_path = write_cache(tmp_path, Cache(title="library cache", raw="bytes"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    calls: list[list[str]] = []
    monkeypatch.setattr(library_page_mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        library_page_mod.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )

    root = build_library_page(ctx)
    _button(root, "打开").on_click(None)

    assert calls == [["open", str(cache_path)]]


def test_library_reveal_button_uses_finder_on_macos(tmp_path: Path, monkeypatch):
    init_vault(tmp_path)
    cache_path = write_cache(tmp_path, Cache(title="library cache", raw="bytes"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    calls: list[list[str]] = []
    monkeypatch.setattr(library_page_mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        library_page_mod.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )

    root = build_library_page(ctx)
    _button(root, "在文件夹中显示").on_click(None)

    assert calls == [["open", "-R", str(cache_path)]]


def test_library_reveal_button_falls_back_to_parent_dir_off_macos(tmp_path: Path, monkeypatch):
    init_vault(tmp_path)
    cache_path = write_cache(tmp_path, Cache(title="library cache", raw="bytes"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    calls: list[list[str]] = []
    monkeypatch.setattr(library_page_mod.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        library_page_mod.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )

    root = build_library_page(ctx)
    _button(root, "在文件夹中显示").on_click(None)

    assert calls == [["xdg-open", str(cache_path.parent)]]


def test_library_vault_footer_shows_and_reveals_vault_path(tmp_path: Path, monkeypatch):
    init_vault(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    calls: list[list[str]] = []
    monkeypatch.setattr(library_page_mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        library_page_mod.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )

    root = build_library_page(ctx)
    _button(root, "在文件夹中显示").on_click(None)

    assert str(tmp_path) in _texts(root)
    vault_path_text = next(
        control
        for control in _walk(root)
        if isinstance(control, ft.Text) and control.value == str(tmp_path)
    )
    assert vault_path_text.expand is not True
    assert calls == [["open", str(tmp_path)]]


def test_library_system_open_failure_notifies_without_crashing(tmp_path: Path, monkeypatch):
    init_vault(tmp_path)
    write_cache(tmp_path, Cache(title="library cache", raw="bytes"))
    rebuild_index(tmp_path)
    page = FakePage()
    ctx = AppContext(page=page, vault=tmp_path)  # type: ignore[arg-type]
    monkeypatch.setattr(library_page_mod.platform, "system", lambda: "Darwin")

    def fail_run(_command: list[str], check: bool) -> None:
        raise OSError("launcher unavailable")

    monkeypatch.setattr(library_page_mod.subprocess, "run", fail_run)

    root = build_library_page(ctx)
    _button(root, "打开").on_click(None)

    assert any("无法打开文件" in text for bar in page.overlay for text in _texts(bar))
