"""Headless UI contracts for explicit v0.1 migration confirmation."""

from __future__ import annotations

import asyncio
from pathlib import Path
import shutil
from types import SimpleNamespace
from typing import Iterable

import flet as ft

from keikeu_app import main as app_main
from keikeu_app.pages.migration_page import build_migration_page
from keikeu_core.migration_v01 import MigrationResult
from keikeu_core.vault import is_vault


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "v01-vault"


class FakePage:
    def __init__(self, platform: ft.PagePlatform = ft.PagePlatform.MACOS) -> None:
        self.controls: list[object] = []
        self.overlay: list[object] = []
        self.services: list[object] = []
        self.platform = platform
        self.theme: ft.Theme | None = None
        self.bgcolor: str | None = None
        self.scroll = ft.ScrollMode.AUTO
        self.title = ""
        self.window = SimpleNamespace(width=None, height=None)
        self.update_count = 0

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
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def _by_key(root: object, key: str) -> object:
    for control in _walk(root):
        if getattr(control, "key", None) == key:
            return control
    raise AssertionError(f"Control not found: {key}")


def _button(root: object, text: str) -> object:
    for control in _walk(root):
        if getattr(getattr(control, "content", None), "value", None) == text:
            return control
    raise AssertionError(f"Button not found: {text}")


def _text_field(root: object, label: str) -> ft.TextField:
    for control in _walk(root):
        if isinstance(control, ft.TextField) and control.label == label:
            return control
    raise AssertionError(f"Text field not found: {label}")


def _texts(root: object) -> list[str]:
    return [
        control.value
        for control in _walk(root)
        if isinstance(control, ft.Text) and isinstance(control.value, str)
    ]


def _copy_fixture(tmp_path: Path) -> Path:
    vault = tmp_path / "legacy-vault"
    shutil.copytree(FIXTURE_VAULT, vault)
    return vault


def _remove_preflight_failures(vault: Path) -> None:
    (vault / "cache" / "2026-07-03-090000-a103-empty-raw.md").unlink()
    (vault / "cache" / "2026-07-04-090000-a104-corrupt-status.md").unlink()


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_startup_detects_v01_before_any_v2_write(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    before = _file_bytes(vault)
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: vault)
    monkeypatch.setattr(
        app_main,
        "init_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not initialize v0.1")),
    )
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not index v0.1")),
    )

    app_main.main(page)  # type: ignore[arg-type]

    assert _by_key(page.controls[0], "migration-preflight-card")
    assert _file_bytes(vault) == before


def test_ios_vault_picker_creates_a_sandbox_vault(tmp_path, monkeypatch):
    page = FakePage(platform=ft.PagePlatform.IOS)
    opened: list[Path] = []
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(app_main, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(app_main.Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(app_main, "_build_shell", lambda _page, vault: opened.append(vault))

    app_main.main(page)  # type: ignore[arg-type]

    assert page.window.width is None
    assert page.window.height is None
    assert _by_key(page.controls[0], "vault-picker-paper-card")
    assert page.controls[0].expand is False
    assert page.services == []
    assert any("iOS 不允许 keikeu 直接打开“文件”App 选择的文件夹。" in text for text in _texts(page.controls[0]))

    _button(page.controls[0], "创建本机 Vault").on_click(None)

    vault = tmp_path / "keikeu-vault"
    assert is_vault(vault)
    assert opened == [vault]


def test_preflight_lists_blockers_and_cancel_keeps_legacy_vault_unchanged(tmp_path):
    vault = _copy_fixture(tmp_path)
    before = _file_bytes(vault)
    chosen: list[bool] = []
    root = build_migration_page(
        FakePage(),  # type: ignore[arg-type]
        vault,
        on_open_migrated=lambda _result: None,
        on_choose_other=lambda: chosen.append(True),
    )

    assert any("迁移被以下项目阻止" in text for text in _texts(root))
    assert _button(root, "创建完整备份并迁移").visible is False
    _button(root, "选择其他文件夹").on_click(None)
    assert chosen == [True]
    assert _file_bytes(vault) == before


def test_picker_routes_a_manually_selected_v01_vault_without_writing_it(tmp_path, monkeypatch):
    vault = _copy_fixture(tmp_path)
    before = _file_bytes(vault)
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(
        app_main,
        "init_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not initialize v0.1")),
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config: (_ for _ in ()).throw(AssertionError("must not configure v0.1")),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "创建 / 打开 Vault").on_click(None)

    assert _by_key(page.controls[0], "migration-preflight-card")
    assert _file_bytes(vault) == before


def test_system_directory_chooser_opens_a_v2_vault_with_path_fallback(tmp_path, monkeypatch):
    vault = tmp_path / "selected-vault"
    page = FakePage()
    configured: list[tuple[Path, Path]] = []
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(app_main, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda selected, config: configured.append((selected, config)),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    picker = next(
        service
        for service in page.services
        if getattr(service, "key", None) == "vault-directory-picker"
    )
    async def choose_directory(**_kwargs: object) -> str:
        return str(vault)

    monkeypatch.setattr(picker, "get_directory_path", choose_directory)

    asyncio.run(_button(root, "从系统选择文件夹").on_click(None))

    assert is_vault(vault)
    assert configured == [(vault, app_main.CONFIG_PATH)]
    assert "系统选择器不可用或取消时，可手工输入完整路径。" in _texts(root)


def test_system_directory_chooser_cancel_keeps_path_fallback_visible(tmp_path, monkeypatch):
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    picker = next(
        service
        for service in page.services
        if getattr(service, "key", None) == "vault-directory-picker"
    )
    async def cancel_directory(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(picker, "get_directory_path", cancel_directory)

    asyncio.run(_button(root, "从系统选择文件夹").on_click(None))

    assert _text_field(root, "Vault 文件夹路径")
    assert "未选择文件夹；可继续手工输入完整路径。" in _texts(root)


def test_confirmed_fixture_migration_displays_backup_report_and_open_action(tmp_path):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    before = _file_bytes(vault)
    completed: list[MigrationResult] = []
    page = FakePage()
    root = build_migration_page(
        page,  # type: ignore[arg-type]
        vault,
        on_open_migrated=lambda result: completed.append(result),
        on_choose_other=lambda: None,
    )

    confirmation = _by_key(root, "migration-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    migrate_button = _button(root, "创建完整备份并迁移")
    assert migrate_button.disabled is False
    migrate_button.on_click(None)

    assert not (vault / "outlines").exists()
    assert not (vault / ".trash" / "outlines").exists()
    assert completed == []
    assert any("迁移已完成" in text for text in _texts(root))
    _button(root, "打开已迁移的 Vault").on_click(None)

    assert len(completed) == 1
    result = completed[0]
    assert _file_bytes(result.backup_path) == before
    assert result.report_path.exists()
