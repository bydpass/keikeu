"""keikeu Flet shell for the current macOS Paper flow.

The GUI only routes user actions to public ``keikeu_core`` APIs.  Markdown,
JSON, migration, and asset recovery remain in the pure-Python core layer.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Callable

import flet as ft

from keikeu_app.local_state import STATE_PATH as DEVICE_STATE_PATH, claim_daily_card
from keikeu_app.pages import build_flashcard_page, build_library_page, build_paper_page
from keikeu_app.pages.migration_page import build_migration_page
from keikeu_app.theme import (
    ACCENT,
    ACCENT_ON,
    BG,
    FG,
    FONT_DISPLAY,
    MUTED,
    RADIUS_SM,
    SIDEBAR_WIDTH,
    SPACE_2,
    SPACE_4,
    SPACE_8,
    SURFACE_WARM,
    TEXT_SM,
    apply_theme,
)
from keikeu_app.widgets import notify, paper_card, primary_button, single_line_field
from keikeu_core.indexer import rebuild_index
from keikeu_core.migration_v01 import inspect_v01_vault, is_v01_vault
from keikeu_core.vault import (
    VaultSelectionToken,
    capture_vault_selection_token,
    copy_vault_no_follow,
    get_vault,
    init_vault,
    is_vault,
    list_active_papers,
    open_directory_no_follow,
    require_home_path,
    resolve_active_paper_path,
    set_vault,
    validate_regular_tree_no_follow,
    validate_vault_papers,
    validate_vault_tree_no_follow,
    vault_index_version,
)

__all__ = ["main", "run", "AppContext", "CONFIG_PATH"]

CONFIG_PATH = Path.home() / ".keikeu_config.json"
INITIAL_WINDOW_WIDTH = 890
INITIAL_WINDOW_HEIGHT = 741

_NAV_PAPER = 0
_NAV_FLASHCARD = 1
_NAV_LIBRARY = 2

_SOURCE_V01 = "v0.1"
_SOURCE_PAPER = "Paper v2/v3"


def _classify_vault_source_no_follow(source: Path) -> str:
    """Return the supported source format after a read-only regular-tree scan."""
    validate_regular_tree_no_follow(source)
    version = vault_index_version(source)
    if version in {2, 3}:
        if not is_vault(source):
            raise ValueError(f"index v{version} 的 Vault 结构不完整")
        return _SOURCE_PAPER
    if version == 1:
        if not is_v01_vault(source):
            raise ValueError("index v1 未匹配可迁移的 v0.1 Vault")
        return _SOURCE_V01
    if version is not None:
        raise ValueError(f"不支持的 Vault index version：{version}")
    if is_v01_vault(source):
        return _SOURCE_V01
    if is_vault(source):
        return _SOURCE_PAPER
    raise ValueError("该文件夹不是受支持的 v0.1 或 Paper v2/v3 Vault")


def _classify_configured_home_vault(source: Path) -> str:
    """Classify a Home Vault while leaving isolated Paper path errors visible."""
    version = vault_index_version(source)
    if version in {2, 3}:
        if not is_vault(source):
            raise ValueError(f"index v{version} 的 Vault 结构不完整")
        return _SOURCE_PAPER
    if version is None and is_vault(source):
        return _SOURCE_PAPER
    validate_regular_tree_no_follow(source)
    if version == 1 and is_v01_vault(source):
        return _SOURCE_V01
    if version is not None:
        raise ValueError(f"不支持的 Vault index version：{version}")
    if is_v01_vault(source):
        return _SOURCE_V01
    raise ValueError("该文件夹不是受支持的 v0.1 或 Paper v2/v3 Vault")


def _has_unsupported_paper_schema(index: dict[str, object]) -> bool:
    errors = index.get("errors")
    return isinstance(errors, list) and any(
        isinstance(error, dict)
        and "schema_version: 2 or 3" in str(error.get("reason", ""))
        for error in errors
    )


def _validated_rebuild(
    vault: Path,
    *,
    require_clean_papers: bool = True,
) -> VaultSelectionToken:
    """Strictly validate one unchanged Paper candidate and bind its final bytes."""
    before = capture_vault_selection_token(vault)
    if _classify_vault_source_no_follow(vault) != _SOURCE_PAPER:
        raise ValueError("Vault 状态已变化；请重新检查后再确认")
    validate_vault_tree_no_follow(vault)
    if require_clean_papers:
        validate_vault_papers(vault)
    index = rebuild_index(vault)
    errors = index.get("errors")
    if not isinstance(errors, list):
        raise ValueError("索引重建没有返回可验证的 errors 列表")
    if errors:
        if _has_unsupported_paper_schema(index):
            raise ValueError("检测到当前运行时不支持的 Paper schema；未切换")
        if require_clean_papers:
            raise ValueError(f"Vault 有 {len(errors)} 个无法验证的 Paper")
    if _classify_vault_source_no_follow(vault) != _SOURCE_PAPER:
        raise ValueError("Vault 在索引重建期间发生变化；未切换")
    final = capture_vault_selection_token(vault)
    if final.path != before.path or final.root_identity != before.root_identity:
        raise ValueError("Vault 根目录在验证期间发生变化；未切换")
    return final


def _validated_v01_selection(vault: Path) -> VaultSelectionToken:
    """Bind a v0.1 manifest preflight between two immutable snapshots."""
    before = capture_vault_selection_token(vault)
    if _classify_vault_source_no_follow(vault) != _SOURCE_V01:
        raise ValueError("v0.1 Vault 在迁移预检后发生变化；未切换")
    preflight = inspect_v01_vault(vault)
    if not preflight.ready:
        blockers = "、".join(
            str(issue.path.relative_to(vault)) for issue in preflight.issues
        )
        raise ValueError(
            f"v0.1 迁移预检未通过（{len(preflight.issues)} 个阻塞项）：{blockers}"
        )
    if _classify_vault_source_no_follow(vault) != _SOURCE_V01:
        raise ValueError("v0.1 Vault 在迁移预检后发生变化；未切换")
    final = capture_vault_selection_token(vault)
    if final != before:
        raise ValueError("v0.1 Vault 在迁移预检后发生变化；未切换")
    return final


@dataclass
class AppContext:
    """The active vault and page-navigation callbacks shared by GUI builders."""

    page: ft.Page
    vault: Path
    library_scope_host: ft.Column | None = None
    open_paper: Callable[[Path | None], None] = field(default=lambda _path: None)
    open_flashcards: Callable[[Path | None], None] = field(default=lambda _path: None)
    open_library: Callable[[], None] = field(default=lambda: None)
    change_vault: Callable[[], None] = field(default=lambda: None)


def _configure_window(page: ft.Page) -> None:
    page.window.width = INITIAL_WINDOW_WIDTH
    page.window.height = INITIAL_WINDOW_HEIGHT


def _pin_home_vault_root(
    vault: Path,
    expected_identity: tuple[int, int] | None = None,
) -> tuple[Path, tuple[int, int]]:
    """Return one exact Home root and reject symlink or identity replacement."""
    raw_vault = vault.expanduser().absolute()
    root_fd = open_directory_no_follow(raw_vault)
    try:
        safe_vault = require_home_path(raw_vault)
        safe_fd = open_directory_no_follow(safe_vault)
        try:
            raw_stat = os.fstat(root_fd)
            safe_stat = os.fstat(safe_fd)
            identity = (raw_stat.st_dev, raw_stat.st_ino)
            if identity != (safe_stat.st_dev, safe_stat.st_ino):
                raise ValueError("Vault root changed during validation")
            if expected_identity is not None and identity != expected_identity:
                raise ValueError("Vault root changed after selection")
            return safe_vault, identity
        finally:
            os.close(safe_fd)
    finally:
        os.close(root_fd)


def _build_shell(
    page: ft.Page,
    vault: Path,
    *,
    expected_root_identity: tuple[int, int] | None = None,
) -> None:
    """Build the Paper / Flashcard / Library navigation shell."""
    vault, root_identity = _pin_home_vault_root(vault, expected_root_identity)
    apply_theme(page)
    page.controls.clear()
    page.scroll = None
    body = ft.Container(expand=True, padding=SPACE_8, bgcolor=BG)
    library_scope_host = ft.Column(
        controls=[],
        spacing=SPACE_2,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        key="shell-library-scopes",
    )
    ctx = AppContext(
        page=page,
        vault=vault,
        library_scope_host=library_scope_host,
    )
    current_nav = _NAV_PAPER
    nav_buttons: dict[int, ft.Button] = {}

    def sync_navigation() -> None:
        for index, button in nav_buttons.items():
            selected = index == current_nav
            button.bgcolor = ACCENT if selected else FG
            button.color = ACCENT_ON if selected else SURFACE_WARM

    def show_paper(open_path: Path | None = None) -> None:
        nonlocal current_nav
        previous_scopes = list(library_scope_host.controls)
        previous_handler = getattr(page, "on_keyboard_event", None)
        try:
            safe_path = (
                resolve_active_paper_path(vault, open_path)
                if open_path is not None
                else None
            )
            relative = safe_path.relative_to(vault) if safe_path is not None else None
            new_content = build_paper_page(ctx, relative)
            library_scope_host.controls.clear()
            if getattr(page, "on_keyboard_event", None) is previous_handler:
                page.on_keyboard_event = None
            current_nav = _NAV_PAPER
            sync_navigation()
            body.content = new_content
            page.update()
        except Exception as ex:
            library_scope_host.controls = previous_scopes
            page.on_keyboard_event = previous_handler
            sync_navigation()
            notify(page, f"无法打开 Paper：{ex}")

    def show_flashcards(open_path: Path | None = None) -> None:
        nonlocal current_nav
        previous_scopes = list(library_scope_host.controls)
        previous_handler = getattr(page, "on_keyboard_event", None)
        try:
            safe_path = (
                resolve_active_paper_path(vault, open_path)
                if open_path is not None
                else None
            )
            relative = safe_path.relative_to(vault) if safe_path is not None else None
            new_content = build_flashcard_page(ctx, relative)
            library_scope_host.controls.clear()
            if getattr(page, "on_keyboard_event", None) is previous_handler:
                page.on_keyboard_event = None
            current_nav = _NAV_FLASHCARD
            sync_navigation()
            body.content = new_content
            page.update()
        except Exception as ex:
            library_scope_host.controls = previous_scopes
            page.on_keyboard_event = previous_handler
            sync_navigation()
            notify(page, f"无法打开 Flashcard：{ex}")

    def show_library() -> None:
        nonlocal current_nav
        previous_scopes = list(library_scope_host.controls)
        previous_handler = getattr(page, "on_keyboard_event", None)
        try:
            new_content = build_library_page(ctx)
            current_nav = _NAV_LIBRARY
            sync_navigation()
            body.content = new_content
            page.update()
        except Exception as ex:
            library_scope_host.controls = previous_scopes
            page.on_keyboard_event = previous_handler
            sync_navigation()
            notify(page, f"无法打开本地文件库：{ex}")

    ctx.open_paper = show_paper
    ctx.open_flashcards = show_flashcards
    ctx.open_library = show_library
    ctx.change_vault = lambda: _build_vault_picker(
        page,
        initial_path=vault,
        on_cancel=lambda: _build_shell(
            page,
            vault,
            expected_root_identity=root_identity,
        ),
    )

    def navigation_button(
        index: int,
        label: str,
        icon: ft.IconData,
        on_click: Callable[[], None],
    ) -> ft.Button:
        button = ft.Button(
            content=ft.Text(label),
            icon=icon,
            key=f"shell-nav-{index}",
            on_click=lambda _e: on_click(),
            color=SURFACE_WARM,
            elevation=0,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                alignment=ft.Alignment.CENTER_LEFT,
            ),
        )
        nav_buttons[index] = button
        return button

    sidebar = ft.Container(
        key="shell-sidebar",
        width=SIDEBAR_WIDTH,
        bgcolor=FG,
        padding=SPACE_4,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "K",
                        color=ACCENT_ON,
                        size=18,
                        font_family=FONT_DISPLAY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=34,
                    height=34,
                    bgcolor=ACCENT,
                    border_radius=RADIUS_SM,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    "KEIKEU",
                    size=22,
                    color=ACCENT_ON,
                    font_family=FONT_DISPLAY,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    "PERSONAL PAPER DESK",
                    size=10,
                    color=SURFACE_WARM,
                    font_family=FONT_DISPLAY,
                ),
                ft.Divider(color=SURFACE_WARM),
                navigation_button(
                    _NAV_PAPER,
                    "纸片",
                    ft.Icons.EDIT_NOTE,
                    show_paper,
                ),
                navigation_button(
                    _NAV_FLASHCARD,
                    "Flashcard",
                    ft.Icons.STYLE,
                    show_flashcards,
                ),
                navigation_button(
                    _NAV_LIBRARY,
                    "本地文件库",
                    ft.Icons.FOLDER_OUTLINED,
                    show_library,
                ),
                library_scope_host,
                ft.Text(
                    "LOCAL PAPER UNIT\nV0.3 · OFFLINE READY",
                    size=TEXT_SM,
                    color=SURFACE_WARM,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=SPACE_2,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )
    sync_navigation()
    page.add(
        ft.Row(
            controls=[sidebar, ft.VerticalDivider(width=3, color=ACCENT), body],
            expand=True,
        )
    )
    show_paper()


def _build_daily_start(
    page: ft.Page,
    vault: Path,
    *,
    expected_root_identity: tuple[int, int] | None = None,
) -> None:
    """Show the one built-in daily card, then enter a blank Paper exactly once."""
    apply_theme(page)
    page.controls.clear()
    page.scroll = None
    finished = False

    def begin_writing() -> None:
        nonlocal finished
        if finished:
            return
        finished = True
        _build_shell(
            page,
            vault,
            expected_root_identity=expected_root_identity,
        )

    async def begin_after_delay() -> None:
        await asyncio.sleep(3)
        begin_writing()

    def on_keyboard(event: object) -> None:
        if str(getattr(event, "key", "")).upper() in {"ENTER", "RETURN"}:
            begin_writing()

    page.on_keyboard_event = on_keyboard
    page.add(
        ft.Container(
            expand=True,
            padding=SPACE_8,
            bgcolor=BG,
            alignment=ft.Alignment.CENTER,
            content=paper_card(
                [
                    ft.Text(
                        "玛格丽特·阿特伍德（意译）",
                        color=MUTED,
                    ),
                    ft.Text(
                        "写作像走迷宫。撞墙时，退回走错的路口，换一条路。",
                        size=24,
                        color=FG,
                        font_family=FONT_DISPLAY,
                        selectable=True,
                    ),
                    primary_button("开始写", lambda _e: begin_writing()),
                ],
                key="daily-start-card",
                spacing=SPACE_4,
            ),
        )
    )
    page.run_task(begin_after_delay)


def _build_startup(
    page: ft.Page,
    vault: Path,
    *,
    expected_root_identity: tuple[int, int] | None = None,
    state_path: Path | None = None,
) -> None:
    """Enter the daily card only after its date has been atomically claimed."""
    safe_vault, root_identity = _pin_home_vault_root(vault, expected_root_identity)
    selected_state_path = DEVICE_STATE_PATH if state_path is None else state_path
    try:
        show_daily = claim_daily_card(state_path=selected_state_path)
    except (OSError, ValueError):
        show_daily = False
    if show_daily:
        _build_daily_start(
            page,
            safe_vault,
            expected_root_identity=root_identity,
        )
        return
    _build_shell(
        page,
        safe_vault,
        expected_root_identity=root_identity,
    )


def _build_migration_gate(
    page: ft.Page,
    vault: Path,
    *,
    configured: bool = False,
    on_cancel: Callable[[], None] | None = None,
    expected_root_identity: tuple[int, int] | None = None,
) -> None:
    """Show a no-write v0.1 preflight before allowing Paper Vault actions."""
    vault, root_identity = _pin_home_vault_root(vault, expected_root_identity)
    validate_vault_tree_no_follow(vault)
    vault, root_identity = _pin_home_vault_root(vault, root_identity)
    apply_theme(page)
    page.controls.clear()
    page.scroll = None

    def open_migrated(_: object) -> None:
        try:
            safe_vault = require_home_path(vault)
            selection = _validated_rebuild(safe_vault)
            set_vault(safe_vault, CONFIG_PATH, selection)
            _build_startup(
                page,
                safe_vault,
                expected_root_identity=selection.root_identity,
            )
        except (OSError, ValueError) as ex:
            notify(page, f"无法打开已迁移的 Vault：{ex}；请检查路径后重试。")

    def choose_other() -> None:
        _build_vault_picker(
            page,
            initial_path=vault if configured else None,
            on_cancel=on_cancel,
        )

    page.add(
        ft.Container(
            expand=True,
            padding=SPACE_8,
            bgcolor=BG,
            content=build_migration_page(
                page,
                vault,
                on_open_migrated=open_migrated,
                on_choose_other=choose_other,
                expected_root_identity=root_identity,
            ),
        )
    )


def _build_vault_picker(
    page: ft.Page,
    *,
    show_configured: bool = True,
    initial_path: Path | None = None,
    on_cancel: Callable[[], None] | None = None,
    unsafe_source: Path | None = None,
    unsafe_source_kind: str = "",
    unsafe_reason: str = "",
    initial_error: str = "",
) -> None:
    """Classify a candidate read-only, then require confirmation before writes."""
    apply_theme(page)
    page.controls.clear()
    page.scroll = ft.ScrollMode.AUTO
    existing = initial_path
    if existing is None and show_configured:
        existing = get_vault(CONFIG_PATH)
    path_field = single_line_field("Vault 文件夹路径", str(existing) if existing is not None else "")
    path_field.hint_text = str(Path.home() / "keikeu-vault")
    path_field.expand = True
    error_text = ft.Text("", color=ft.Colors.ERROR)
    preview = ft.Column(controls=[], visible=False, spacing=SPACE_4, key="vault-preview")
    preview_generation = 0
    directory_picker = ft.FilePicker(key="vault-directory-picker")
    page.services.append(directory_picker)

    def invalidate_preview(*, update: bool = False) -> int:
        nonlocal preview_generation
        preview_generation += 1
        preview.controls.clear()
        preview.visible = False
        if update:
            page.update()
        return preview_generation

    def show_preview(controls: list[ft.Control], generation: int) -> None:
        if generation != preview_generation:
            return
        error_text.value = ""
        preview.controls[:] = controls
        preview.visible = True
        page.update()

    def show_error(message: str) -> None:
        invalidate_preview()
        error_text.value = message
        page.update()

    def show_action_error(message: str) -> None:
        error_text.value = message
        page.update()

    def open_safe_vault(vault: Path, generation: int) -> None:
        if generation != preview_generation:
            return
        try:
            safe_vault = require_home_path(vault)
            selection = _validated_rebuild(
                safe_vault,
                require_clean_papers=False,
            )
            set_vault(safe_vault, CONFIG_PATH, selection)
        except (OSError, ValueError) as ex:
            show_error(f"无法打开 Vault：{ex}；当前 Vault 未切换。")
            return
        notify(page, "Vault 已切换")
        _build_startup(
            page,
            safe_vault,
            expected_root_identity=selection.root_identity,
        )

    def initialize_vault(vault: Path, generation: int) -> None:
        if generation != preview_generation:
            return
        try:
            raw_vault = vault.expanduser().absolute()
            if os.path.lexists(raw_vault):
                validate_vault_tree_no_follow(raw_vault)
                descriptor = open_directory_no_follow(raw_vault)
                try:
                    with os.scandir(descriptor) as entries:
                        if next(entries, None) is not None:
                            raise ValueError("目标已不再为空；请重新检查，不会自动初始化")
                finally:
                    os.close(descriptor)
            else:
                require_home_path(raw_vault)
            init_vault(raw_vault)
            safe_vault = require_home_path(raw_vault)
            selection = _validated_rebuild(safe_vault)
            set_vault(safe_vault, CONFIG_PATH, selection)
        except (OSError, ValueError) as ex:
            show_error(f"无法初始化 Vault：{ex}；当前 Vault 未切换。")
            return
        notify(page, "Vault 已创建")
        _build_startup(
            page,
            safe_vault,
            expected_root_identity=selection.root_identity,
        )

    def show_relocation(
        source: Path,
        reason: str,
        source_kind: str,
        generation: int,
    ) -> None:
        destination_field = single_line_field("Home 内全新目标路径")
        destination_field.hint_text = str(Path.home() / f"{source.name or 'keikeu-vault'}-safe")
        destination_field.expand = True
        confirmation = ft.Checkbox(
            label="我确认：仅复制并验证到新位置；原路径不会被修改或删除。",
            key="vault-relocation-confirm",
        )
        relocate_button = primary_button("复制、验证并切换", lambda _e: None)
        relocate_button.disabled = True
        progress_text = ft.Text("", color=MUTED, key="vault-relocation-progress")
        relocation_busy = False

        def on_confirmation_change(_: ft.ControlEvent) -> None:
            if relocation_busy:
                return
            relocate_button.disabled = not bool(confirmation.value)
            page.update()

        def on_relocate(_: ft.ControlEvent) -> None:
            nonlocal relocation_busy
            if (
                generation != preview_generation
                or relocation_busy
                or not confirmation.value
            ):
                return
            raw_destination = (destination_field.value or "").strip()
            if not raw_destination:
                show_action_error("请输入 Home 内尚不存在的目标路径。")
                return

            relocation_busy = True
            relocate_button.disabled = True
            confirmation.disabled = True
            destination_field.disabled = True
            path_field.disabled = True
            inspect_button.disabled = True
            directory_button.disabled = True
            progress_text.value = "正在只读复查来源并复制验证，请勿重复操作…"
            error_text.value = ""
            page.update()

            copied: Path | None = None
            switched = False
            try:
                current_kind = _classify_vault_source_no_follow(source)
                if current_kind != source_kind:
                    raise ValueError(
                        f"来源格式已从 {source_kind} 变为 {current_kind}；请重新检查"
                    )
                destination = Path(raw_destination).expanduser().absolute()
                copied = copy_vault_no_follow(source, destination)
                copied = require_home_path(copied)
                validate_vault_tree_no_follow(copied)
                copied_kind = _classify_vault_source_no_follow(copied)
                if copied_kind != source_kind:
                    raise ValueError(
                        f"复制结果格式与已确认来源不符：{source_kind} -> {copied_kind}"
                    )
                if source_kind == _SOURCE_V01:
                    selection = _validated_v01_selection(copied)
                    set_vault(copied, CONFIG_PATH, selection)
                    switched = True
                    _build_migration_gate(
                        page,
                        copied,
                        configured=True,
                        expected_root_identity=selection.root_identity,
                    )
                    return
                selection = _validated_rebuild(copied)
                set_vault(copied, CONFIG_PATH, selection)
            except (OSError, ValueError) as ex:
                relocation_busy = False
                confirmation.disabled = False
                destination_field.disabled = False
                path_field.disabled = False
                inspect_button.disabled = False
                directory_button.disabled = False
                relocate_button.disabled = not bool(confirmation.value)
                progress_text.value = ""
                retained = f"；安全副本保留在 {copied}" if copied is not None else ""
                config_state = (
                    "；安全副本仍是当前 Vault"
                    if switched
                    else "；当前配置未修改"
                )
                show_action_error(
                    f"无法搬迁 Vault：{ex}；原路径未修改{config_state}{retained}。"
                )
                return
            notify(page, "Vault 已复制、验证并切换；原路径保持不变")
            _build_startup(
                page,
                copied,
                expected_root_identity=selection.root_identity,
            )

        confirmation.on_change = on_confirmation_change
        relocate_button.on_click = on_relocate
        show_preview(
            [
                ft.Text("此路径不在允许写入的 Home 边界内。", color=ft.Colors.ERROR),
                ft.Text(f"来源：{source}", selectable=True),
                ft.Text(f"原因：{reason}", color=MUTED, selectable=True),
                ft.Text(f"只读识别：{source_kind} Vault", color=MUTED),
                ft.Text("必须复制到当前用户 Home 内的全新位置，验证完成后才会切换。", color=MUTED),
                destination_field,
                confirmation,
                relocate_button,
                progress_text,
            ],
            generation,
        )

    def inspect_vault(raw: str) -> None:
        generation = invalidate_preview()
        raw = raw.strip()
        if not raw:
            show_error("请输入文件夹路径。")
            return
        vault = Path(raw).expanduser().absolute()
        if not os.path.lexists(vault):
            try:
                safe_vault = require_home_path(vault)
            except (OSError, ValueError) as ex:
                show_error(f"无法检查 Vault：{ex}")
                return
            show_preview(
                [
                    ft.Text("此位置为空或尚不存在。", color=FG),
                    ft.Text(f"路径：{safe_vault}", selectable=True),
                    ft.Text("确认后将创建 Paper Vault 结构。", color=MUTED),
                    primary_button(
                        "确认初始化并打开",
                        lambda _e: initialize_vault(vault, generation),
                    ),
                ],
                generation,
            )
            return
        try:
            safe_vault = require_home_path(vault)
        except (OSError, ValueError) as ex:
            try:
                source_kind = _classify_vault_source_no_follow(vault)
            except (OSError, ValueError) as source_ex:
                show_error(f"无法搬迁此来源：{source_ex}；未复制、未切换 Vault。")
                return
            show_relocation(vault, str(ex), source_kind, generation)
            return
        try:
            validate_vault_tree_no_follow(vault)
            if safe_vault.is_dir() and not any(safe_vault.iterdir()):
                show_preview(
                    [
                        ft.Text("此位置为空或尚不存在。", color=FG),
                        ft.Text(f"路径：{safe_vault}", selectable=True),
                        ft.Text("确认后将创建 Paper Vault 结构。", color=MUTED),
                        primary_button(
                            "确认初始化并打开",
                            lambda _e: initialize_vault(vault, generation),
                        ),
                    ],
                    generation,
                )
                return
            source_kind = _classify_vault_source_no_follow(safe_vault)
            if source_kind == _SOURCE_V01:
                _build_migration_gate(page, safe_vault, on_cancel=on_cancel)
            else:
                paper_count = len(list_active_papers(safe_vault))
                show_preview(
                    [
                        ft.Text("检测到可用 Vault。", color=FG),
                        ft.Text(f"路径：{safe_vault}", selectable=True),
                        ft.Text(f"Paper 数量：{paper_count}"),
                        primary_button(
                            "确认切换并打开",
                            lambda _e: open_safe_vault(safe_vault, generation),
                        ),
                    ],
                    generation,
                )
        except (OSError, ValueError) as ex:
            show_error(f"无法检查 Vault：{ex}")

    def on_open(_: ft.ControlEvent) -> None:
        inspect_vault(path_field.value or "")

    def on_path_change(_: ft.ControlEvent) -> None:
        invalidate_preview()
        error_text.value = ""
        page.update()

    async def on_choose_directory(_: ft.ControlEvent) -> None:
        try:
            selected = await directory_picker.get_directory_path(
                dialog_title="选择 Vault 文件夹",
                initial_directory=str(existing or Path.home()),
            )
        except (OSError, ValueError) as ex:
            show_error(f"系统目录选择器不可用：{ex}；可改为手工输入路径。")
            return
        if selected is None:
            show_error("未选择文件夹；可继续手工输入完整路径。")
            return
        path_field.value = selected
        inspect_vault(selected)

    path_field.on_change = on_path_change
    directory_button = ft.OutlinedButton(
        content=ft.Text("从系统选择文件夹"),
        on_click=on_choose_directory,
        key="vault-directory-chooser",
    )
    inspect_button = primary_button("检查 Vault", on_open)

    picker_controls: list[ft.Control] = [
        ft.Text("打开或创建 Vault", size=28, color=FG, font_family=FONT_DISPLAY, weight=ft.FontWeight.W_400),
        ft.Text("Vault 保存你的 Paper Markdown；索引可随时从 Paper 重建。", color=MUTED),
        ft.Text(
            "保护边界：仅允许当前用户 Home 内路径；尚未启用 Apple App Sandbox。",
            color=MUTED,
        ),
        directory_button,
        ft.Text("系统选择器不可用或取消时，可手工输入完整路径。", color=MUTED),
        path_field,
        inspect_button,
        preview,
        error_text,
    ]
    if on_cancel is not None:
        picker_controls.append(
            ft.OutlinedButton(content=ft.Text("取消"), on_click=lambda _e: on_cancel())
        )

    page.add(
        ft.Container(
            padding=SPACE_8,
            bgcolor=BG,
            expand=True,
            content=paper_card(
                controls=picker_controls,
                key="vault-picker-paper-card",
                spacing=SPACE_4,
            ),
        )
    )
    if unsafe_source is not None:
        generation = invalidate_preview()
        show_relocation(
            unsafe_source,
            unsafe_reason or "路径未通过 Home 安全检查",
            unsafe_source_kind,
            generation,
        )
    elif initial_error:
        show_error(initial_error)


def main(page: ft.Page) -> None:
    """Flet view builder: show the selected Paper Vault or the local picker."""
    page.title = "keikeu"
    _configure_window(page)
    apply_theme(page)
    vault = get_vault(CONFIG_PATH)
    if vault is None:
        _build_vault_picker(page)
        return
    raw_vault = vault.expanduser().absolute()
    if not os.path.lexists(raw_vault):
        _build_vault_picker(
            page,
            initial_path=raw_vault,
            initial_error="当前配置的 Vault 不存在；请选择现有 Vault 或新位置。",
        )
        return
    try:
        safe_vault, root_identity = _pin_home_vault_root(raw_vault)
    except (OSError, ValueError) as ex:
        try:
            source_kind = _classify_vault_source_no_follow(raw_vault)
        except (OSError, ValueError) as source_ex:
            _build_vault_picker(
                page,
                show_configured=False,
                initial_path=raw_vault,
                initial_error=(
                    f"当前 Vault 无法安全搬迁：{source_ex}；未复制、未更改配置。"
                ),
            )
            return
        _build_vault_picker(
            page,
            show_configured=False,
            initial_path=raw_vault,
            unsafe_source=raw_vault,
            unsafe_source_kind=source_kind,
            unsafe_reason=str(ex),
        )
        return
    try:
        source_kind = _classify_configured_home_vault(safe_vault)
    except (OSError, ValueError) as ex:
        _build_vault_picker(
            page,
            initial_path=raw_vault,
            initial_error=f"当前 Vault 无法安全打开：{ex}",
        )
        return
    if source_kind == _SOURCE_V01:
        try:
            _build_migration_gate(
                page,
                safe_vault,
                configured=True,
                expected_root_identity=root_identity,
            )
        except (OSError, ValueError) as ex:
            _build_vault_picker(
                page,
                initial_path=raw_vault,
                initial_error=f"当前 Vault 在打开迁移页前发生变化：{ex}",
            )
    else:
        try:
            _build_startup(
                page,
                safe_vault,
                expected_root_identity=root_identity,
            )
        except (OSError, ValueError) as ex:
            _build_vault_picker(
                page,
                initial_path=raw_vault,
                initial_error=f"当前 Vault 在打开前发生变化：{ex}",
            )


def run() -> None:
    """No-argument console entry point."""
    ft.run(main)


if __name__ == "__main__":
    run()
