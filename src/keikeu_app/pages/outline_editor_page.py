"""Outline editor page: edit and save a structured outline.

GUI layer only. All persistence goes through ``keikeu_core.markdown_io``
(``write_outline`` / ``update_outline`` / ``read_outline``) and the index
through ``keikeu_core.indexer``. This module never serializes by hand.

Every field may be blank. The UI may softly hint at completion but must NEVER
block a save (appdesign.md / product invariants). ``raw_inspiration`` is kept
verbatim.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.widgets import notify, section_field, single_line_field
from keikeu_core.indexer import list_caches, list_outlines, rebuild_index
from keikeu_core.markdown_io import (
    read_cache,
    read_outline,
    update_cache,
    update_outline,
    write_outline,
)
from keikeu_core.models import CacheStatus, EndingType, Outline, Relation, RelationType
from keikeu_core.vault import soft_delete

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_outline_editor_page"]

_ENDING_OPTIONS = [e.value for e in EndingType]
_RELATION_OPTIONS = [r.value for r in RelationType]


def build_outline_editor_page(
    ctx: "AppContext",
    open_path: Path | None = None,
    initial_outline: Outline | None = None,
    source_cache_path: Path | None = None,
) -> ft.Control:
    """Build the outline editor.

    ``open_path`` is the outline Markdown file being edited, or ``None`` for a
    brand-new outline. ``initial_outline`` pre-fills a new draft from a cache
    without writing it yet. Save dispatches to ``write_outline`` (new) or
    ``update_outline`` (existing) and never blocks on missing fields.
    """
    page = ctx.page

    state: dict[str, object] = {
        "path": open_path,
        "created": datetime.now(),
    }
    export_picker = ft.FilePicker()
    page.services.append(export_picker)

    title_field = single_line_field("Title", "")
    raw_field = section_field("原始灵感 (raw_inspiration)", "", min_lines=4, max_lines=14)
    summary_field = section_field("整理后摘要 (summary)", "", min_lines=2, max_lines=10)
    fandom_field = single_line_field("Fandom", "")
    characters_field = single_line_field("人物 (characters, comma-separated)", "")
    cp_field = single_line_field("CP", "")
    warning_setting_field = single_line_field("原作 / AU / IF / PA", "")
    warning_cp_structure_field = single_line_field("CP 结构", "")
    warning_elements_field = single_line_field("情节元素", "")
    plot_field = section_field("流水账 (plot)", "", min_lines=4, max_lines=16)
    ending_dd = ft.Dropdown(
        label="Ending Type",
        value=EndingType.OE.value,
        options=[ft.dropdown.Option(e) for e in _ENDING_OPTIONS],
    )
    custom_ending_field = section_field(
        "Custom ending (custom_ending)", "", min_lines=2, max_lines=8
    )

    # === Local relation picker ============================================= #
    # Relations are selected from the index so users never hand-type target
    # paths. The stored model still carries the relative path for Markdown I/O.
    relations: list[Relation] = []
    relations_column = ft.Column(controls=[])

    def _asset_entries() -> list[dict]:
        """Return relation targets from the rebuildable index."""
        return list_caches(ctx.vault) + list_outlines(ctx.vault)

    def _asset_title_by_path() -> dict[str, str]:
        """Map indexed relative paths to display titles."""
        return {
            str(entry["path"]): entry.get("title") or "(untitled)"
            for entry in _asset_entries()
        }

    def _render_relations() -> None:
        title_by_path = _asset_title_by_path()
        relations_column.controls.clear()
        for rel in relations:
            target_title = title_by_path.get(rel.target_path, rel.target_path)

            def remove_relation(
                _: ft.ControlEvent,
                relation: Relation = rel,
            ) -> None:
                if relation in relations:
                    relations.remove(relation)
                    _render_relations()
                    page.update()

            row = ft.Row(
                controls=[
                    ft.Text(rel.relation_type.value, weight=ft.FontWeight.BOLD),
                    ft.Text(target_title, expand=True),
                    ft.Text(rel.note),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=remove_relation,
                    ),
                ],
                wrap=True,
            )
            relations_column.controls.append(row)

    def add_relation_row(
        rtype: str = RelationType.SEQUEL.value, target: str = "", note: str = ""
    ) -> None:
        relations.append(
            Relation(
                relation_type=rtype,
                target_path=target,
                note=note,
            )
        )
        _render_relations()

    def on_add_relation(_: ft.ControlEvent) -> None:
        selected: dict[str, object] = {}
        search_field = ft.TextField(label="搜索本地资产")
        assets_column = ft.Column(controls=[])
        relation_type_dd = ft.Dropdown(
            label="关系类型",
            value=RelationType.SEQUEL.value,
            options=[ft.dropdown.Option(r) for r in _RELATION_OPTIONS],
        )
        note_field = ft.TextField(label="说明")
        selected_text = ft.Text("尚未选择关联对象", size=12, color=ft.Colors.OUTLINE)
        error_text = ft.Text("", color=ft.Colors.ERROR)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("添加关联"),
            content=ft.Column(
                controls=[
                    search_field,
                    assets_column,
                    selected_text,
                    relation_type_dd,
                    note_field,
                    error_text,
                ],
                tight=True,
            ),
            actions=[],
        )

        def select_asset(entry: dict) -> None:
            selected["entry"] = entry
            selected_text.value = f"已选择：{entry.get('title') or '(untitled)'}"
            error_text.value = ""
            page.update()

        def refresh_assets(_: ft.ControlEvent | None = None) -> None:
            query = (search_field.value or "").strip().lower()
            assets_column.controls.clear()
            for entry in _asset_entries():
                title = entry.get("title") or "(untitled)"
                if query and query not in title.lower():
                    continue
                subtitle = "  ·  ".join(
                    bit
                    for bit in (
                        entry.get("type", ""),
                        entry.get("updated", ""),
                    )
                    if bit
                )
                assets_column.controls.append(
                    ft.Row(
                        controls=[
                            ft.Button(
                                content=ft.Text(title),
                                on_click=lambda _e, item=entry: select_asset(item),
                            ),
                            ft.Text(subtitle, size=12, color=ft.Colors.OUTLINE),
                        ],
                        wrap=True,
                    )
                )
            if not assets_column.controls:
                assets_column.controls.append(ft.Text("没有可关联的本地资产"))
            page.update()

        def cancel(_: ft.ControlEvent) -> None:
            dialog.open = False
            page.update()

        def confirm(_: ft.ControlEvent) -> None:
            entry = selected.get("entry")
            if not isinstance(entry, dict):
                error_text.value = "先选择关联对象"
                page.update()
                return
            add_relation_row(
                relation_type_dd.value or RelationType.SEQUEL.value,
                str(entry["path"]),
                note_field.value or "",
            )
            dialog.open = False
            page.update()

        dialog.actions = [
            ft.OutlinedButton(content=ft.Text("取消"), on_click=cancel),
            ft.Button(content=ft.Text("确认添加"), on_click=confirm),
        ]
        search_field.on_change = refresh_assets
        refresh_assets()
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _collect_relations() -> list[Relation]:
        return list(relations)

    def _load_outline(existing: Outline) -> None:
        title_field.value = existing.title
        raw_field.value = existing.raw_inspiration
        summary_field.value = existing.summary
        fandom_field.value = existing.fandom
        characters_field.value = ", ".join(existing.characters)
        cp_field.value = existing.cp
        warning_setting_field.value = existing.warning_setting
        warning_cp_structure_field.value = existing.warning_cp_structure
        warning_elements_field.value = existing.warning_elements
        plot_field.value = existing.plot
        ending_dd.value = existing.ending_type.value
        custom_ending_field.value = existing.custom_ending
        state["created"] = existing.created
        for rel in existing.relations:
            add_relation_row(rel.relation_type.value, rel.target_path, rel.note)

    # === Load existing or initial draft ==================================== #
    if open_path is not None:
        _load_outline(read_outline(open_path))
    elif initial_outline is not None:
        _load_outline(initial_outline)

    def _current_outline() -> Outline:
        chars = [
            c.strip()
            for c in (characters_field.value or "").split(",")
            if c.strip()
        ]
        return Outline(
            title=title_field.value or "",
            raw_inspiration=raw_field.value or "",
            summary=summary_field.value or "",
            fandom=fandom_field.value or "",
            characters=chars,
            cp=cp_field.value or "",
            warning_setting=warning_setting_field.value or "",
            warning_cp_structure=warning_cp_structure_field.value or "",
            warning_elements=warning_elements_field.value or "",
            plot=plot_field.value or "",
            ending_type=ending_dd.value or EndingType.OE.value,
            custom_ending=custom_ending_field.value or "",
            relations=_collect_relations(),
            created=state["created"],  # type: ignore[arg-type]
            updated=datetime.now(),
        )

    def _persist_current_outline() -> Path:
        """Save the live outline fields and return the vault source path."""
        outline = _current_outline()  # never blocks; all fields may be blank
        path = state["path"]
        if path is None:
            path = write_outline(ctx.vault, outline)
            state["path"] = path
        else:
            update_outline(path, outline)  # type: ignore[arg-type]

        if source_cache_path is not None:
            cache = read_cache(source_cache_path)
            cache.linked_outline = str(path.relative_to(ctx.vault))  # type: ignore[union-attr]
            cache.status = CacheStatus.OUTLINED
            cache.updated = datetime.now()
            update_cache(source_cache_path, cache)

        rebuild_index(ctx.vault)
        return path  # type: ignore[return-value]

    def on_save(_: ft.ControlEvent) -> None:
        try:
            _persist_current_outline()
            notify(page, "Outline saved")
            page.update()
        except Exception as ex:
            notify(page, f"Could not save outline: {ex}")

    def on_delete(_: ft.ControlEvent) -> None:
        path = state["path"]
        if not isinstance(path, Path):
            notify(page, "Nothing to delete")
            return
        try:
            soft_delete(ctx.vault, str(path.relative_to(ctx.vault)))
            state["path"] = None
            rebuild_index(ctx.vault)
            notify(page, "已移入回收站")
            ctx.open_library()
        except Exception as ex:
            notify(page, f"Could not delete outline: {ex}")

    def _default_export_name() -> str:
        """Return a dialog filename; saved outlines use the vault filename."""
        path = state["path"]
        if isinstance(path, Path):
            return path.name
        title = (title_field.value or "").strip()
        return f"{title}.md" if title else "outline.md"

    async def on_export(_: ft.ControlEvent) -> None:
        try:
            target = await export_picker.save_file(
                dialog_title="导出 Markdown",
                file_name=_default_export_name(),
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["md"],
            )
            if not target:
                return
            source_path = _persist_current_outline()
            shutil.copy2(source_path, Path(target))
            notify(page, "Markdown exported")
            page.update()
        except Exception as ex:
            notify(page, f"Could not export Markdown: {ex}")

    # === Soft completion hint (never blocks) =============================== #
    hint = ft.Text("", size=12, color=ft.Colors.OUTLINE)

    def refresh_hint(_: ft.ControlEvent | None = None) -> None:
        missing = []
        if not (summary_field.value or "").strip():
            missing.append("整理后摘要")
        if not (plot_field.value or "").strip():
            missing.append("流水账")
        hint.value = (
            "Looks complete." if not missing else "Optional, still blank: " + ", ".join(missing)
        )
        if page.controls:
            page.update()

    refresh_hint()
    summary_field.on_change = refresh_hint
    plot_field.on_change = refresh_hint

    header = ft.Text(
        "New outline" if open_path is None else "Edit outline",
        size=20,
        weight=ft.FontWeight.BOLD,
    )

    return ft.Column(
        controls=[
            header,
            title_field,
            raw_field,
            summary_field,
            ft.Row(controls=[fandom_field, cp_field]),
            characters_field,
            ft.Text("内容要素", weight=ft.FontWeight.BOLD),
            warning_setting_field,
            warning_cp_structure_field,
            warning_elements_field,
            plot_field,
            ending_dd,
            custom_ending_field,
            ft.Divider(),
            ft.Text("逻辑关联 (relations)", weight=ft.FontWeight.BOLD),
            relations_column,
            ft.OutlinedButton(
                content=ft.Text("Add relation"),
                icon=ft.Icons.ADD,
                on_click=on_add_relation,
            ),
            ft.Divider(),
            hint,
            ft.Row(
                controls=[
                    ft.Button(content=ft.Text("Save"), on_click=on_save),
                    ft.OutlinedButton(
                        content=ft.Text("导出 Markdown"),
                        on_click=on_export,
                    ),
                    ft.OutlinedButton(content=ft.Text("Delete"), on_click=on_delete),
                ],
                wrap=True,
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
