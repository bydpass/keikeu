"""Outline editor page: edit and save a structured outline.

GUI layer only. All persistence goes through ``keikeu_core.markdown_io``
(``write_outline`` / ``update_outline`` / ``read_outline``) and the index
through ``keikeu_core.indexer``. This module never serializes by hand.

Every field may be blank. The UI may softly hint at completion but must NEVER
block a save (appdesign.md / product invariants). ``raw_inspiration`` is kept
verbatim.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from keikeu_app.widgets import notify, section_field, single_line_field
from keikeu_core.indexer import rebuild_index
from keikeu_core.markdown_io import (
    read_cache,
    read_outline,
    update_cache,
    update_outline,
    write_outline,
)
from keikeu_core.models import CacheStatus, EndingType, Outline, Relation, RelationType

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

    title_field = single_line_field("Title", "")
    raw_field = section_field("原始灵感 (raw_inspiration)", "", min_lines=4, max_lines=14)
    summary_field = section_field("整理后摘要 (summary)", "", min_lines=2, max_lines=10)
    fandom_field = single_line_field("Fandom", "")
    characters_field = single_line_field("人物 (characters, comma-separated)", "")
    cp_field = single_line_field("CP", "")
    warnings_field = section_field("观前提醒 (content_warnings)", "", min_lines=2, max_lines=6)
    plot_field = section_field("流水账 (plot)", "", min_lines=4, max_lines=16)
    ending_dd = ft.Dropdown(
        label="Ending Type",
        value=EndingType.OE.value,
        options=[ft.dropdown.Option(e) for e in _ENDING_OPTIONS],
    )
    custom_ending_field = section_field(
        "Custom ending (custom_ending)", "", min_lines=2, max_lines=8
    )

    # === Minimal relations editor ========================================== #
    # Each row holds a relation-type dropdown, a target-path field, and a note
    # field. They are read back into Relation objects only at save time.
    relation_rows: list[ft.Row] = []
    relations_column = ft.Column(controls=[])

    def _make_relation_row(
        rtype: str = RelationType.SEQUEL.value,
        target: str = "",
        note: str = "",
    ) -> ft.Row:
        type_dd = ft.Dropdown(
            value=rtype,
            options=[ft.dropdown.Option(r) for r in _RELATION_OPTIONS],
            width=160,
        )
        target_tf = ft.TextField(label="target path", value=target, expand=True)
        note_tf = ft.TextField(label="note", value=note, expand=True)
        row = ft.Row(controls=[type_dd, target_tf, note_tf])

        def remove_row(_: ft.ControlEvent) -> None:
            if row in relation_rows:
                relation_rows.remove(row)
                relations_column.controls.remove(row)
                page.update()

        row.controls.append(
            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, on_click=remove_row)
        )
        return row

    def add_relation_row(
        rtype: str = RelationType.SEQUEL.value, target: str = "", note: str = ""
    ) -> None:
        row = _make_relation_row(rtype, target, note)
        relation_rows.append(row)
        relations_column.controls.append(row)

    def on_add_relation(_: ft.ControlEvent) -> None:
        add_relation_row()
        page.update()

    def _collect_relations() -> list[Relation]:
        relations: list[Relation] = []
        for row in relation_rows:
            type_dd, target_tf, note_tf = row.controls[0], row.controls[1], row.controls[2]
            target = (target_tf.value or "").strip()
            if not target:
                # Skip empty rows so a blank add-row never blocks the save.
                continue
            relations.append(
                Relation(
                    relation_type=type_dd.value or RelationType.SEQUEL.value,
                    target_path=target,
                    note=note_tf.value or "",
                )
            )
        return relations

    def _load_outline(existing: Outline) -> None:
        title_field.value = existing.title
        raw_field.value = existing.raw_inspiration
        summary_field.value = existing.summary
        fandom_field.value = existing.fandom
        characters_field.value = ", ".join(existing.characters)
        cp_field.value = existing.cp
        warnings_field.value = existing.content_warnings
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
            content_warnings=warnings_field.value or "",
            plot=plot_field.value or "",
            ending_type=ending_dd.value or EndingType.OE.value,
            custom_ending=custom_ending_field.value or "",
            relations=_collect_relations(),
            created=state["created"],  # type: ignore[arg-type]
            updated=datetime.now(),
        )

    def on_save(_: ft.ControlEvent) -> None:
        try:
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
            notify(page, "Outline saved")
            page.update()
        except Exception as ex:
            notify(page, f"Could not save outline: {ex}")

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
            warnings_field,
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
            ft.Row(controls=[ft.Button(content=ft.Text("Save"), on_click=on_save)]),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
