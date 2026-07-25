"""keikeu Flet shell for the current macOS Paper flow.

The GUI routes user actions through ``KeikeuService``. Markdown, JSON,
migration, and asset recovery remain behind that local boundary.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import flet as ft

from keikeu_app.local_state import STATE_PATH as DEVICE_STATE_PATH
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
from keikeu_bridge import (
    KeikeuService,
    MigrationPreflightDto,
    ServiceError,
    StartupDto,
    VaultPreviewDto,
)

__all__ = ["main", "run", "AppContext", "CONFIG_PATH"]

CONFIG_PATH = Path.home() / ".keikeu_config.json"
INITIAL_WINDOW_WIDTH = 890
INITIAL_WINDOW_HEIGHT = 741

_NAV_PAPER = 0
_NAV_FLASHCARD = 1
_NAV_LIBRARY = 2

@dataclass
class AppContext:
    """The active vault and page-navigation callbacks shared by GUI builders."""

    page: ft.Page
    vault: Path
    service: KeikeuService
    library_scope_host: ft.Column | None = None
    open_paper: Callable[[Path | None], None] = field(default=lambda _path: None)
    open_flashcards: Callable[[Path | None], None] = field(default=lambda _path: None)
    open_library: Callable[[], None] = field(default=lambda: None)
    change_vault: Callable[[], None] = field(default=lambda: None)


def _configure_window(page: ft.Page) -> None:
    page.window.width = INITIAL_WINDOW_WIDTH
    page.window.height = INITIAL_WINDOW_HEIGHT


def _new_service(*, state_path: Path | None = None) -> KeikeuService:
    return KeikeuService(
        config_path=CONFIG_PATH,
        state_path=DEVICE_STATE_PATH if state_path is None else state_path,
    )


def _build_shell(
    page: ft.Page,
    vault: Path,
    *,
    expected_root_identity: tuple[int, int] | None = None,
    service: KeikeuService | None = None,
) -> None:
    """Build the Paper / Flashcard / Library navigation shell."""
    service = _new_service() if service is None else service
    service.activate_existing_vault(
        vault,
        expected_root_identity=expected_root_identity,
    )
    active_vault = service.active_vault
    if active_vault is None:
        raise ServiceError("operation_failed", "Vault activation failed", "choose_vault")
    vault = active_vault
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
        service=service,
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
            new_content = build_paper_page(ctx, open_path)
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
            new_content = build_flashcard_page(ctx, open_path)
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
        service=service,
        initial_path=vault,
        on_cancel=lambda: _build_shell(
            page,
            vault,
            service=service,
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
    service: KeikeuService | None = None,
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
            service=service,
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
    service = _new_service(state_path=state_path)
    startup = service.activate_existing_vault(
        vault,
        expected_root_identity=expected_root_identity,
        claim_daily=True,
    )
    active_vault = service.active_vault
    if active_vault is None:
        raise ServiceError("operation_failed", "Vault activation failed", "choose_vault")
    if startup.show_daily_card:
        _build_daily_start(
            page,
            active_vault,
            service=service,
        )
        return
    _build_shell(
        page,
        active_vault,
        service=service,
    )


def _build_migration_gate(
    page: ft.Page,
    vault_or_service: Path | KeikeuService,
    *,
    configured: bool = False,
    on_cancel: Callable[[], None] | None = None,
    expected_root_identity: tuple[int, int] | None = None,
    preflight: MigrationPreflightDto | None = None,
) -> None:
    """Show a no-write v0.1 preflight before allowing Paper Vault actions."""
    if isinstance(vault_or_service, KeikeuService):
        service = vault_or_service
        vault = service.active_vault
        if preflight is None:
            preflight = service.migration_preflight()
    else:
        vault = vault_or_service
        service = _new_service()
        inspected = service.vault_inspect(str(vault))
        preflight = inspected.migration
    if preflight is None:
        raise ServiceError(
            "preflight_blocked",
            "migration preflight is unavailable",
            "inspect",
        )
    apply_theme(page)
    page.controls.clear()
    page.scroll = None

    def open_migrated(_: object) -> None:
        try:
            active_vault = service.active_vault
            if active_vault is None:
                raise ServiceError(
                    "operation_failed",
                    "migrated Vault was not activated",
                    "choose_vault",
                )
            startup = service.activate_existing_vault(
                active_vault,
                claim_daily=True,
                require_clean_papers=True,
            )
            if startup.show_daily_card:
                _build_daily_start(page, active_vault, service=service)
            else:
                _build_shell(page, active_vault, service=service)
        except ServiceError as ex:
            notify(page, f"无法打开已迁移的 Vault：{ex.message}；请检查路径后重试。")

    def choose_other() -> None:
        _build_vault_picker(
            page,
            service=service,
            initial_path=vault if configured and vault is not None else None,
            on_cancel=on_cancel,
        )

    page.add(
        ft.Container(
            expand=True,
            padding=SPACE_8,
            bgcolor=BG,
            content=build_migration_page(
                page,
                service,
                preflight,
                on_open_migrated=open_migrated,
                on_choose_other=choose_other,
            ),
        )
    )


def _build_vault_picker(
    page: ft.Page,
    *,
    service: KeikeuService | None = None,
    show_configured: bool = True,
    initial_path: Path | None = None,
    on_cancel: Callable[[], None] | None = None,
    initial_preview: VaultPreviewDto | None = None,
    unsafe_source: Path | None = None,
    unsafe_source_kind: str = "",
    unsafe_reason: str = "",
    initial_error: str = "",
) -> None:
    """Classify a candidate read-only, then require confirmation before writes."""
    service = _new_service() if service is None else service
    apply_theme(page)
    page.controls.clear()
    page.scroll = ft.ScrollMode.AUTO
    existing = initial_path
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

    def enter_startup(startup: StartupDto) -> None:
        active_vault = service.active_vault
        if startup.state == "migration" and startup.migration is not None:
            _build_migration_gate(
                page,
                service,
                configured=True,
                preflight=startup.migration,
            )
            return
        if active_vault is None:
            show_error("Vault 已处理，但没有可用的活动路径。")
            return
        if startup.show_daily_card:
            _build_daily_start(page, active_vault, service=service)
        else:
            _build_shell(page, active_vault, service=service)

    def open_safe_vault(candidate: VaultPreviewDto, generation: int) -> None:
        if generation != preview_generation:
            return
        try:
            startup = service.vault_open(candidate.token)
        except ServiceError as ex:
            show_error(f"无法打开 Vault：{ex.message}；当前 Vault 未切换。")
            return
        notify(page, "Vault 已切换")
        enter_startup(startup)

    def initialize_vault(candidate: VaultPreviewDto, generation: int) -> None:
        if generation != preview_generation:
            return
        try:
            startup = service.vault_initialize(candidate.token)
        except ServiceError as ex:
            show_error(f"无法初始化 Vault：{ex.message}；当前 Vault 未切换。")
            return
        notify(page, "Vault 已创建")
        enter_startup(startup)

    def show_relocation(
        candidate: VaultPreviewDto,
        generation: int,
    ) -> None:
        destination_field = single_line_field("Home 内全新目标路径")
        source = Path(candidate.display_path)
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

            try:
                startup = service.vault_relocate(
                    candidate.token,
                    raw_destination,
                )
            except ServiceError as ex:
                relocation_busy = False
                confirmation.disabled = False
                destination_field.disabled = False
                path_field.disabled = False
                inspect_button.disabled = False
                directory_button.disabled = False
                relocate_button.disabled = not bool(confirmation.value)
                progress_text.value = ""
                show_action_error(
                    f"无法搬迁 Vault：{ex.message}；原路径未修改。"
                )
                return
            notify(page, "Vault 已复制、验证并切换；原路径保持不变")
            enter_startup(startup)

        confirmation.on_change = on_confirmation_change
        relocate_button.on_click = on_relocate
        show_preview(
            [
                ft.Text("此路径不在允许写入的 Home 边界内。", color=ft.Colors.ERROR),
                ft.Text(f"来源：{source}", selectable=True),
                ft.Text(f"原因：{candidate.message}", color=MUTED, selectable=True),
                ft.Text(f"只读识别：{candidate.source_kind} Vault", color=MUTED),
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
        try:
            candidate = service.vault_inspect(raw)
        except ServiceError as ex:
            show_error(f"无法检查 Vault：{ex.message}")
            return
        if candidate.kind == "create":
            show_preview(
                [
                    ft.Text("此位置为空或尚不存在。", color=FG),
                    ft.Text(f"路径：{candidate.display_path}", selectable=True),
                    ft.Text("确认后将创建 Paper Vault 结构。", color=MUTED),
                    primary_button(
                        "确认初始化并打开",
                        lambda _e: initialize_vault(candidate, generation),
                    ),
                ],
                generation,
            )
            return
        if candidate.kind == "relocate":
            show_relocation(candidate, generation)
            return
        if candidate.kind == "migration" and candidate.migration is not None:
            _build_migration_gate(
                page,
                service,
                on_cancel=on_cancel,
                preflight=candidate.migration,
            )
            return
        if candidate.kind == "paper":
            show_preview(
                [
                    ft.Text("检测到可用 Vault。", color=FG),
                    ft.Text(f"路径：{candidate.display_path}", selectable=True),
                    ft.Text(f"Paper 数量：{candidate.paper_count}"),
                    primary_button(
                        "确认切换并打开",
                        lambda _e: open_safe_vault(candidate, generation),
                    ),
                ],
                generation,
            )
            return
        show_error("无法识别此 Vault。")

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
    if initial_preview is not None:
        path_field.value = initial_preview.display_path
        inspect_vault(initial_preview.display_path)
    elif unsafe_source is not None:
        path_field.value = str(unsafe_source)
        inspect_vault(str(unsafe_source))
    elif initial_error:
        show_error(initial_error)


def main(page: ft.Page) -> None:
    """Flet view builder: show the selected Paper Vault or the local picker."""
    page.title = "keikeu"
    _configure_window(page)
    apply_theme(page)
    service = _new_service()
    try:
        startup = service.startup_load()
    except ServiceError as ex:
        _build_vault_picker(
            page,
            service=service,
            initial_error=f"当前 Vault 无法安全打开：{ex.message}",
        )
        return
    if startup.state == "migration" and startup.migration is not None:
        _build_migration_gate(
            page,
            service,
            configured=True,
            preflight=startup.migration,
        )
        return
    if startup.state == "ready" and service.active_vault is not None:
        try:
            if startup.show_daily_card:
                _build_daily_start(
                    page,
                    service.active_vault,
                    service=service,
                )
            else:
                _build_shell(
                    page,
                    service.active_vault,
                    service=service,
                )
        except ServiceError as ex:
            _build_vault_picker(
                page,
                service=service,
                initial_error=f"当前 Vault 无法安全打开：{ex.message}",
            )
        return
    _build_vault_picker(
        page,
        service=service,
        initial_path=(
            Path(startup.configured_path)
            if startup.configured_path
            else None
        ),
        initial_preview=startup.preview,
        initial_error=startup.message,
    )


def run() -> None:
    """No-argument console entry point."""
    ft.run(main)


if __name__ == "__main__":
    run()
