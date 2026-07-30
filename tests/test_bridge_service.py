"""Focused contracts for the transport-neutral application service."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from keikeu_bridge import (
    HighlightDto,
    KeikeuService,
    PaperSaveDto,
    ServiceError,
)
from keikeu_core import vault as vault_module
from keikeu_core.indexer import rebuild_index
from keikeu_core.markdown_io import (
    next_paper_code,
    read_paper,
    write_paper,
)
from keikeu_core.models import Paper


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
    assert preview.kind == "create"
    assert not vault.exists()
    startup = service.vault_initialize(preview.token)
    assert startup.state == "ready"

    return service, vault


def _save_paper(
    service: KeikeuService,
    summary: str,
    *,
    name: str | None = None,
    highlight: str = "",
):
    draft = service.paper_create_draft()
    highlights = (
        (HighlightDto("Anchor", highlight),)
        if highlight
        else ()
    )
    return service.paper_save(
        PaperSaveDto(
            edit_token=draft.edit_token,
            summary=summary,
            display_name=name,
            highlights=highlights,
            tags=("tag", "tag"),
        )
    )


def test_startup_reuses_config_without_claiming_daily_card_twice(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    first_service = _service_for_home(tmp_path)
    preview = first_service.vault_inspect(str(tmp_path / "vault"))

    first = first_service.vault_initialize(preview.token)
    second = _service_for_home(tmp_path).startup_load()

    assert first.state == second.state == "ready"
    assert first.show_daily_card is True
    assert second.show_daily_card is False


def test_paper_save_freezes_initial_summary_and_preserves_unknown_frontmatter(
    service_and_vault,
):
    service, vault = service_and_vault
    saved = _save_paper(
        service,
        "First summary",
        name="Rain Platform",
        highlight="Keep the station clock visible.",
    )

    updated = service.paper_save(
        PaperSaveDto(
            edit_token=saved.edit_token,
            summary="Second summary",
            display_name=saved.display_name,
            highlights=saved.highlights,
            tags=saved.tags,
        )
    )
    stored = read_paper(vault / str(updated.path))

    assert stored.initial_summary == "First summary"
    assert stored.summary == "Second summary"
    assert stored.tags == ["tag"]
    assert stored.highlights[0].display_name == "Anchor"

    code = next_paper_code(vault)
    legacy_path = write_paper(
        vault,
        Paper(
            code=code,
            initial_summary="",
            summary="Legacy-compatible summary",
            extra_frontmatter={"private_marker": "keep-me"},
        ),
        destination=Path("cache") / f"{code}.md",
    )
    rebuild_index(vault)
    opened = service.paper_open(str(legacy_path.relative_to(vault)))
    service.paper_save(
        PaperSaveDto(
            edit_token=opened.edit_token,
            summary="Edited through service",
        )
    )

    assert read_paper(legacy_path).extra_frontmatter == {
        "private_marker": "keep-me"
    }


def test_paper_save_does_not_report_index_refresh_failure_as_save_failure(
    service_and_vault,
    monkeypatch,
):
    service, vault = service_and_vault
    refresh_attempts = 0

    def fail_index_refresh(_vault: Path) -> dict[str, object]:
        nonlocal refresh_attempts
        refresh_attempts += 1
        raise OSError("injected index refresh failure")

    monkeypatch.setattr(
        "keikeu_bridge.service.rebuild_index",
        fail_index_refresh,
    )

    saved = _save_paper(service, "Durable Markdown")

    assert refresh_attempts == 1
    assert saved.summary == "Durable Markdown"
    assert read_paper(vault / str(saved.path)).summary == "Durable Markdown"


def test_paper_save_returns_stable_error_for_external_change(service_and_vault):
    service, vault = service_and_vault
    saved = _save_paper(service, "Original")
    opened = service.paper_open(str(saved.path))
    path = vault / str(saved.path)
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(ServiceError) as caught:
        service.paper_save(
            PaperSaveDto(
                edit_token=opened.edit_token,
                summary="Must not overwrite",
            )
        )

    assert caught.value.code == "stale_snapshot"
    assert caught.value.recovery == "reopen"
    assert path.read_bytes().endswith(b"\n\n")


def test_flashcard_and_library_views_keep_python_projection(service_and_vault):
    service, _vault = service_and_vault
    first = _save_paper(
        service,
        "Summary first",
        name="Éclair",
        highlight="Second card",
    )
    _save_paper(service, "Other Paper", name="Zulu")

    deck = service.flashcard_open(str(first.path))
    assert deck.paper_label == f"Éclair ({first.code})"
    assert [card.title for card in deck.cards] == ["Summary", "Anchor"]
    assert [card.content for card in deck.cards] == ["Summary first", "Second card"]

    assert service.library_create_folder("Ideas") == "Ideas"
    moved = service.library_move([str(first.path)], "Ideas")
    assert len(moved) == 1 and moved[0].succeeded
    view = service.library_query(
        scope="folder:Ideas",
        search="anchor",
        sort="name",
    )
    assert [entry.display_name for entry in view.entries] == ["Éclair"]
    assert view.entries[0].folder == "Ideas"

    branched = service.library_branch(view.entries[0].path)
    assert branched.succeeded
    assert branched.destination is not None
    assert branched.destination.startswith("cache/Ideas/")


def test_trash_round_trip_returns_per_item_reports(service_and_vault):
    service, _vault = service_and_vault
    saved = _save_paper(service, "Trash me")

    deleted = service.library_soft_delete([str(saved.path)])
    assert deleted[0].succeeded
    trash = service.library_query(scope="trash")
    assert [entry.code for entry in trash.entries] == [saved.code]

    restored = service.library_restore([trash.entries[0].path])
    assert restored[0].succeeded
    assert service.library_query(scope="trash").entries == ()


def test_v01_preview_uses_relative_issues_and_does_not_migrate(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    source = Path(__file__).parent / "fixtures" / "v01-vault"
    vault = tmp_path / "legacy-vault"
    shutil.copytree(source, vault)
    original_index = (vault / "keikeu_index.json").read_bytes()

    preview = _service_for_home(tmp_path).vault_inspect(str(vault))

    assert preview.kind == "migration"
    assert preview.migration is not None
    assert preview.migration.ready is False
    assert preview.migration.issues
    assert all(not issue.path.startswith("/") for issue in preview.migration.issues)
    assert (vault / "keikeu_index.json").read_bytes() == original_index


def test_ready_v01_migration_runs_through_service_and_activates_vault(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(vault_module, "_current_home", lambda: tmp_path)
    source = Path(__file__).parent / "fixtures" / "v01-vault"
    vault = tmp_path / "legacy-vault"
    shutil.copytree(source, vault)
    (vault / "cache" / "2026-07-03-090000-a103-empty-raw.md").unlink()
    (vault / "cache" / "2026-07-04-090000-a104-corrupt-status.md").unlink()
    service = _service_for_home(tmp_path)
    preview = service.vault_inspect(str(vault))

    assert preview.migration is not None and preview.migration.ready
    result = service.migration_run(preview.migration.token)

    assert result.converted_count == 2
    assert all(not path.startswith("/") for path in result.paper_paths)
    assert service.startup_load().state == "ready"


def test_system_target_never_accepts_an_absolute_or_traversing_paper_path(
    service_and_vault,
):
    service, vault = service_and_vault
    saved = _save_paper(service, "Open me")

    assert service.resolve_system_target("open", str(saved.path)) == (
        vault / str(saved.path)
    )
    with pytest.raises(ServiceError):
        service.resolve_system_target("open", "/private/tmp/not-a-paper.md")
    with pytest.raises(ServiceError):
        service.resolve_system_target("reveal", "../outside.md")


def test_invalid_or_expired_edit_token_is_not_treated_as_core_failure(
    service_and_vault,
):
    service, _vault = service_and_vault

    with pytest.raises(ServiceError) as caught:
        service.paper_save(PaperSaveDto(edit_token="missing", summary="No"))

    assert caught.value.code == "session_expired"
