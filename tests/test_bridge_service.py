"""Focused protocol-v2 contracts for the transport-neutral application service."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from keikeu_bridge.dto import (
    CardPageDto,
    PaperEditableDto,
    PaperReconcileRequestDto,
    PaperSaveDto,
)
from keikeu_bridge.service import KeikeuService, ServiceError
from keikeu_core import vault as vault_module
from keikeu_core.indexer import rebuild_index_v4
from keikeu_core.markdown_io import (
    read_paper_v4_snapshot,
    render_paper_v4_bytes,
    write_paper_v4,
)
from keikeu_core.models import CardPageV4, PaperV4


def _service_for_home(home: Path) -> KeikeuService:
    return KeikeuService(
        config_path=home / ".keikeu_config.json",
        state_path=home / ".keikeu_state.json",
    )


@pytest.fixture
def service_and_vault(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    service = _service_for_home(tmp_path)
    vault = tmp_path / "vault"

    preview = service.vault_inspect(str(vault))
    assert preview.kind == "create" and preview.candidate_locator is None
    startup = service.vault_initialize(preview.token)
    assert startup.state == "ready"
    assert startup.vault_locator and startup.index_state == "current"
    return service, vault, startup.vault_locator


def _save_paper(
    service: KeikeuService,
    content: str,
    *,
    name: str | None = None,
    second_page: str = "",
):
    draft = service.paper_create_draft()
    pages = [CardPageDto("First", content, "summary")]
    if second_page:
        pages.append(CardPageDto("Anchor", second_page, "snapshot"))
    result = service.paper_save(
        PaperSaveDto(
            edit_token=draft.edit_token,
            vault_locator=draft.vault_locator,
            display_name=name,
            tags=("tag", "tag"),
            pages=tuple(pages),
        )
    )
    return result.paper, result.warnings


def _editable(paper) -> PaperEditableDto:
    return PaperEditableDto(paper.display_name, paper.tags, paper.pages)


def test_startup_reuses_config_without_claiming_daily_card_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    first_service = _service_for_home(tmp_path)
    preview = first_service.vault_inspect(str(tmp_path / "vault"))

    first = first_service.vault_initialize(preview.token)
    second = _service_for_home(tmp_path).startup_load()

    assert first.state == second.state == "ready"
    assert first.show_daily_card is True
    assert second.show_daily_card is False
    assert first.vault_locator == second.vault_locator


def test_paper_v4_save_updates_whole_asset_and_preserves_unknown_frontmatter(
    service_and_vault,
):
    service, vault, _locator = service_and_vault
    saved, warnings = _save_paper(
        service,
        "First page",
        name="Rain Platform",
        second_page="Keep the station clock visible.",
    )
    assert warnings == ()

    updated = service.paper_save(
        PaperSaveDto(
            edit_token=saved.edit_token,
            vault_locator=saved.vault_locator,
            display_name=saved.display_name,
            tags=saved.tags,
            pages=(
                CardPageDto("First", "Edited first page", "summary"),
                saved.pages[1],
            ),
        )
    ).paper
    stored, _source = read_paper_v4_snapshot(vault / str(updated.path))
    assert stored.pages[0].content == "Edited first page"
    assert stored.tags == ["tag"]
    assert stored.pages[1].name == "Anchor"

    custom = PaperV4(
        code="K-20260802-901",
        pages=[CardPageV4("Original")],
        extra_frontmatter={"private_marker": "keep-me"},
    )
    custom_path = write_paper_v4(
        vault,
        custom,
        destination="cache/K-20260802-901.md",
    )
    rebuild_index_v4(vault)
    opened = service.paper_open(str(custom_path.relative_to(vault)))
    assert opened.state == "opened" and opened.paper is not None
    service.paper_save(
        PaperSaveDto(
            edit_token=opened.paper.edit_token,
            vault_locator=opened.paper.vault_locator,
            display_name=None,
            tags=(),
            pages=(CardPageDto(None, "Edited", None),),
        )
    )
    assert read_paper_v4_snapshot(custom_path)[0].extra_frontmatter == {
        "private_marker": "keep-me"
    }


def test_paper_save_reports_index_degraded_after_markdown_commit(
    service_and_vault,
    monkeypatch,
):
    service, vault, _locator = service_and_vault
    monkeypatch.setattr(
        "keikeu_bridge.service.rebuild_index_v4",
        lambda _vault: (_ for _ in ()).throw(OSError("synthetic index failure")),
    )

    saved, warnings = _save_paper(service, "Durable Markdown")

    assert warnings == ("index_degraded",)
    assert read_paper_v4_snapshot(vault / str(saved.path))[0].pages[0].content == (
        "Durable Markdown"
    )


def test_paper_save_returns_stale_without_overwriting_external_change(service_and_vault):
    service, vault, _locator = service_and_vault
    saved, _warnings = _save_paper(service, "Original")
    opened = service.paper_open(str(saved.path))
    assert opened.paper is not None
    path = vault / str(saved.path)
    changed = path.read_bytes() + b"\n"
    path.write_bytes(changed)

    with pytest.raises(ServiceError) as caught:
        service.paper_save(
            PaperSaveDto(
                edit_token=opened.paper.edit_token,
                vault_locator=opened.paper.vault_locator,
                display_name=None,
                tags=(),
                pages=(CardPageDto(None, "Must not overwrite", None),),
            )
        )

    assert caught.value.code == "stale_snapshot"
    assert path.read_bytes() == changed


def test_library_v4_projects_all_pages_and_path_mutations(service_and_vault):
    service, _vault, locator = service_and_vault
    first, _warnings = _save_paper(
        service,
        "Summary first",
        name="Éclair",
        second_page="Second searchable card",
    )
    _save_paper(service, "Other Paper", name="Zulu")

    created = service.library_create_folder("Ideas", locator)
    assert created.name == "Ideas" and created.warnings == ()
    moved = service.library_move([str(first.path)], "Ideas", locator)
    assert len(moved.reports) == 1 and moved.reports[0].succeeded
    view = service.library_query(
        scope="folder:Ideas",
        search="searchable",
        sort="name",
        verify_index=True,
    )
    assert [entry.display_name for entry in view.entries] == ["Éclair"]
    assert view.entries[0].page_count == 2
    assert view.entries[0].page_names == ("First", "Anchor")
    assert view.index_state == "current" and view.vault_locator == locator

    branched = service.library_branch(view.entries[0].path, locator)
    assert branched.report.succeeded and branched.report.destination
    assert branched.report.destination.startswith("cache/Ideas/")


def test_trash_round_trip_returns_per_item_reports(service_and_vault):
    service, _vault, locator = service_and_vault
    saved, _warnings = _save_paper(service, "Trash me")

    deleted = service.library_soft_delete([str(saved.path)], locator)
    assert deleted.reports[0].succeeded
    trash = service.library_query(scope="trash")
    assert [entry.code for entry in trash.entries] == [saved.code]

    restored = service.library_restore([trash.entries[0].path], locator)
    assert restored.reports[0].succeeded
    assert service.library_query(scope="trash").entries == ()


def test_open_damage_is_a_tagged_success_without_author_text(service_and_vault):
    service, vault, _locator = service_and_vault
    broken = vault / "cache" / "K-20260802-777.md"
    broken.write_text("broken author body", encoding="utf-8")

    result = service.paper_open("cache/K-20260802-777.md")

    assert result.state == "repair_required" and result.paper is None
    assert result.repair is not None and result.repair.origin == "open"
    assert "broken author body" not in result.repair.reason


def test_reconcile_distinguishes_not_committed_committed_and_vault_change(
    service_and_vault,
):
    service, vault, _locator = service_and_vault
    saved, _warnings = _save_paper(service, "Baseline")
    baseline = _editable(saved)
    submitted = PaperEditableDto(
        saved.display_name,
        saved.tags,
        (CardPageDto("First", "Submitted", "summary"),),
    )
    request = PaperReconcileRequestDto(
        vault_locator=saved.vault_locator,
        target_path=saved.target_path,
        code=saved.code,
        created=saved.created,
        source_digest=saved.source_digest,
        baseline=baseline,
        submitted=submitted,
    )

    not_committed = service.paper_reconcile_save(request)
    assert not_committed.state == "not_committed"
    assert not_committed.paper is not None
    assert not_committed.paper.pages[0].content == "Submitted"

    disk, _source = read_paper_v4_snapshot(vault / saved.target_path)
    disk.pages[0].content = "Submitted"
    (vault / saved.target_path).write_bytes(render_paper_v4_bytes(disk))
    committed = service.paper_reconcile_save(request)
    assert committed.state == "committed" and committed.paper is not None

    changed_vault = service.paper_reconcile_save(
        PaperReconcileRequestDto(
            **{**request.__dict__, "vault_locator": "vault-v1:wrong"},
        )
    )
    assert changed_vault.state == "stale"
    assert changed_vault.stale_reason == "vault_changed"
    assert changed_vault.index_state == "not_checked"


def test_v01_runs_as_two_explicit_migration_stages(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    source = Path(__file__).parent / "fixtures" / "v01-vault"
    vault = tmp_path / "legacy-vault"
    shutil.copytree(source, vault)
    (vault / "cache" / "2026-07-03-090000-a103-empty-raw.md").unlink()
    (vault / "cache" / "2026-07-04-090000-a104-corrupt-status.md").unlink()
    service = _service_for_home(tmp_path)
    preview = service.vault_inspect(str(vault))
    assert preview.migration and preview.migration.kind == "v01_to_v3"

    first = service.migration_run(preview.migration.token)
    assert first.kind == "v01_to_v3" and first.converted_count == 2
    next_startup = service.startup_load()
    assert next_startup.state == "migration"
    assert next_startup.migration and next_startup.migration.kind == "paper_to_v4"

    second = service.migration_run(next_startup.migration.token)
    assert second.kind == "paper_to_v4" and second.converted_count == 2
    assert service.startup_load().state == "ready"


def test_v01_preview_uses_relative_issues_and_does_not_migrate(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    source = Path(__file__).parent / "fixtures" / "v01-vault"
    vault = tmp_path / "legacy-vault"
    shutil.copytree(source, vault)
    original_index = (vault / "keikeu_index.json").read_bytes()

    preview = _service_for_home(tmp_path).vault_inspect(str(vault))

    assert preview.migration is not None and preview.migration.ready is False
    assert all(not issue.path.startswith("/") for issue in preview.migration.issues)
    assert (vault / "keikeu_index.json").read_bytes() == original_index


def test_system_target_and_locator_reject_untrusted_targets(service_and_vault):
    service, vault, locator = service_and_vault
    saved, _warnings = _save_paper(service, "Open me")
    assert service.resolve_system_target("open", str(saved.path)) == vault / str(saved.path)
    with pytest.raises(ServiceError):
        service.resolve_system_target("open", "/private/tmp/not-a-paper.md")
    with pytest.raises(ServiceError):
        service.library_create_folder("Ideas", "vault-v1:wrong")
    assert locator == saved.vault_locator


def test_invalid_or_expired_edit_token_is_a_session_error(service_and_vault):
    service, _vault, locator = service_and_vault
    with pytest.raises(ServiceError) as caught:
        service.paper_save(
            PaperSaveDto(
                edit_token="missing",
                vault_locator=locator,
                display_name=None,
                tags=(),
                pages=(CardPageDto(None, "No", None),),
            )
        )
    assert caught.value.code == "session_expired"
