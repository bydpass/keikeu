"""Focused protocol-v2 contracts for the transport-neutral application service."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import shutil

import pytest

from keikeu_bridge.dto import (
    CardPageDto,
    PaperEditableDto,
    PaperReconcileRequestDto,
    PaperSaveDto,
)
from keikeu_bridge import service as service_module
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


def _reconcile_request(
    paper,
    submitted: PaperEditableDto,
) -> PaperReconcileRequestDto:
    return PaperReconcileRequestDto(
        vault_locator=paper.vault_locator,
        target_path=paper.target_path,
        code=paper.code,
        created=paper.created,
        source_digest=paper.source_digest,
        baseline=_editable(paper) if paper.source_digest is not None else None,
        submitted=submitted,
    )


def _replace_content(vault: Path, paper, content: str) -> None:
    path = vault / paper.target_path
    stored, _source = read_paper_v4_snapshot(path)
    stored.pages[0].content = content
    path.write_bytes(render_paper_v4_bytes(stored))


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


def test_first_save_conflict_is_known_not_commit_unknown(service_and_vault):
    service, vault, _locator = service_and_vault
    draft = service.paper_create_draft()
    target = vault / draft.target_path
    original = PaperV4(code=draft.code, pages=[CardPageV4(content="Existing")])
    write_paper_v4(vault, original, destination=draft.target_path)

    with pytest.raises(ServiceError) as caught:
        service.paper_save(
            PaperSaveDto(
                draft.edit_token,
                draft.vault_locator,
                None,
                (),
                (CardPageDto(None, "Submitted", None),),
            )
        )

    assert caught.value.code == "conflict"
    assert read_paper_v4_snapshot(target)[0].pages[0].content == "Existing"


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


def test_reconcile_existing_fault_matrix_and_page_safe_repair(service_and_vault):
    service, vault, _locator = service_and_vault
    saved, _warnings = _save_paper(service, "Baseline")
    submitted = PaperEditableDto(
        saved.display_name,
        saved.tags,
        (CardPageDto("First", "Submitted", "summary"),),
    )
    request = _reconcile_request(saved, submitted)
    path = vault / saved.target_path

    path.unlink()
    missing = service.paper_reconcile_save(request)
    assert missing.state == "stale" and missing.stale_reason == "missing_existing"

    path.write_bytes(
        render_paper_v4_bytes(
            PaperV4(
                code=saved.code,
                created=datetime.fromisoformat(saved.created),
                updated=datetime.fromisoformat(saved.updated),
                pages=[CardPageV4("Third", name="First", type="summary")],
            )
        )
    )
    third = service.paper_reconcile_save(request)
    assert third.state == "stale" and third.stale_reason == "third_content"

    changed_identity = read_paper_v4_snapshot(path)[0]
    changed_identity.code = "K-20260802-999"
    path.write_bytes(render_paper_v4_bytes(changed_identity))
    identity = service.paper_reconcile_save(request)
    assert identity.state == "stale" and identity.stale_reason == "identity_changed"

    broken = render_paper_v4_bytes(changed_identity).replace(
        b'<!-- keikeu:page {"name":"First","type":"summary"} -->',
        b'<!-- keikeu:page {"name":"First","type":"invalid"} -->',
    )
    path.write_bytes(broken)
    repair = service.paper_reconcile_save(request)
    assert repair.state == "repair_required"
    assert repair.repair is not None and repair.repair.origin == "unknown_save"
    assert repair.repair.page_number == 1
    assert "Third" not in repair.repair.reason


def test_reconcile_invalid_submitted_depends_on_whether_disk_changed(service_and_vault):
    service, vault, _locator = service_and_vault
    saved, _warnings = _save_paper(service, "Baseline")
    invalid = PaperEditableDto(None, (), (CardPageDto(None, "", None),))
    request = _reconcile_request(saved, invalid)

    unchanged = service.paper_reconcile_save(request)
    assert unchanged.state == "not_committed" and unchanged.paper is not None

    _replace_content(vault, saved, "Third content")
    changed = service.paper_reconcile_save(request)
    assert changed.state == "stale" and changed.stale_reason == "submitted_invalid"


def test_reconcile_first_save_missing_committed_duplicate_and_broken(service_and_vault):
    service, vault, _locator = service_and_vault
    draft = service.paper_create_draft()
    submitted = PaperEditableDto(
        "First save",
        ("tag",),
        (CardPageDto("Page", "Submitted", "summary"),),
    )
    request = _reconcile_request(draft, submitted)

    missing = service.paper_reconcile_save(request)
    assert missing.state == "not_committed" and missing.paper is not None

    target = vault / draft.target_path
    target.write_bytes(
        render_paper_v4_bytes(
            PaperV4(
                code=draft.code,
                display_name="First save",
                tags=["tag"],
                pages=[CardPageV4("Submitted", name="Page", type="summary")],
                created=datetime.fromisoformat(draft.created),
                updated=datetime(2026, 8, 2, 13, 0),
            )
        )
    )
    committed = service.paper_reconcile_save(request)
    assert committed.state == "committed" and committed.paper is not None

    target.unlink()
    duplicate = vault / "cache" / "Elsewhere"
    duplicate.mkdir()
    (duplicate / f"{draft.code}.md").write_bytes(
        render_paper_v4_bytes(
            PaperV4(
                code=draft.code,
                pages=[CardPageV4("Elsewhere")],
                created=datetime.fromisoformat(draft.created),
            )
        )
    )
    duplicate_result = service.paper_reconcile_save(request)
    assert duplicate_result.state == "stale"
    assert duplicate_result.stale_reason == "duplicate_code"

    (duplicate / f"{draft.code}.md").unlink()
    target.write_bytes(b"broken author bytes")
    broken = service.paper_reconcile_save(request)
    assert broken.state == "repair_required"
    assert broken.repair is not None
    assert "broken author bytes" not in broken.repair.reason


def test_reconcile_audits_other_index_rows_and_root_identity_before_target_read(
    service_and_vault,
    monkeypatch,
):
    service, vault, _locator = service_and_vault
    saved, _warnings = _save_paper(service, "Baseline")
    other, _warnings = _save_paper(service, "Other")
    _replace_content(vault, other, "Changed outside Index")
    request = _reconcile_request(saved, _editable(saved))

    degraded = service.paper_reconcile_save(request)
    assert degraded.state == "not_committed"
    assert degraded.index_state == "degraded"

    parked = vault.with_name("parked-vault")
    vault.rename(parked)
    vault.mkdir()
    monkeypatch.setattr(
        service_module,
        "read_paper_v4_snapshot",
        lambda _path: (_ for _ in ()).throw(AssertionError("target was read")),
    )
    changed_root = service.paper_reconcile_save(request)
    assert changed_root.state == "stale"
    assert changed_root.stale_reason == "vault_changed"
    assert changed_root.index_state == "not_checked"


def test_post_commit_failures_are_never_reported_as_retryable(service_and_vault, monkeypatch):
    service, vault, locator = service_and_vault
    saved, _warnings = _save_paper(service, "Before")
    opened = service.paper_open(saved.target_path)
    assert opened.paper is not None

    real_replace = service_module.replace_paper_v4_bytes

    def replace_then_fail(*args, **kwargs):
        real_replace(*args, **kwargs)
        raise OSError("injected after Paper replacement")

    monkeypatch.setattr(service_module, "replace_paper_v4_bytes", replace_then_fail)
    with pytest.raises(ServiceError) as paper_error:
        service.paper_save(
            PaperSaveDto(
                opened.paper.edit_token,
                locator,
                None,
                (),
                (CardPageDto(None, "After", None),),
            )
        )
    assert paper_error.value.code == "commit_unknown"
    assert read_paper_v4_snapshot(vault / saved.target_path)[0].pages[0].content == "After"

    monkeypatch.setattr(service_module, "replace_paper_v4_bytes", real_replace)
    real_move = service_module.move_papers

    def move_then_fail(*args, **kwargs):
        real_move(*args, **kwargs)
        raise OSError("injected after path mutation")

    service.library_create_folder("Ideas", locator)
    monkeypatch.setattr(service_module, "move_papers", move_then_fail)
    with pytest.raises(ServiceError) as move_error:
        service.library_move([saved.target_path], "Ideas", locator)
    assert move_error.value.code == "commit_unknown"
    assert (vault / "cache" / "Ideas" / Path(saved.target_path).name).is_file()

    monkeypatch.setattr(service_module, "move_papers", real_move)
    real_rebuild = service_module.rebuild_index_v4

    def rebuild_then_fail(*args, **kwargs):
        real_rebuild(*args, **kwargs)
        raise OSError("injected after Index replacement")

    monkeypatch.setattr(service_module, "rebuild_index_v4", rebuild_then_fail)
    with pytest.raises(ServiceError) as index_error:
        service.library_rebuild(locator)
    assert index_error.value.code == "commit_unknown"
    assert json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8"))["version"] == 4


def test_vault_config_change_followed_by_readback_failure_is_commit_unknown(
    service_and_vault,
    monkeypatch,
):
    service, _vault, _locator = service_and_vault
    destination = _vault.with_name("other-vault")
    vault_module.init_vault(destination)
    preview = service.vault_inspect(str(destination))

    monkeypatch.setattr(
        service,
        "_startup_for_selected",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("injected after config mutation")
        ),
    )
    with pytest.raises(ServiceError) as caught:
        service.vault_open(preview.token)

    assert caught.value.code == "commit_unknown"
    assert vault_module.get_vault(service._config_path) == destination  # noqa: SLF001


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
