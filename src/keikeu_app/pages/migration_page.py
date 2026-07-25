"""Explicit v0.1 migration preflight and confirmation UI.

The page performs no vault write while it displays preflight information.  The
only destructive transition is the clearly labelled confirmation action, which
delegates the atomic migration to the pure-Python core module.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from keikeu_app.theme import DANGER, FG, FONT_DISPLAY, MUTED, SPACE_3, SPACE_4, SPACE_6, SUCCESS, SURFACE_WARM
from keikeu_app.widgets import page_header, paper_card, primary_button
from keikeu_bridge import (
    KeikeuService,
    MigrationPreflightDto,
    MigrationResultDto,
    ServiceError,
)

__all__ = ["build_migration_page"]


def _preflight_lines(preflight: MigrationPreflightDto) -> list[ft.Control]:
    lines: list[ft.Control] = [
        ft.Text(f"活动 Cache：{preflight.cache_count}", color=FG),
        ft.Text(f"回收站 Cache：{preflight.trash_cache_count}", color=FG),
        ft.Text(
            f"活动 Outline：{preflight.outline_count}（成功后永久移除）",
            color=DANGER,
        ),
        ft.Text(
            f"回收站 Outline：{preflight.trash_outline_count}（成功后永久移除）",
            color=DANGER,
        ),
    ]
    if preflight.issues:
        lines.append(ft.Text("迁移被以下项目阻止：", color=DANGER, weight=ft.FontWeight.W_600))
        lines.extend(
            ft.Text(
                f"• {issue.path}：{issue.message}",
                color=DANGER,
                selectable=True,
            )
            for issue in preflight.issues
        )
    else:
        lines.append(ft.Text("预检通过：可以创建备份并执行迁移。", color=SUCCESS))
    return lines


def build_migration_page(
    page: ft.Page,
    service: KeikeuService,
    preflight: MigrationPreflightDto,
    *,
    on_open_migrated: Callable[[MigrationResultDto], None],
    on_choose_other: Callable[[], None],
) -> ft.Control:
    """Build a no-write preflight page for one detected v0.1 vault."""
    status = ft.Text("", color=DANGER, selectable=True)
    result_details = ft.Column(controls=[], visible=False, spacing=SPACE_3)
    confirmation = ft.Checkbox(
        label="我已了解：将先创建完整备份，再永久移除活动与回收站中的旧 Outline。",
        key="migration-confirm",
        visible=preflight.ready,
    )
    migrate_button = primary_button("创建完整备份并迁移", lambda _e: None)
    migrate_button.key = "migration-run"
    migrate_button.disabled = True
    migrate_button.visible = preflight.ready
    choose_button = ft.OutlinedButton(
        content=ft.Text("选择其他文件夹"), on_click=lambda _e: on_choose_other()
    )

    def on_confirmation_change(_: ft.ControlEvent) -> None:
        migrate_button.disabled = not bool(confirmation.value)
        page.update()

    def on_migrate(_: ft.ControlEvent) -> None:
        if not confirmation.value:
            return
        confirmation.disabled = True
        migrate_button.disabled = True
        status.value = "正在创建完整备份并迁移；请勿关闭应用。"
        status.color = MUTED
        page.update()
        try:
            result = service.migration_run(preflight.token)
        except ServiceError as exc:
            confirmation.disabled = False
            migrate_button.disabled = False
            prefix = "迁移未执行" if exc.code == "preflight_blocked" else "迁移失败"
            status.value = f"{prefix}：{exc.message}；原 vault 保持可恢复状态。"
            status.color = DANGER
            page.update()
            return

        confirmation.visible = False
        migrate_button.visible = False
        status.value = "迁移已完成。请核对备份和报告路径后再打开新的 Paper vault。"
        status.color = SUCCESS
        result_details.controls[:] = [
            ft.Text(f"已转换 Paper：{result.converted_count}", color=FG),
            ft.Text(f"完整备份：{result.backup_path}", selectable=True),
            ft.Text(f"迁移报告：{result.report_path}", selectable=True),
            primary_button("打开已迁移的 Vault", lambda _e: on_open_migrated(result)),
        ]
        result_details.visible = True
        page.update()

    confirmation.on_change = on_confirmation_change
    migrate_button.on_click = on_migrate
    return ft.Column(
        controls=[
            page_header(
                "需要迁移旧 Vault",
                "检测到 v0.1 Cache / Outline 数据；不会在后台静默升级。",
                "MIGRATION · CONFIRM FIRST",
            ),
            paper_card(
                [
                    ft.Text("迁移前检查", size=22, color=FG, font_family=FONT_DISPLAY),
                    ft.Text("Vault：已验证的本地迁移来源", color=MUTED),
                    ft.Text(f"完整备份将写入：{preflight.backup_path}", color=MUTED, selectable=True),
                    ft.Container(
                        content=ft.Column(controls=_preflight_lines(preflight), spacing=SPACE_3),
                        bgcolor=SURFACE_WARM,
                        padding=SPACE_4,
                    ),
                    ft.Text(
                        "迁移只重写可预检通过的 Cache 为 Paper；旧 Outline 不解析、不转换，"
                        "只会在成功后从活动 vault 永久移除。",
                        color=MUTED,
                    ),
                    confirmation,
                    migrate_button,
                    status,
                    result_details,
                    choose_button,
                ],
                key="migration-preflight-card",
                spacing=SPACE_4,
            ),
        ],
        spacing=SPACE_6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
