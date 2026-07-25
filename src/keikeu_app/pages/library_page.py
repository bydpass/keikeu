"""Paper Library: folder scopes, retrieval, recovery, and OS handoff."""

from __future__ import annotations

import asyncio
import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Iterable
import unicodedata

import flet as ft

from keikeu_app.theme import (
    ACCENT,
    ACCENT_ON,
    BORDER,
    BORDER_SOFT,
    FG,
    FONT_DISPLAY,
    MUTED,
    RADIUS_SM,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SURFACE_WARM,
)
from keikeu_app.widgets import (
    close_top_dialog,
    danger_button,
    notify,
    page_header,
    paper_card,
    single_line_field,
)
from keikeu_core.indexer import list_index_errors, list_papers, rebuild_index
from keikeu_core.markdown_io import branch_paper, read_paper_snapshot
from keikeu_core.vault import (
    PathOperationResult,
    create_folder,
    list_active_folders,
    list_trashed_folders,
    list_trashed_papers,
    merge_folders,
    move_papers,
    next_paper_code,
    permanently_delete_folder,
    permanently_delete_papers,
    rename_folder,
    resolve_active_paper_path,
    restore_folder,
    restore_papers,
    soft_delete_folder,
    soft_delete_papers,
    validate_vault_tree_no_follow,
)

if TYPE_CHECKING:
    from keikeu_app.main import AppContext

__all__ = ["build_library_page"]

_SCOPE_ALL = "all"
_SCOPE_UNFILED = "unfiled"
_SCOPE_TRASH = "trash"
_FOLDER_PREFIX = "folder:"
_BATCH_UNFILED_KEY = "../__keikeu_unfiled__"


def _open_command(path: Path) -> list[str]:
    """Return the platform command for opening a file with its default app."""
    system = platform.system()
    if system == "Darwin":
        return ["open", str(path)]
    if system == "Windows":
        return ["cmd", "/c", "start", "", str(path)]
    return ["xdg-open", str(path)]


def _reveal_command(path: Path) -> list[str]:
    """Return the platform command for showing a file in its file manager."""
    if platform.system() == "Darwin":
        return ["open", str(path)] if path.is_dir() else ["open", "-R", str(path)]
    return _open_command(path if path.is_dir() else path.parent)


def _run_system_command(page: ft.Page, command: list[str], action: str) -> None:
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.SubprocessError) as ex:
        notify(page, f"无法{action}：{ex}")


def _open_with_system(page: ft.Page, path: Path) -> None:
    _run_system_command(page, _open_command(path), "打开文件")


def _reveal_in_folder(page: ft.Page, path: Path) -> None:
    _run_system_command(page, _reveal_command(path), "在文件夹中显示")


def _folder_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _scope_for_folder(folder: str) -> str:
    return f"{_FOLDER_PREFIX}{folder}"


def _folder_from_scope(scope: str) -> str | None:
    return scope[len(_FOLDER_PREFIX) :] if scope.startswith(_FOLDER_PREFIX) else None


def _show_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    page.show_dialog(dialog)


def _close_dialog(page: ft.Page) -> None:
    page.pop_dialog()


def _result_summary(action: str, results: Iterable[PathOperationResult]) -> str:
    records = list(results)
    succeeded = sum(result.succeeded for result in records)
    failed = len(records) - succeeded
    if not records:
        return f"{action}：没有可处理项目"
    if not failed:
        return f"{action}：{succeeded} 项成功"
    failure_details = "；".join(
        f"{result.source}：{result.error or '未知错误'}"
        for result in records
        if not result.succeeded
    )
    return f"{action}：{succeeded} 项成功，{failed} 项失败；{failure_details}"


def build_library_page(
    ctx: "AppContext",
    initial_scope: str = _SCOPE_ALL,
) -> ft.Control:
    """Build the one-level scoped Library with per-item safe mutations."""
    page = ctx.page
    search_field = single_line_field(
        "搜索名称、代号、Summary、Tags 或 Highlight 名称"
    )
    search_field.width = 430
    search_field.key = "library-search"
    sort_field = ft.Dropdown(
        label="排序",
        value="updated_desc",
        width=190,
        dense=True,
        options=[
            ft.DropdownOption(key="updated_desc", text="最近更新"),
            ft.DropdownOption(key="name", text="名称"),
            ft.DropdownOption(key="created_desc", text="创建时间：新→旧"),
            ft.DropdownOption(key="created_asc", text="创建时间：旧→新"),
        ],
        key="library-sort",
    )
    batch_destination = ft.Dropdown(
        label="批量移动到",
        width=190,
        dense=True,
        key="library-batch-destination",
    )
    scope_controls = ft.Column(
        controls=[],
        spacing=SPACE_2,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        key="library-scopes",
    )
    scope_in_sidebar = ctx.library_scope_host is not None
    if ctx.library_scope_host is not None:
        ctx.library_scope_host.controls = [scope_controls]
    results = ft.Column(
        controls=[],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        key="library-results",
    )
    operation_status = ft.Text("", color=MUTED, size=12, key="library-operation-status")
    selection_notice = ft.Text("", color=MUTED, size=12, key="library-selection-notice")
    selected_paths: set[str] = set()
    drag_state: dict[str, str | None] = {"path": None}
    current_scope = (
        initial_scope
        if initial_scope in {_SCOPE_ALL, _SCOPE_UNFILED, _SCOPE_TRASH}
        or initial_scope.startswith(_FOLDER_PREFIX)
        else _SCOPE_ALL
    )
    visible_active: list[dict[str, object]] = []
    selection_notice_generation = 0

    def on_reveal_vault(_: ft.ControlEvent) -> None:
        try:
            validate_vault_tree_no_follow(ctx.vault)
        except (OSError, ValueError) as ex:
            notify(page, f"无法在文件夹中显示 Vault：{ex}")
            return
        _reveal_in_folder(page, ctx.vault)

    def _set_operation(message: str) -> None:
        operation_status.value = message

    def _recover_from_stale_action(action: str, error: Exception) -> None:
        message = f"{action}失败：{error}；已刷新 Library，请重试。"
        try:
            rebuild_index(ctx.vault)
            _set_operation(message)
            refresh()
        except (OSError, ValueError) as refresh_error:
            _set_operation(f"{message} 刷新失败：{refresh_error}")
            page.update()

    def _refresh_after_mutation(message: str) -> None:
        rebuild_index(ctx.vault)
        _set_operation(message)
        refresh()

    def _apply_move(paths: Iterable[str], folder: str | None) -> None:
        records = list(paths)
        try:
            results_for_move = move_papers(ctx.vault, records, folder)
        except (OSError, ValueError) as ex:
            _recover_from_stale_action("移动", ex)
            return
        succeeded = {
            str(result.source) for result in results_for_move if result.succeeded
        }
        selected_paths.difference_update(succeeded)
        _refresh_after_mutation(_result_summary("移动", results_for_move))

    def _move_menu_items(rel_path: str, folders: list[str]) -> list[ft.PopupMenuItem]:
        items = [
            ft.PopupMenuItem(
                content="移动到：未归类",
                disabled=Path(rel_path).parent == Path("cache"),
                on_click=lambda _e, path=rel_path: _apply_move([path], None),
            )
        ]
        for folder in folders:
            items.append(
                ft.PopupMenuItem(
                    content=f"移动到：{folder}",
                    disabled=Path(rel_path).parent == Path("cache") / folder,
                    on_click=lambda _e, path=rel_path, target=folder: _apply_move(
                        [path],
                        target,
                    ),
                )
            )
        return items

    def _branch(rel_path: str) -> None:
        try:
            source = resolve_active_paper_path(ctx.vault, rel_path)
            _paper, source_bytes = read_paper_snapshot(source)
            code = next_paper_code(ctx.vault)
            destination = source.relative_to(ctx.vault).parent / f"{code}.md"
            branch_paper(
                ctx.vault,
                source.relative_to(ctx.vault),
                destination,
                code,
                expected_source_bytes=source_bytes,
            )
            _refresh_after_mutation(f"已创建分支 {code}")
        except (OSError, ValueError, FileExistsError) as ex:
            _set_operation(f"无法创建分支：{ex}")
            page.update()

    def _trash_active(paths: Iterable[str]) -> None:
        records = list(paths)
        try:
            deletion_results = soft_delete_papers(ctx.vault, records)
        except (OSError, ValueError) as ex:
            _recover_from_stale_action("移至 Trash", ex)
            return
        selected_paths.difference_update(
            str(result.source) for result in deletion_results if result.succeeded
        )
        _refresh_after_mutation(_result_summary("移至 Trash", deletion_results))

    def _restore_paths(paths: Iterable[Path]) -> None:
        try:
            restore_results = restore_papers(ctx.vault, list(paths))
        except (OSError, ValueError) as ex:
            _recover_from_stale_action("恢复", ex)
            return
        if any(
            result.error and "duplicate Paper code" in result.error
            for result in restore_results
        ):
            message = "现有 Paper 代号冲突；历史代号不会改写，冲突项仍留在 Trash。"
        else:
            message = _result_summary("恢复", restore_results)
        _refresh_after_mutation(message)

    def _run_permanent_delete(
        paths: list[Path],
        *,
        folder: str | None,
        clear_all: bool,
        dialog: ft.AlertDialog,
    ) -> None:
        try:
            deletion_results = permanently_delete_papers(ctx.vault, paths)
            if folder is not None and folder in list_trashed_folders(ctx.vault):
                remaining = [
                    path
                    for path in list_trashed_papers(ctx.vault)
                    if path.parent == Path(".trash/cache") / folder
                ]
                if not remaining:
                    deletion_results.append(
                        permanently_delete_folder(ctx.vault, folder)
                    )
            if clear_all:
                for empty_folder in list_trashed_folders(ctx.vault):
                    remaining = [
                        path
                        for path in list_trashed_papers(ctx.vault)
                        if path.parent == Path(".trash/cache") / empty_folder
                    ]
                    if not remaining:
                        deletion_results.append(
                            permanently_delete_folder(ctx.vault, empty_folder)
                        )
        except (OSError, ValueError) as ex:
            _close_dialog(page)
            _recover_from_stale_action("永久删除", ex)
            return
        _close_dialog(page)
        _refresh_after_mutation(_result_summary("永久删除", deletion_results))

    def _confirm_permanent_delete(
        paths: list[Path],
        *,
        folder: str | None = None,
        label: str,
        clear_all: bool = False,
    ) -> None:
        count = len(paths)
        execute_field = (
            single_line_field("输入 execute")
            if count >= 4
            else None
        )
        error = ft.Text("", color=ft.Colors.ERROR, size=12)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("确认永久删除"),
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"{label}；共 {count} 个 Paper。此操作不可恢复。"
                    ),
                    *(
                        [
                            ft.Text("请输入小写 execute 后继续。", color=MUTED),
                            execute_field,
                        ]
                        if execute_field is not None
                        else []
                    ),
                    error,
                ],
                tight=True,
                spacing=SPACE_3,
            ),
            actions=[],
            key="permanent-delete-dialog",
        )

        def confirm(_: ft.ControlEvent) -> None:
            if (
                execute_field is not None
                and (execute_field.value or "").strip() != "execute"
            ):
                error.value = "请输入完全一致的小写 execute。"
                page.update()
                return
            _run_permanent_delete(
                paths,
                folder=folder,
                clear_all=clear_all,
                dialog=dialog,
            )

        dialog.actions = [
            ft.TextButton(
                content=ft.Text("取消"),
                on_click=lambda _e: _close_dialog(page),
            ),
            danger_button("永久删除", confirm),
        ]
        _show_dialog(page, dialog)

    def _show_create_folder(_: ft.ControlEvent) -> None:
        name_field = single_line_field("新文件夹名称")
        error = ft.Text("", color=ft.Colors.ERROR, size=12)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("新建文件夹"),
            content=ft.Column(
                controls=[name_field, error],
                tight=True,
                spacing=SPACE_3,
            ),
            actions=[],
            key="create-folder-dialog",
        )

        def create(_: ft.ControlEvent) -> None:
            try:
                create_folder(ctx.vault, name_field.value or "")
            except (OSError, ValueError, FileExistsError) as ex:
                error.value = f"无法新建文件夹：{ex}"
                page.update()
                return
            _close_dialog(page)
            _set_operation("文件夹已创建")
            refresh()

        dialog.actions = [
            ft.TextButton(
                content=ft.Text("取消"),
                on_click=lambda _e: _close_dialog(page),
            ),
            ft.Button(content=ft.Text("创建"), on_click=create),
        ]
        _show_dialog(page, dialog)

    def _show_merge_confirmation(
        source: str,
        destination: str,
    ) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("合并同名文件夹"),
            content=ft.Text(
                f"“{source}”将合并到“{destination}”。冲突项保留在原文件夹并逐项报告。"
            ),
            actions=[],
            key="merge-folder-dialog",
        )

        def merge(_: ft.ControlEvent) -> None:
            try:
                merge_results = merge_folders(ctx.vault, source, destination)
            except (OSError, ValueError) as ex:
                _close_dialog(page)
                _close_dialog(page)
                _recover_from_stale_action("合并文件夹", ex)
                return
            _cancel_selection_for_scope_change()
            _close_dialog(page)
            _close_dialog(page)
            message = (
                _result_summary("合并文件夹", merge_results)
                if merge_results
                else "合并文件夹：空文件夹已合并"
            )
            _refresh_after_mutation(message)

        dialog.actions = [
            ft.TextButton(
                content=ft.Text("取消"),
                on_click=lambda _e: _close_dialog(page),
            ),
            ft.Button(content=ft.Text("确认合并"), on_click=merge),
        ]
        _show_dialog(page, dialog)

    def _show_rename_folder(folder: str) -> None:
        name_field = single_line_field("文件夹新名称", folder)
        error = ft.Text("", color=ft.Colors.ERROR, size=12)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"重命名“{folder}”"),
            content=ft.Column(
                controls=[name_field, error],
                tight=True,
                spacing=SPACE_3,
            ),
            actions=[],
            key="rename-folder-dialog",
        )

        def rename(_: ft.ControlEvent) -> None:
            requested = (name_field.value or "").strip()
            existing = next(
                (
                    name
                    for name in list_active_folders(ctx.vault)
                    if name != folder and _folder_key(name) == _folder_key(requested)
                ),
                None,
            )
            if existing is not None:
                _show_merge_confirmation(folder, existing)
                return
            try:
                rename_folder(ctx.vault, folder, requested)
            except (OSError, ValueError, FileExistsError) as ex:
                error.value = f"无法重命名文件夹：{ex}"
                page.update()
                return
            _cancel_selection_for_scope_change()
            _close_dialog(page)
            _set_operation("文件夹已重命名")
            refresh()

        dialog.actions = [
            ft.TextButton(
                content=ft.Text("取消"),
                on_click=lambda _e: _close_dialog(page),
            ),
            ft.Button(content=ft.Text("重命名"), on_click=rename),
        ]
        _show_dialog(page, dialog)

    def _trash_folder(folder: str) -> None:
        try:
            folder_results = soft_delete_folder(ctx.vault, folder)
        except (OSError, ValueError) as ex:
            _recover_from_stale_action("文件夹移至 Trash", ex)
            return
        _cancel_selection_for_scope_change()
        _refresh_after_mutation(_result_summary("文件夹移至 Trash", folder_results))

    def _restore_trash_folder(folder: str) -> None:
        try:
            folder_results = restore_folder(ctx.vault, folder)
        except (OSError, ValueError) as ex:
            _recover_from_stale_action("恢复文件夹", ex)
            return
        _refresh_after_mutation(_result_summary("恢复文件夹", folder_results))

    def _cancel_selection_for_scope_change() -> None:
        nonlocal selection_notice_generation
        cancelled = len(selected_paths)
        selected_paths.clear()
        if not cancelled:
            return
        selection_notice_generation += 1
        generation = selection_notice_generation
        selection_notice.value = f"已取消选择的 {cancelled} 个 Paper"
        if hasattr(page, "run_task"):
            page.run_task(_clear_selection_notice_after_delay, generation)

    def _set_scope(scope: str) -> None:
        nonlocal current_scope
        if scope == current_scope:
            return
        _cancel_selection_for_scope_change()
        current_scope = scope
        refresh()

    async def _clear_selection_notice_after_delay(generation: int) -> None:
        await asyncio.sleep(2)
        if generation != selection_notice_generation:
            return
        selection_notice.value = ""
        page.update()

    def _scope_button(
        text: str,
        scope: str,
        *,
        destination: str | None | object = ...,
    ) -> ft.Control:
        selected = current_scope == scope
        button = ft.Button(
            content=ft.Text(text),
            key=f"library-scope-{scope}",
            on_click=lambda _e: _set_scope(scope),
            bgcolor=(
                ACCENT
                if selected
                else FG
                if scope_in_sidebar
                else None
            ),
            color=(
                ACCENT_ON
                if selected
                else SURFACE_WARM
                if scope_in_sidebar
                else FG
            ),
            elevation=0,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            ),
        )
        if destination is ...:
            return button

        def accept(_: object) -> None:
            path = drag_state.get("path")
            if path:
                _apply_move([path], destination if isinstance(destination, str) else None)
            drag_state["path"] = None

        return ft.DragTarget(
            group="library-paper",
            data=destination,
            content=button,
            on_accept=accept,
            key=f"library-drop-{scope}",
            expand=scope.startswith(_FOLDER_PREFIX),
        )

    def _render_scopes(
        folders: list[str],
        trash_count: int,
    ) -> None:
        scope_controls.controls = [
            ft.Text(
                "LIBRARY",
                color=SURFACE_WARM if scope_in_sidebar else MUTED,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            _scope_button("全部 Paper", _SCOPE_ALL),
            _scope_button("未归类", _SCOPE_UNFILED, destination=None),
        ]
        for folder in folders:
            def folder_menu_items(name: str = folder) -> list[ft.PopupMenuItem]:
                return [
                    ft.PopupMenuItem(
                        content="重命名",
                        on_click=lambda _e: _show_rename_folder(name),
                    ),
                    ft.PopupMenuItem(
                        content="移至 Trash",
                        on_click=lambda _e: _trash_folder(name),
                    ),
                ]

            menu = ft.PopupMenuButton(
                icon=ft.Icons.MORE_HORIZ,
                icon_color=SURFACE_WARM if scope_in_sidebar else FG,
                tooltip=f"{folder} 文件夹菜单",
                key=f"folder-menu-{folder}",
                items=folder_menu_items(),
            )
            context_menu = ft.ContextMenu(
                content=ft.Container(width=1, height=1),
                items=folder_menu_items(),
                width=1,
                height=1,
                right=0,
                bottom=0,
                opacity=0,
                key=f"folder-context-menu-{folder}",
            )

            def open_folder_context(event: object, target=context_menu) -> None:
                page.run_task(
                    target.open,
                    getattr(event, "global_position", None),
                    None,
                )

            scope_controls.controls.append(
                ft.GestureDetector(
                    content=ft.Stack(
                        controls=[
                            ft.Row(
                                controls=[
                                    _scope_button(
                                        folder,
                                        _scope_for_folder(folder),
                                        destination=folder,
                                    ),
                                    menu,
                                ],
                                spacing=SPACE_2,
                            ),
                            context_menu,
                        ],
                    ),
                    on_secondary_tap_down=open_folder_context,
                    expand=True,
                )
            )
        scope_controls.controls.extend(
            [
                ft.OutlinedButton(
                    content=ft.Text("新建文件夹"),
                    icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED,
                    style=ft.ButtonStyle(
                        color=SURFACE_WARM if scope_in_sidebar else FG,
                    ),
                    on_click=_show_create_folder,
                    key="library-create-folder",
                ),
                ft.Divider(),
                _scope_button(f"Trash · {trash_count}", _SCOPE_TRASH),
            ]
        )

    def _active_row(
        entry: dict[str, object],
        folders: list[str],
    ) -> ft.Control:
        rel_path = str(entry["path"])
        code = str(entry["code"])
        display_name = entry.get("display_name")
        title = (
            str(display_name)
            if isinstance(display_name, str) and display_name
            else code
        )
        summary = str(entry.get("summary", ""))
        folder = entry.get("folder")
        tags = [tag for tag in entry.get("tags", []) if isinstance(tag, str)]
        checkbox = ft.Checkbox(
            value=rel_path in selected_paths,
            semantics_label=f"选择 {title}",
            key=f"paper-select-{rel_path}",
        )

        def select(_: ft.ControlEvent) -> None:
            if checkbox.value:
                selected_paths.add(rel_path)
            else:
                selected_paths.discard(rel_path)
            refresh()

        checkbox.on_change = select

        def on_edit(_: ft.ControlEvent) -> None:
            try:
                path = resolve_active_paper_path(ctx.vault, rel_path)
            except (OSError, ValueError) as ex:
                notify(page, f"无法打开 Paper：{ex}")
                return
            ctx.open_paper(path.relative_to(ctx.vault))

        def on_open_system(_: ft.ControlEvent) -> None:
            try:
                path = resolve_active_paper_path(ctx.vault, rel_path)
            except (OSError, ValueError) as ex:
                notify(page, f"无法打开文件：{ex}")
                return
            _open_with_system(page, path)

        def on_reveal(_: ft.ControlEvent) -> None:
            try:
                path = resolve_active_paper_path(ctx.vault, rel_path)
            except (OSError, ValueError) as ex:
                notify(page, f"无法在文件夹中显示：{ex}")
                return
            _reveal_in_folder(page, path)

        def paper_menu_items() -> list[ft.PopupMenuItem]:
            return [
                *_move_menu_items(rel_path, folders),
                ft.PopupMenuItem(
                    content="复制分支",
                    on_click=lambda _e: _branch(rel_path),
                ),
                ft.PopupMenuItem(content="打开", on_click=on_open_system),
                ft.PopupMenuItem(content="在文件夹中显示", on_click=on_reveal),
                ft.PopupMenuItem(
                    content="移至 Trash",
                    on_click=lambda _e: _trash_active([rel_path]),
                ),
            ]

        menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_HORIZ,
            tooltip=f"{title} 菜单",
            key=f"paper-menu-{rel_path}",
            items=paper_menu_items(),
        )
        row = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            checkbox,
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        title,
                                        color=FG,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    ft.Text(
                                        f"{code} · {folder or '未归类'}",
                                        color=MUTED,
                                        size=12,
                                    ),
                                ],
                                spacing=SPACE_1,
                                expand=True,
                            ),
                            menu,
                        ],
                        spacing=SPACE_2,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                content=ft.Text("编辑"),
                                on_click=on_edit,
                            ),
                            ft.OutlinedButton(
                                content=ft.Text("打开 Flashcard"),
                                on_click=lambda _e: ctx.open_flashcards(Path(rel_path)),
                            ),
                            ft.OutlinedButton(
                                content=ft.Text("打开"),
                                on_click=on_open_system,
                                key=f"paper-open-{rel_path}",
                            ),
                            ft.OutlinedButton(
                                content=ft.Text("在文件夹中显示"),
                                on_click=on_reveal,
                                key=f"paper-reveal-{rel_path}",
                            ),
                            danger_button(
                                "删除",
                                lambda _e: _trash_active([rel_path]),
                            ),
                        ],
                        spacing=SPACE_2,
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(summary, color=FG, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(
                        "Tags：" + ("、".join(tags) if tags else "未添加"),
                        size=12,
                        color=MUTED,
                    ),
                ],
                spacing=SPACE_2,
            ),
            padding=ft.Padding.symmetric(vertical=SPACE_3),
            border=ft.Border.only(bottom=ft.BorderSide(width=1, color=BORDER_SOFT)),
        )

        def start_drag(_: object) -> None:
            drag_state["path"] = rel_path

        context_menu = ft.ContextMenu(
            content=ft.Container(width=1, height=1),
            items=paper_menu_items(),
            width=1,
            height=1,
            right=0,
            bottom=0,
            opacity=0,
            key=f"paper-context-menu-{rel_path}",
        )

        def open_paper_context(event: object) -> None:
            page.run_task(
                context_menu.open,
                getattr(event, "global_position", None),
                None,
            )

        return ft.Draggable(
            group="library-paper",
            data=rel_path,
            content=ft.GestureDetector(
                content=ft.Stack(controls=[row, context_menu]),
                on_secondary_tap_down=open_paper_context,
            ),
            content_feedback=ft.Text(title),
            on_drag_start=start_drag,
            key=f"paper-drag-{rel_path}",
        )

    def _trash_row(rel_path: Path) -> ft.Control:
        try:
            paper, _source_bytes = read_paper_snapshot(ctx.vault / rel_path)
            delete_label = (
                f"{paper.display_name} ({paper.code})"
                if paper.display_name
                else paper.code
            )
        except (OSError, ValueError):
            delete_label = rel_path.name

        def restore(_: ft.ControlEvent) -> None:
            _restore_paths([rel_path])

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(delete_label, color=FG, expand=True),
                    ft.OutlinedButton(content=ft.Text("恢复"), on_click=restore),
                    danger_button(
                        "永久删除",
                        lambda _e: _confirm_permanent_delete(
                            [rel_path],
                            label=delete_label,
                        ),
                    ),
                ],
                spacing=SPACE_3,
            ),
            padding=ft.Padding.symmetric(vertical=SPACE_3),
            border=ft.Border.only(bottom=ft.BorderSide(width=1, color=BORDER_SOFT)),
        )

    def _trash_entry(rel_path: Path) -> dict[str, object]:
        try:
            paper, _source_bytes = read_paper_snapshot(ctx.vault / rel_path)
        except (OSError, ValueError):
            return {
                "path": str(rel_path),
                "code": rel_path.stem,
                "display_name": None,
                "summary": "",
                "tags": [],
                "highlight_names": [],
                "created": "",
                "updated": "",
            }
        return {
            "path": str(rel_path),
            "code": paper.code,
            "display_name": paper.display_name,
            "summary": paper.summary,
            "tags": list(paper.tags),
            "highlight_names": [
                highlight.display_name
                for highlight in paper.highlights
                if highlight.display_name
            ],
            "created": paper.created.isoformat(),
            "updated": paper.updated.isoformat(),
        }

    def _render_trash(
        visible_trashed: list[Path],
        trash_folders: list[str],
        all_trashed: list[Path],
        *,
        filtered: bool,
    ) -> None:
        count_label = f"Trash · {len(all_trashed)}"
        if filtered:
            count_label += f" · 显示 {len(visible_trashed)}"
        results.controls.append(
            ft.Row(
                controls=[
                    ft.Text(
                        count_label,
                        size=18,
                        font_family=FONT_DISPLAY,
                        color=FG,
                    ),
                    danger_button(
                        "清空 Trash",
                        lambda _e: _confirm_permanent_delete(
                            all_trashed,
                            label="清空 Trash",
                            clear_all=True,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )
        root_papers = [path for path in visible_trashed if len(path.parts) == 3]
        results.controls.extend(_trash_row(path) for path in root_papers)
        for folder in trash_folders:
            folder_path = Path(".trash/cache") / folder
            visible_folder_papers = [
                path for path in visible_trashed if path.parent == folder_path
            ]
            all_folder_papers = [
                path for path in all_trashed if path.parent == folder_path
            ]
            if filtered and not visible_folder_papers:
                continue
            results.controls.append(
                ft.ExpansionTile(
                    title=ft.Text(
                        f"{folder} · {len(all_folder_papers)}",
                        weight=ft.FontWeight.W_600,
                    ),
                    controls=[
                        ft.Row(
                            controls=[
                                ft.OutlinedButton(
                                    content=ft.Text("恢复文件夹"),
                                    on_click=lambda _e, name=folder: _restore_trash_folder(
                                        name
                                    ),
                                ),
                                danger_button(
                                    "永久删除文件夹",
                                    lambda _e, name=folder, paths=all_folder_papers: _confirm_permanent_delete(
                                        paths,
                                        folder=name,
                                        label=f"文件夹 {name}",
                                    ),
                                ),
                            ],
                            spacing=SPACE_3,
                            wrap=True,
                        ),
                        *[_trash_row(path) for path in visible_folder_papers],
                    ],
                    controls_padding=SPACE_3,
                    maintain_state=True,
                    collapsed_shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                    shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                    key=f"trash-folder-{folder}",
                )
            )
        if filtered and not visible_trashed:
            results.controls.append(
                ft.Text("Trash 中没有符合搜索条件的 Paper。", color=MUTED)
            )
        elif not all_trashed and not trash_folders:
            results.controls.append(ft.Text("Trash 为空。", color=MUTED))

    def _entry_search_text(entry: dict[str, object]) -> str:
        values = [
            value
            for value in (
                entry.get("display_name"),
                entry.get("code"),
                entry.get("summary"),
            )
            if isinstance(value, str)
        ]
        for key in ("tags", "highlight_names"):
            values.extend(
                value
                for value in entry.get(key, [])
                if isinstance(value, str)
            )
        return _folder_key(" ".join(values))

    def _sort_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
        mode = sort_field.value or "updated_desc"
        if mode == "name":
            return sorted(
                entries,
                key=lambda entry: (
                    _folder_key(
                        str(entry.get("display_name") or entry.get("code", ""))
                    ),
                    str(entry.get("code", "")),
                    str(entry.get("path", "")),
                ),
            )
        if mode == "created_asc":
            return sorted(
                entries,
                key=lambda entry: (
                    str(entry.get("created", "")),
                    str(entry.get("path", "")),
                ),
            )
        field = "created" if mode == "created_desc" else "updated"
        return sorted(
            entries,
            key=lambda entry: (
                str(entry.get(field, "")),
                str(entry.get("path", "")),
            ),
            reverse=True,
        )

    def _select_all(_: ft.ControlEvent) -> None:
        selected_paths.update(str(entry["path"]) for entry in visible_active)
        refresh()

    def _clear_selection(_: ft.ControlEvent) -> None:
        selected_paths.clear()
        refresh()

    def _batch_move(_: ft.ControlEvent) -> None:
        if not selected_paths:
            _set_operation("请先选择 Paper")
            page.update()
            return
        value = batch_destination.value
        if value is None:
            _set_operation("请选择目标文件夹")
            page.update()
            return
        _apply_move(
            sorted(selected_paths),
            None if value == _BATCH_UNFILED_KEY else value,
        )

    def refresh(
        _: ft.ControlEvent | None = None,
        *,
        rebuild: bool = False,
    ) -> None:
        nonlocal current_scope, visible_active
        if rebuild:
            rebuild_index(ctx.vault)
        papers = list_papers(ctx.vault)
        errors = list_index_errors(ctx.vault)
        folders = list_active_folders(ctx.vault)
        trashed = list_trashed_papers(ctx.vault)
        trash_folders = list_trashed_folders(ctx.vault)
        requested_folder = _folder_from_scope(current_scope)
        if requested_folder is not None and requested_folder not in folders:
            _cancel_selection_for_scope_change()
            current_scope = _SCOPE_ALL
        _render_scopes(folders, len(trashed))

        batch_destination.options = [
            ft.DropdownOption(key=_BATCH_UNFILED_KEY, text="未归类"),
            *[
                ft.DropdownOption(key=folder, text=folder)
                for folder in folders
            ],
        ]
        query = _folder_key((search_field.value or "").strip())
        scoped = papers
        if current_scope == _SCOPE_UNFILED:
            scoped = [entry for entry in papers if entry.get("folder") is None]
        elif current_scope.startswith(_FOLDER_PREFIX):
            folder = _folder_from_scope(current_scope)
            scoped = [entry for entry in papers if entry.get("folder") == folder]
        visible_active = _sort_entries(
            [
                entry
                for entry in scoped
                if not query or query in _entry_search_text(entry)
            ]
        )

        results.controls.clear()
        if current_scope == _SCOPE_TRASH:
            trash_entries = _sort_entries(
                [
                    entry
                    for entry in (_trash_entry(path) for path in trashed)
                    if not query or query in _entry_search_text(entry)
                ]
            )
            _render_trash(
                [Path(str(entry["path"])) for entry in trash_entries],
                trash_folders,
                trashed,
                filtered=bool(query),
            )
        else:
            scope_label = (
                "全部 Paper"
                if current_scope == _SCOPE_ALL
                else "未归类"
                if current_scope == _SCOPE_UNFILED
                else _folder_from_scope(current_scope) or "全部 Paper"
            )
            results.controls.extend(
                [
                    ft.Column(
                        controls=[
                            ft.Text(
                                f"{scope_label} · {len(visible_active)}",
                                size=18,
                                font_family=FONT_DISPLAY,
                                color=FG,
                            ),
                            ft.Row(
                                controls=[
                                    ft.OutlinedButton(
                                        content=ft.Text("全选当前"),
                                        on_click=_select_all,
                                    ),
                                    ft.OutlinedButton(
                                        content=ft.Text("取消全选"),
                                        on_click=_clear_selection,
                                    ),
                                ],
                                spacing=SPACE_2,
                                wrap=True,
                            ),
                        ],
                        spacing=SPACE_2,
                    ),
                    selection_notice,
                    ft.Row(
                        controls=[
                            batch_destination,
                            ft.OutlinedButton(
                                content=ft.Text("移动所选"),
                                on_click=_batch_move,
                            ),
                            danger_button(
                                "所选移至 Trash",
                                lambda _e: _trash_active(sorted(selected_paths)),
                            ),
                            ft.Text(
                                f"已选择 {len(selected_paths)}",
                                color=MUTED,
                                size=12,
                            ),
                        ],
                        spacing=SPACE_3,
                        wrap=True,
                    ),
                ]
            )
            results.controls.extend(
                _active_row(entry, folders) for entry in visible_active
            )
            if not visible_active:
                if query:
                    empty = "当前范围没有符合搜索条件的 Paper。"
                elif current_scope == _SCOPE_ALL:
                    empty = "Vault 中还没有 Paper。"
                elif current_scope == _SCOPE_UNFILED:
                    empty = "没有未归类 Paper。"
                else:
                    empty = "这个文件夹为空。"
                results.controls.append(ft.Text(empty, color=MUTED))
            results.controls.append(ft.Divider())
            results.controls.append(
                ft.Text(
                    f"资产健康 · {len(errors)}",
                    size=18,
                    font_family=FONT_DISPLAY,
                    color=FG,
                )
            )
            if errors:
                results.controls.extend(
                    ft.Text(
                        f"损坏 Paper：{error.get('path', '')} — {error.get('reason', '')}",
                        color=ft.Colors.ERROR,
                    )
                    for error in errors
                )
            else:
                results.controls.append(
                    ft.Text("所有活动 Paper 都可读取。", color=MUTED)
                )
        page.update()

    search_field.on_change = refresh
    sort_field.on_select = refresh

    def on_keyboard(event: object) -> None:
        key = str(getattr(event, "key", "")).upper()
        if key in {"ESC", "ESCAPE"}:
            close_top_dialog(page)
        elif (
            key == "F"
            and bool(getattr(event, "meta", False))
        ):
            page.run_task(search_field.focus)

    page.on_keyboard_event = on_keyboard
    refresh(rebuild=True)

    library_card = paper_card(
        [
            ft.Row(
                controls=[
                    search_field,
                    sort_field,
                    ft.OutlinedButton(
                        content=ft.Text("刷新"),
                        on_click=lambda _e: refresh(rebuild=True),
                    ),
                ],
                wrap=True,
                spacing=SPACE_3,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            operation_status,
            ft.Divider(),
            ft.Row(
                controls=(
                    [results]
                    if scope_in_sidebar
                    else [
                        ft.Container(
                            content=scope_controls,
                            width=160,
                            padding=SPACE_3,
                            bgcolor=SURFACE_WARM,
                            border=ft.Border.all(1, BORDER),
                            border_radius=RADIUS_SM,
                        ),
                        ft.VerticalDivider(width=1, color=BORDER),
                        results,
                    ]
                ),
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        key="library-paper-card",
        spacing=SPACE_4,
        expand=True,
    )
    vault_card = paper_card(
        [
            ft.Text("Vault 路径", size=18, font_family=FONT_DISPLAY, color=FG),
            ft.Row(
                controls=[
                    ft.Text(
                        str(ctx.vault),
                        width=360,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        color=MUTED,
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("在文件夹中显示"),
                        on_click=on_reveal_vault,
                        key="library-reveal-vault",
                    ),
                    ft.OutlinedButton(
                        content=ft.Text("更换 Vault…"),
                        on_click=lambda _e: ctx.change_vault(),
                    ),
                ],
                wrap=True,
                spacing=SPACE_3,
            ),
            ft.Text(
                "写入仅允许当前用户 Home 内路径；尚未启用 Apple App Sandbox。",
                color=MUTED,
                size=12,
            ),
        ],
        key="library-vault-card",
        spacing=SPACE_3,
    )
    return ft.Column(
        controls=[
            page_header(
                "本地文件库",
                "在当前文件夹范围内检索、移动、分支与恢复 Paper。",
                "VAULT · PAPER 资产",
            ),
            vault_card,
            library_card,
        ],
        spacing=SPACE_6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
