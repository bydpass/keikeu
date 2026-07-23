"""Headless UI contracts for explicit v0.1 migration confirmation."""

from __future__ import annotations

import asyncio
from pathlib import Path
import shutil
from types import SimpleNamespace
from typing import Iterable

import flet as ft

from keikeu_app import main as app_main
from keikeu_app.pages import migration_page as migration_page_mod
from keikeu_app.pages.migration_page import build_migration_page
from keikeu_core.markdown_io import write_paper
from keikeu_core.migration_v01 import MigrationResult, is_v01_vault
from keikeu_core.models import Highlight, Paper
from keikeu_core.vault import (
    capture_vault_selection_token,
    get_vault,
    init_vault,
    is_vault,
    set_vault,
    vault_index_version,
)


FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "v01-vault"


class FakePage:
    def __init__(self) -> None:
        self.controls: list[object] = []
        self.overlay: list[object] = []
        self.services: list[object] = []
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
        lambda _vault, _config, _selection: (_ for _ in ()).throw(AssertionError("must not configure v0.1")),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)

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
        lambda selected, config, _selection: configured.append((selected, config)),
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

    assert not vault.exists()
    assert configured == []
    assert "此位置为空或尚不存在。" in _texts(root)
    _button(root, "确认初始化并打开").on_click(None)

    assert is_vault(vault)
    assert configured == [(vault.resolve(), app_main.CONFIG_PATH)]
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


def test_valid_vault_preview_is_read_only_until_confirmed(tmp_path, monkeypatch):
    vault = tmp_path / "existing-vault"
    init_vault(vault)
    (vault / "cache" / "Folder").mkdir()
    write_paper(
        vault,
        Paper(
            code="K-20260722-001",
            initial_summary="",
            summary="folder-aware preview",
        ),
        destination="cache/Folder/K-20260722-001.md",
    )
    page = FakePage()
    order: list[str] = []
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: order.append("rebuild") or {"papers": [], "errors": []},
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: order.append("set"),
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: order.append("shell"),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)

    assert order == []
    assert "Paper 数量：1" in _texts(root)
    _button(root, "确认切换并打开").on_click(None)
    assert order == ["rebuild", "set", "shell"]


def test_confirmed_v2_rejects_ordinary_root_replacement_after_final_validation(
    tmp_path,
    monkeypatch,
):
    vault = tmp_path / "validated-vault"
    parked = tmp_path / "parked-vault"
    config = tmp_path / "config.json"
    init_vault(vault)
    config_bytes = b'{"vault": "old"}\n'
    config.write_bytes(config_bytes)
    page = FakePage()
    real_set = app_main.set_vault
    shell_calls: list[Path] = []

    def replace_root_then_set(selected, config_path, selection) -> None:
        vault.rename(parked)
        vault.mkdir()
        (vault / "ordinary.txt").write_bytes(b"ordinary replacement")
        real_set(selected, config_path, selection)

    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(app_main, "set_vault", replace_root_then_set)
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, selected, **_kwargs: shell_calls.append(selected),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    _button(root, "确认切换并打开").on_click(None)

    assert shell_calls == []
    assert config.read_bytes() == config_bytes
    assert is_vault(parked)
    assert (vault / "ordinary.txt").read_bytes() == b"ordinary replacement"
    assert list(tmp_path.glob(f".{config.name}.*.tmp")) == []
    assert any("validated selection" in text for text in _texts(root))


def test_path_change_invalidates_the_visible_preview_and_its_old_confirmation(
    tmp_path, monkeypatch
):
    vault = tmp_path / "existing-vault"
    init_vault(vault)
    page = FakePage()
    order: list[str] = []
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: order.append("rebuild") or {"papers": [], "errors": []},
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: order.append("set"),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    path_field = _text_field(root, "Vault 文件夹路径")
    path_field.value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    preview = _by_key(root, "vault-preview")
    old_confirmation = _button(root, "确认切换并打开")

    path_field.value = str(tmp_path / "different-vault")
    path_field.on_change(None)
    old_confirmation.on_click(None)

    assert preview.visible is False
    assert preview.controls == []
    assert order == []


def test_empty_vault_preview_does_not_initialize_before_confirm(tmp_path, monkeypatch):
    vault = tmp_path / "new-vault"
    page = FakePage()
    order: list[str] = []
    real_init = app_main.init_vault
    real_rebuild = app_main.rebuild_index
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)

    def tracked_init(path: Path) -> None:
        order.append("init")
        real_init(path)

    def tracked_rebuild(path: Path) -> dict[str, object]:
        order.append("rebuild")
        return real_rebuild(path)

    monkeypatch.setattr(app_main, "init_vault", tracked_init)
    monkeypatch.setattr(app_main, "rebuild_index", tracked_rebuild)
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: order.append("set"),
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: order.append("shell"),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)

    assert not vault.exists()
    assert order == []
    _button(root, "确认初始化并打开").on_click(None)
    assert is_vault(vault)
    assert order == ["init", "rebuild", "set", "shell"]


def test_empty_preview_blocks_if_the_directory_becomes_nonempty_before_confirm(
    tmp_path, monkeypatch
):
    vault = tmp_path / "changed-empty-vault"
    vault.mkdir()
    page = FakePage()
    monkeypatch.setattr(
        app_main,
        "init_vault",
        lambda _vault: (_ for _ in ()).throw(
            AssertionError("changed candidate must not be initialized")
        ),
    )
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: (_ for _ in ()).throw(
            AssertionError("changed candidate must not be rebuilt")
        ),
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(
            AssertionError("changed candidate must not be configured")
        ),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    note = vault / "appeared-after-preview.txt"
    note.write_text("keep", encoding="utf-8")

    _button(root, "确认初始化并打开").on_click(None)

    assert note.read_text(encoding="utf-8") == "keep"
    assert any("目标已不再为空" in text for text in _texts(root))


def test_missing_preview_rejects_a_root_symlink_created_before_confirm(
    tmp_path, monkeypatch
):
    candidate = tmp_path / "new-vault"
    target = tmp_path / "symlink-target"
    page = FakePage()
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(
            AssertionError("symlink candidate must not be configured")
        ),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(candidate)
    _button(root, "检查 Vault").on_click(None)
    target.mkdir()
    candidate.symlink_to(target, target_is_directory=True)

    _button(root, "确认初始化并打开").on_click(None)

    assert candidate.is_symlink()
    assert list(target.iterdir()) == []
    assert any("symlink" in text for text in _texts(root))


def test_valid_v2_preview_reclassifies_before_rebuild_or_switch(tmp_path, monkeypatch):
    vault = tmp_path / "changed-vault"
    init_vault(vault)
    page = FakePage()
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: (_ for _ in ()).throw(
            AssertionError("changed candidate must not be rebuilt")
        ),
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(
            AssertionError("changed candidate must not be configured")
        ),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    (vault / "keikeu_index.json").unlink()
    (vault / ".trash" / "cache").rename(vault / ".trash" / "cache-moved")

    _button(root, "确认切换并打开").on_click(None)

    assert not (vault / "keikeu_index.json").exists()
    assert (vault / ".trash" / "cache-moved").is_dir()
    assert any("不是受支持的 v0.1 或 Paper v2/v3 Vault" in text for text in _texts(root))


def test_valid_home_v2_with_a_damaged_paper_switches_and_exposes_index_error(
    tmp_path, monkeypatch
):
    vault = tmp_path / "damaged-vault"
    init_vault(vault)
    (vault / "cache" / "K-20260722-001.md").write_text(
        "---\ntype: paper\nschema_version: 2\n---\nbroken\n",
        encoding="utf-8",
    )
    page = FakePage()
    order: list[str] = []
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: order.append("set"),
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: order.append("shell"),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    _button(root, "确认切换并打开").on_click(None)

    index = app_main.rebuild_index(vault)
    assert order == ["set", "shell"]
    assert len(index["errors"]) == 1


def test_v2_index_with_a_v3_paper_rebuilds_v3_and_switches(tmp_path, monkeypatch):
    vault = tmp_path / "mixed-vault"
    init_vault(vault)
    write_paper(
        vault,
        Paper(
            code="K-20260722-001",
            initial_summary="",
            summary="mixed schema fixture",
            display_name="v3 Paper",
            highlights=[Highlight(content="保留内容", display_name="锚点")],
        ),
        destination="cache/K-20260722-001.md",
    )
    (vault / "keikeu_index.json").write_text(
        '{"version": 2, "papers": [], "errors": []}\n',
        encoding="utf-8",
    )
    page = FakePage()
    order: list[str] = []
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: order.append("set"),
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: order.append("shell"),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    _button(root, "确认切换并打开").on_click(None)

    assert order == ["set", "shell"]
    assert vault_index_version(vault) == 3


def test_nonempty_non_vault_is_rejected_without_mutation(tmp_path, monkeypatch):
    candidate = tmp_path / "ordinary-folder"
    candidate.mkdir()
    note = candidate / "keep.txt"
    note.write_text("keep me", encoding="utf-8")
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(
        app_main,
        "init_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not initialize")),
    )
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not rebuild")),
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(AssertionError("must not configure")),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(candidate)
    _button(root, "检查 Vault").on_click(None)

    assert any("不是受支持的 v0.1 或 Paper v2/v3 Vault" in text for text in _texts(root))
    assert note.read_text(encoding="utf-8") == "keep me"


def test_picker_rejects_internal_file_symlink_before_format_detection(tmp_path, monkeypatch):
    vault = tmp_path / "symlink-vault"
    init_vault(vault)
    target = tmp_path / "outside-paper.md"
    target.write_text("outside", encoding="utf-8")
    linked = vault / "cache" / "linked.md"
    linked.symlink_to(target)
    config = tmp_path / "config.json"
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(
        app_main,
        "is_v01_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not detect format")),
    )
    monkeypatch.setattr(
        app_main,
        "is_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not detect format")),
    )
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not rebuild")),
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(AssertionError("must not configure")),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)

    assert any("symlink" in text for text in _texts(root))
    assert linked.is_symlink()
    assert not config.exists()


def test_picker_rejects_a_root_symlink_before_format_detection(tmp_path, monkeypatch):
    target = tmp_path / "target-vault"
    root_link = tmp_path / "linked-vault"
    init_vault(target)
    root_link.symlink_to(target, target_is_directory=True)
    page = FakePage()
    monkeypatch.setattr(
        app_main,
        "is_v01_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not detect format")),
    )
    monkeypatch.setattr(
        app_main,
        "is_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not detect format")),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(root_link)
    _button(root, "检查 Vault").on_click(None)

    assert any("symlink" in text for text in _texts(root))
    assert root_link.is_symlink()


def test_startup_unsafe_non_vault_is_classified_and_rejected_before_copy(
    tmp_path, monkeypatch
):
    source = tmp_path / "configured-outside-home"
    source.mkdir()
    note = source / "keep.txt"
    note.write_text("do not copy", encoding="utf-8")
    page = FakePage()
    calls: list[Path] = []
    monkeypatch.setattr(app_main, "get_vault", lambda _config: source)

    def reject(path: Path) -> Path:
        calls.append(path)
        raise ValueError("simulated outside Home")

    monkeypatch.setattr(app_main, "require_home_path", reject)
    monkeypatch.setattr(
        app_main,
        "copy_vault_no_follow",
        lambda _source, _destination: (_ for _ in ()).throw(
            AssertionError("unsupported source must not be copied")
        ),
    )
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(
            AssertionError("unsupported source must not be configured")
        ),
    )

    app_main.main(page)  # type: ignore[arg-type]

    assert calls == [source.absolute()]
    assert any(
        "不是受支持的 v0.1 或 Paper v2/v3 Vault" in text
        for text in _texts(page.controls[0])
    )
    assert not any(
        getattr(control, "key", None) == "vault-relocation-confirm"
        for control in _walk(page.controls[0])
    )
    assert note.read_text(encoding="utf-8") == "do not copy"


def test_picker_offers_relocation_for_unsafe_v3(tmp_path, monkeypatch):
    source = tmp_path / "unsafe-v3"
    init_vault(source)
    (source / "outlines").mkdir()
    (source / "keikeu_index.json").write_text(
        '{"version": 3, "papers": [], "errors": []}\n',
        encoding="utf-8",
    )
    page = FakePage()
    real_guard = app_main.require_home_path

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)

    assert any("Paper v2/v3 Vault" in text for text in _texts(root))
    assert _by_key(root, "vault-relocation-confirm")
    assert _button(root, "复制、验证并切换")


def test_v2_index_wins_over_leftover_outlines_during_classification(tmp_path):
    vault = tmp_path / "v2-with-outlines"
    init_vault(vault)
    (vault / "outlines").mkdir()
    page = FakePage()

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)

    assert _button(root, "确认切换并打开")
    assert not any(
        getattr(control, "key", None) == "migration-preflight-card"
        for control in _walk(root)
    )


def test_unsupported_readable_index_wins_over_leftover_outlines(tmp_path):
    vault = tmp_path / "unsupported-with-outlines"
    init_vault(vault)
    (vault / "outlines").mkdir()
    (vault / "keikeu_index.json").write_text(
        '{"version": 4, "papers": [], "errors": []}\n',
        encoding="utf-8",
    )
    page = FakePage()

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)

    assert any("index version：4" in text for text in _texts(root))
    assert not any(
        getattr(control, "key", None) == "migration-preflight-card"
        for control in _walk(root)
    )


def test_corrupt_structural_index_is_rebuilt_after_picker_confirmation(
    tmp_path, monkeypatch
):
    vault = tmp_path / "corrupt-index-vault"
    init_vault(vault)
    (vault / "keikeu_index.json").write_text("{broken", encoding="utf-8")
    page = FakePage()
    order: list[str] = []
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: order.append("set"),
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: order.append("shell"),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    _button(root, "确认切换并打开").on_click(None)

    assert order == ["set", "shell"]
    assert vault_index_version(vault) == 3


def test_missing_disposable_index_is_rebuilt_after_picker_confirmation(
    tmp_path, monkeypatch
):
    vault = tmp_path / "missing-index-vault"
    init_vault(vault)
    (vault / "keikeu_index.json").unlink()
    page = FakePage()
    order: list[str] = []
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: order.append("set"),
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: order.append("shell"),
    )

    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(vault)
    _button(root, "检查 Vault").on_click(None)
    _button(root, "确认切换并打开").on_click(None)

    assert order == ["set", "shell"]
    assert vault_index_version(vault) == 3


def test_configured_corrupt_structural_index_rebuilds_during_normal_open(
    tmp_path, monkeypatch
):
    vault = tmp_path / "configured-corrupt-index"
    init_vault(vault)
    (vault / "keikeu_index.json").write_text("{broken", encoding="utf-8")
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: vault)

    app_main.main(page)  # type: ignore[arg-type]

    assert vault_index_version(vault) == 3
    assert _by_key(page.controls[0], "shell-sidebar")


def test_startup_rejects_a_root_symlink_before_shell_or_format_probe(
    tmp_path, monkeypatch
):
    target = tmp_path / "target-vault"
    root_link = tmp_path / "configured-link"
    init_vault(target)
    root_link.symlink_to(target, target_is_directory=True)
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: root_link)
    monkeypatch.setattr(
        app_main,
        "is_v01_vault",
        lambda _vault: (_ for _ in ()).throw(AssertionError("must not detect format")),
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: (_ for _ in ()).throw(AssertionError("must not open shell")),
    )

    app_main.main(page)  # type: ignore[arg-type]

    assert any("symlink" in text for text in _texts(page.controls[0]))
    assert root_link.is_symlink()


def test_startup_opens_home_vault_with_an_isolated_symlink_error(tmp_path, monkeypatch):
    vault = tmp_path / "configured-symlink-vault"
    init_vault(vault)
    target = tmp_path / "outside-paper.md"
    target.write_text("outside", encoding="utf-8")
    (vault / "cache" / "linked.md").symlink_to(target)
    config = tmp_path / "config.json"
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: vault)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    opened: list[Path] = []
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, opened_vault, **_kwargs: opened.append(opened_vault),
    )

    app_main.main(page)  # type: ignore[arg-type]

    assert opened == [vault]
    assert not config.exists()


def test_startup_rejects_root_swap_to_home_symlink_after_classification(
    tmp_path,
    monkeypatch,
):
    vault = tmp_path / "configured-vault"
    parked = tmp_path / "parked-vault"
    redirect = tmp_path / "redirect-vault"
    init_vault(vault)
    init_vault(redirect)
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: vault)
    real_classify = app_main._classify_configured_home_vault

    def classify_then_swap(candidate: Path) -> str:
        source_kind = real_classify(candidate)
        vault.rename(parked)
        vault.symlink_to(redirect, target_is_directory=True)
        return source_kind

    monkeypatch.setattr(
        app_main,
        "_classify_configured_home_vault",
        classify_then_swap,
    )

    app_main.main(page)  # type: ignore[arg-type]

    root = page.controls[0]
    assert any("发生变化" in text or "symlink" in text for text in _texts(root))
    assert _text_field(root, "Vault 文件夹路径").value == str(vault)
    assert vault.is_symlink()
    assert (parked / "keikeu_index.json").exists()
    assert (redirect / "keikeu_index.json").exists()


def test_startup_rejects_v01_ordinary_root_swap_before_migration_gate(
    tmp_path,
    monkeypatch,
):
    vault = _copy_fixture(tmp_path)
    configured = tmp_path / "configured-v01"
    vault.rename(configured)
    vault = configured
    replacement = tmp_path / "replacement-v01"
    shutil.copytree(FIXTURE_VAULT, replacement)
    _remove_preflight_failures(vault)
    _remove_preflight_failures(replacement)
    parked = tmp_path / "parked-v01"
    page = FakePage()
    monkeypatch.setattr(app_main, "get_vault", lambda _config: vault)
    real_classify = app_main._classify_configured_home_vault

    def classify_then_swap(candidate: Path) -> str:
        source_kind = real_classify(candidate)
        vault.rename(parked)
        replacement.rename(vault)
        return source_kind

    monkeypatch.setattr(
        app_main,
        "_classify_configured_home_vault",
        classify_then_swap,
    )

    app_main.main(page)  # type: ignore[arg-type]

    root = page.controls[0]
    assert any("发生变化" in text for text in _texts(root))
    assert _text_field(root, "Vault 文件夹路径").value == str(vault)
    assert not any("创建完整备份并迁移" in text for text in _texts(root))
    assert is_v01_vault(parked)
    assert is_v01_vault(vault)


def test_unsafe_v2_copy_rebuilds_then_switches_and_keeps_source(tmp_path, monkeypatch):
    source = tmp_path / "unsafe-v2"
    destination = tmp_path / "safe-v2-copy"
    config = tmp_path / "config.json"
    init_vault(source)
    before = _file_bytes(source)
    page = FakePage()
    order: list[str] = []
    scans: list[Path] = []
    real_guard = app_main.require_home_path
    real_copy = app_main.copy_vault_no_follow
    real_rebuild = app_main.rebuild_index
    real_scan = app_main.validate_regular_tree_no_follow

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    def tracked_copy(copy_source: Path, copy_destination: Path) -> Path:
        assert scans.count(source.absolute()) >= 2
        order.append("copy")
        return real_copy(copy_source, copy_destination)

    def tracked_scan(path: Path) -> None:
        scans.append(path.expanduser().absolute())
        real_scan(path)

    def tracked_rebuild(vault: Path) -> dict[str, object]:
        order.append("rebuild")
        return real_rebuild(vault)

    def tracked_set(vault: Path, config_path: Path, selection) -> None:
        order.append("set")
        set_vault(vault, config_path, selection)

    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    monkeypatch.setattr(app_main, "validate_regular_tree_no_follow", tracked_scan)
    monkeypatch.setattr(app_main, "copy_vault_no_follow", tracked_copy)
    monkeypatch.setattr(app_main, "rebuild_index", tracked_rebuild)
    monkeypatch.setattr(app_main, "set_vault", tracked_set)
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: order.append("shell"),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)
    assert order == []
    assert not destination.exists()

    _text_field(root, "Home 内全新目标路径").value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "复制、验证并切换").on_click(None)

    assert order == ["copy", "rebuild", "set", "shell"]
    assert get_vault(config) == destination.resolve()
    assert _file_bytes(source) == before


def test_relocation_disables_controls_ignores_duplicate_click_and_recovers_on_failure(
    tmp_path, monkeypatch
):
    source = tmp_path / "unsafe-v2"
    destination = tmp_path / "failed-copy"
    init_vault(source)
    page = FakePage()
    real_guard = app_main.require_home_path

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    path_field = _text_field(root, "Vault 文件夹路径")
    path_field.value = str(source)
    _button(root, "检查 Vault").on_click(None)
    destination_field = _text_field(root, "Home 内全新目标路径")
    destination_field.value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    relocate_button = _button(root, "复制、验证并切换")
    update_count = page.update_count
    copy_calls = 0

    def fail_copy(_source: Path, _destination: Path) -> Path:
        nonlocal copy_calls
        copy_calls += 1
        assert page.update_count > update_count
        assert relocate_button.disabled is True
        assert confirmation.disabled is True
        assert destination_field.disabled is True
        assert path_field.disabled is True
        assert "正在只读复查来源并复制验证" in _by_key(
            root, "vault-relocation-progress"
        ).value
        relocate_button.on_click(None)
        raise OSError("simulated copy failure")

    monkeypatch.setattr(app_main, "copy_vault_no_follow", fail_copy)
    relocate_button.on_click(None)

    assert copy_calls == 1
    assert relocate_button.disabled is False
    assert confirmation.disabled is False
    assert destination_field.disabled is False
    assert path_field.disabled is False
    assert any("simulated copy failure" in text for text in _texts(root))
    assert not destination.exists()


def test_relocation_rejects_an_existing_destination_symlink_without_resolving_it(
    tmp_path, monkeypatch
):
    source = tmp_path / "unsafe-v2"
    destination = tmp_path / "destination-link"
    target = tmp_path / "destination-target"
    init_vault(source)
    target.mkdir()
    destination.symlink_to(target, target_is_directory=True)
    page = FakePage()
    real_guard = app_main.require_home_path

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(
            AssertionError("symlink destination must not be selected")
        ),
    )
    app_main._build_vault_picker(page, show_configured=False)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)
    _text_field(root, "Home 内全新目标路径").value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)

    _button(root, "复制、验证并切换").on_click(None)

    assert destination.is_symlink()
    assert list(target.iterdir()) == []
    assert any("destination already exists" in text for text in _texts(root))


def test_unsafe_v2_validation_failure_does_not_switch_config(tmp_path, monkeypatch):
    old_vault = tmp_path / "old-vault"
    source = tmp_path / "unsafe-v2"
    destination = tmp_path / "invalid-v2-copy"
    config = tmp_path / "config.json"
    init_vault(old_vault)
    init_vault(source)
    set_vault(
        old_vault,
        config,
        capture_vault_selection_token(old_vault),
    )
    before = _file_bytes(source)
    page = FakePage()
    real_guard = app_main.require_home_path

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    monkeypatch.setattr(app_main, "get_vault", lambda _config: old_vault)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    monkeypatch.setattr(
        app_main,
        "rebuild_index",
        lambda _vault: {"papers": [], "errors": [{"path": "cache/broken.md"}]},
    )
    monkeypatch.setattr(
        app_main,
        "_build_shell",
        lambda _page, _vault, **_kwargs: (_ for _ in ()).throw(AssertionError("must not open")),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)
    _text_field(root, "Home 内全新目标路径").value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "复制、验证并切换").on_click(None)

    assert get_vault(config) == old_vault.resolve()
    assert _file_bytes(source) == before
    assert destination.exists()
    assert any("无法验证的 Paper" in text for text in _texts(root))


def test_unsafe_v01_copy_preflights_before_switch_and_cancel_keeps_copy_selected(
    tmp_path, monkeypatch
):
    old_vault = tmp_path / "old-vault"
    source = _copy_fixture(tmp_path)
    _remove_preflight_failures(source)
    destination = tmp_path / "safe-v01-copy"
    config = tmp_path / "config.json"
    init_vault(old_vault)
    set_vault(
        old_vault,
        config,
        capture_vault_selection_token(old_vault),
    )
    before = _file_bytes(source)
    page = FakePage()
    order: list[str] = []
    real_guard = app_main.require_home_path
    real_copy = app_main.copy_vault_no_follow
    real_inspect = app_main.inspect_v01_vault
    real_gate = app_main._build_migration_gate  # type: ignore[attr-defined]

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    def tracked_copy(copy_source: Path, copy_destination: Path) -> Path:
        order.append("copy")
        return real_copy(copy_source, copy_destination)

    def tracked_inspect(vault: Path):
        order.append("preflight")
        return real_inspect(vault)

    def tracked_set(vault: Path, config_path: Path, selection) -> None:
        order.append("set")
        set_vault(vault, config_path, selection)

    def tracked_gate(gate_page: object, vault: Path, **kwargs: object) -> None:
        order.append("gate")
        real_gate(gate_page, vault, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(app_main, "get_vault", lambda _config: old_vault)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    monkeypatch.setattr(app_main, "copy_vault_no_follow", tracked_copy)
    monkeypatch.setattr(app_main, "inspect_v01_vault", tracked_inspect)
    monkeypatch.setattr(app_main, "set_vault", tracked_set)
    monkeypatch.setattr(app_main, "_build_migration_gate", tracked_gate)

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)
    _text_field(root, "Home 内全新目标路径").value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "复制、验证并切换").on_click(None)

    assert order == ["copy", "preflight", "set", "gate"]
    assert get_vault(config) == destination.resolve()
    assert _file_bytes(source) == before
    _button(page.controls[0], "选择其他文件夹").on_click(None)
    assert get_vault(config) == destination.resolve()
    assert _text_field(page.controls[0], "Vault 文件夹路径").value == str(destination.resolve())


def test_unsafe_v01_preflight_blockers_keep_config_unchanged(tmp_path, monkeypatch):
    old_vault = tmp_path / "old-vault"
    source = _copy_fixture(tmp_path)
    destination = tmp_path / "blocked-v01-copy"
    config = tmp_path / "config.json"
    init_vault(old_vault)
    set_vault(
        old_vault,
        config,
        capture_vault_selection_token(old_vault),
    )
    before = _file_bytes(source)
    page = FakePage()
    real_guard = app_main.require_home_path

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    monkeypatch.setattr(app_main, "get_vault", lambda _config: old_vault)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    monkeypatch.setattr(
        app_main,
        "_build_migration_gate",
        lambda _page, _vault, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not open migration gate")
        ),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)
    _text_field(root, "Home 内全新目标路径").value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "复制、验证并切换").on_click(None)

    assert get_vault(config) == old_vault.resolve()
    assert destination.exists()
    assert _file_bytes(source) == before
    assert any("v0.1 迁移预检未通过" in text for text in _texts(root))


def test_unsafe_v01_rechecks_manifest_inside_bound_selection_before_switch(
    tmp_path,
    monkeypatch,
):
    old_vault = tmp_path / "old-vault"
    source = _copy_fixture(tmp_path)
    _remove_preflight_failures(source)
    destination = tmp_path / "changed-v01-copy"
    config = tmp_path / "config.json"
    init_vault(old_vault)
    set_vault(
        old_vault,
        config,
        capture_vault_selection_token(old_vault),
    )
    assert app_main.inspect_v01_vault(source).ready is True
    page = FakePage()
    real_guard = app_main.require_home_path
    real_copy = app_main.copy_vault_no_follow

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    def inject_invalid_cache(copy_source: Path, copy_destination: Path) -> Path:
        copied = real_copy(copy_source, copy_destination)
        (copied / "cache" / "injected-invalid.md").write_text(
            "not a legacy Cache",
            encoding="utf-8",
        )
        return copied

    monkeypatch.setattr(app_main, "get_vault", lambda _config: old_vault)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    monkeypatch.setattr(app_main, "copy_vault_no_follow", inject_invalid_cache)
    monkeypatch.setattr(
        app_main,
        "_build_migration_gate",
        lambda _page, _vault, **_kwargs: (_ for _ in ()).throw(
            AssertionError("invalid manifest must not open migration gate")
        ),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)
    _text_field(root, "Home 内全新目标路径").value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "复制、验证并切换").on_click(None)

    assert get_vault(config) == old_vault.resolve()
    assert (destination / "cache" / "injected-invalid.md").is_file()
    assert any("injected-invalid.md" in text for text in _texts(root))
    assert any("当前配置未修改" in text for text in _texts(root))


def test_unsafe_v01_migration_failure_keeps_safe_copy_selected(tmp_path, monkeypatch):
    source = _copy_fixture(tmp_path)
    _remove_preflight_failures(source)
    destination = tmp_path / "safe-v01-copy"
    config = tmp_path / "config.json"
    before = _file_bytes(source)
    page = FakePage()
    real_guard = app_main.require_home_path

    def simulated_guard(path: Path) -> Path:
        if path == source:
            raise ValueError("simulated outside Home")
        return real_guard(path)

    monkeypatch.setattr(app_main, "get_vault", lambda _config: None)
    monkeypatch.setattr(app_main, "CONFIG_PATH", config)
    monkeypatch.setattr(app_main, "require_home_path", simulated_guard)
    monkeypatch.setattr(
        migration_page_mod,
        "migrate_v01_vault",
        lambda _vault, **_kwargs: (_ for _ in ()).throw(OSError("simulated migration failure")),
    )

    app_main._build_vault_picker(page)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    _text_field(root, "Vault 文件夹路径").value = str(source)
    _button(root, "检查 Vault").on_click(None)
    _text_field(root, "Home 内全新目标路径").value = str(destination)
    confirmation = _by_key(root, "vault-relocation-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "复制、验证并切换").on_click(None)

    migration_root = page.controls[0]
    migration_confirmation = _by_key(migration_root, "migration-confirm")
    migration_confirmation.value = True
    migration_confirmation.on_change(None)
    _button(migration_root, "创建完整备份并迁移").on_click(None)

    assert get_vault(config) == destination.resolve()
    assert _file_bytes(source) == before
    assert any("simulated migration failure" in text for text in _texts(migration_root))


def test_open_migrated_failure_keeps_the_report_page_and_shows_an_error(
    tmp_path, monkeypatch
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    page = FakePage()
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda _vault, _config, _selection: (_ for _ in ()).throw(
            OSError("simulated config failure")
        ),
    )

    app_main._build_migration_gate(page, vault)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    confirmation = _by_key(root, "migration-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "创建完整备份并迁移").on_click(None)
    _button(root, "打开已迁移的 Vault").on_click(None)

    assert _by_key(page.controls[0], "migration-preflight-card")
    assert "simulated config failure" in _texts(page.overlay[-1])[0]


def test_open_migrated_strictly_validates_trash_before_switching_config(
    tmp_path, monkeypatch
):
    vault = _copy_fixture(tmp_path)
    _remove_preflight_failures(vault)
    page = FakePage()
    configured: list[Path] = []
    monkeypatch.setattr(
        app_main,
        "set_vault",
        lambda selected, _config, _selection: configured.append(selected),
    )

    app_main._build_migration_gate(page, vault)  # type: ignore[attr-defined, arg-type]
    root = page.controls[0]
    confirmation = _by_key(root, "migration-confirm")
    confirmation.value = True
    confirmation.on_change(None)
    _button(root, "创建完整备份并迁移").on_click(None)
    (vault / ".trash" / "cache" / "K-20260722-999.md").write_text(
        "not a Paper",
        encoding="utf-8",
    )

    _button(root, "打开已迁移的 Vault").on_click(None)

    assert configured == []
    assert "missing frontmatter" in _texts(page.overlay[-1])[0]
    assert _by_key(page.controls[0], "migration-preflight-card")


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
