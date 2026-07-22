# keikeu Project Map

> Authority: current coordinates, module entry points, documentation index, and next gate. Product behavior belongs in [SPEC](SPEC.md); rules belong in [RULES](RULES.md).

Updated: 2026-07-22

## Current coordinates

| Track | State | Evidence boundary |
| --- | --- | --- |
| Road v0.2 engineering Phases 0–7 | Complete | Paper v2, migration, recovery, macOS UI, Flashcard, Outline retirement, and macOS file-service smoke are implemented and recorded. |
| Road v0.2 Phase 8 product acceptance | Complete | The author completed the real one-shot and two-session short/medium scenarios; no P0/P1 was reported. P2/P3 observations are recorded separately. |
| Phase 7.5 lightweight iOS | Quick-test build complete on an independent branch | Responsive shell and app-sandbox Vault were exercised on `codex/fix-ios-device-readiness`. This is a lightweight iOS version for rapid testing, not a step in the macOS Road sequence. |
| Phase 8.5 / Road v0.3 preparation | Documentation reform implemented; review pending | This is the precursor to the next macOS version. Current evidence covers the authority map, HTML maps, archive, link gate, browser QA, and bounded Graphify trial; independent fresh-agent cold start was not run. |
| Road v0.3 Phase 6 | Complete; Phase 7 next | The approved [Planbook](planbook_road_v0_3.md) is executing: Flashcard now selects Papers by indexed path, resets to page 1, supports list/jump/arrow navigation with bounded feedback, and stores no position. The daily start card claims only a local date before display, while `Cmd+S`, `Cmd+F`, and `Esc` use page-local handlers. CP4 is complete; final documentation calibration, candidate smoke, and product acceptance remain Phase 7 scope. |

Phase 8 product acceptance is complete. Road v0.2 is marked by local annotated tag `v0.2.0` at `d0feac0269a5619f5dbf27c04347ba69c5665b42`; archival remains a separate developer decision. Automated tests, platform smoke, and author acceptance remain distinct evidence.

Phase 7.5 and Phase 8.5 are separate tracks: Phase 7.5 is the independent lightweight iOS test version; Phase 8.5 prepares Road v0.3 and the next macOS version. Phase 7.5 is not a merge gate for Phase 8.5.

Road v0.3 product decisions and Planbook are approved. Phase 0 authority/fixtures through Phase 6 Flashcard/daily-card/keyboard engineering are complete, including CP4. Safe relocation supports v0.1 and mixed Paper v2/v3 Vaults. Native atomic no-replace rename/exchange is available on Darwin/Linux; unsupported platforms fail before destructive mutation. `architecture.html` remains the explicitly marked Road v0.3 target until Phase 7 recalibrates it against verified code.

## Product flow

```text
Paper Markdown → Flashcard → external prose editor
```

See [SPEC](SPEC.md) for the contract and [interaction.html](design/interaction.html) for executable state examples.

## Current runtime map (Paper v3 + folder-aware paths)

| Area | Responsibility | Source | Direct evidence |
| --- | --- | --- | --- |
| Domain model | Paper v3/Highlight naming validation and normalization | [`models.py`](../src/keikeu_core/models.py) | [`test_models.py`](../tests/test_models.py) |
| Markdown | Paper v2/v3 parse, v3 render, exact-destination create/update, clean same-folder branch copy | [`markdown_io.py`](../src/keikeu_core/markdown_io.py) | [`test_markdown_io.py`](../tests/test_markdown_io.py) |
| Vault | Home/path validation, one-level active/Trash enumeration, global code allocation, folder/move/Trash operations, copy verification, atomic config | [`vault.py`](../src/keikeu_core/vault.py) | [`test_vault.py`](../tests/test_vault.py) |
| Index | folder-aware rebuildable Paper/index v3 metadata and isolated path/parse errors | [`indexer.py`](../src/keikeu_core/indexer.py) | [`test_indexer.py`](../tests/test_indexer.py) |
| v0.1 migration | preflight, external backup, Paper v3 staging, swap | [`migration_v01.py`](../src/keikeu_core/migration_v01.py) | [`test_migration_v01.py`](../tests/test_migration_v01.py) |
| App shell | Vault/migration identity gates, vault-relative Paper routing, and custom Library scope sidebar | [`main.py`](../src/keikeu_app/main.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Paper UI | create/update with Paper and Highlight names, immutable code, drag/menu ordering, delete, handoff | [`paper_page.py`](../src/keikeu_app/pages/paper_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Flashcard UI | named Summary-first projection, Paper selector, page-1 reset, list/arrow/jump navigation | [`flashcard_page.py`](../src/keikeu_app/pages/flashcard_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Device state | disposable once-per-local-day start-card claim; no Flashcard position | [`local_state.py`](../src/keikeu_app/local_state.py) | [`test_local_state.py`](../tests/test_local_state.py) |
| Library UI | folder scopes, scoped search/sort, selection, drag/menu/batch moves, branch, Trash/recovery, system handoff | [`library_page.py`](../src/keikeu_app/pages/library_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |

The visual dependency and lifecycle view is [architecture.html](architecture/architecture.html).

## Documentation map

```text
README
  └─ PROJECT ── current coordinates and the next gate
       ├─ AUTHORITY ── product / rules / agent procedure
       ├─ VIEWS ────── design / interaction / architecture
       ├─ EVIDENCE ─── tests / acceptance / generated observations
       └─ CONTEXT ──── human manuals / ADRs / read-only archive
```

- **Authority:** [SPEC](SPEC.md) owns product behavior and acceptance; [RULES](RULES.md) owns engineering, interaction, data, Git, and evidence constraints; [AGENTS](../AGENTS.md) owns agent procedure. Runtime facts come from [`src/`](../src/) and [`tests/`](../tests/).
- **Views:** [design](design/design.html) shows v0.3 target visual tokens and component states; [interaction](design/interaction.html) shows target user paths and states; [architecture](architecture/architecture.html) shows target modules, dependencies, and lifecycles. Current implementation evidence remains in `src/`, `tests/`, and this map.
- **Evidence:** [acceptance](acceptance/README.md) holds the completed Phase 8 evidence; the used SOP is archived at its commit baseline. [generated](generated/README.md) holds rebuildable observations; the [cold-start audit](cold_start_report.md) records the Phase 8.5 evidence boundary. None defines intent by itself.
- **Context:** [ADR 0001](architecture/decisions/0001-document-authority.md) explains the authority split; [ADR 0002](architecture/decisions/0002-home-write-boundary.md) fixes the Home write boundary and App Sandbox deferral; [ADR 0003](architecture/decisions/0003-paper-v3-one-level-folders.md) fixes Paper v3 and one-level folders. [Manual](manual/README.md) teaches people; [archive](archive/README.md) preserves superseded records. Neither overrides authority.

## Commands

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/check_docs.py
flet run src/keikeu_app/main.py
```

Application tests must not be inferred from documentation checks. Platform smoke and author acceptance require their own evidence.

## Open gates

1. Create the focused local Phase 6 commit from the reviewed implementation and evidence; do not push or tag.
2. Begin Phase 7 by calibrating `architecture.html`, design, and interaction against the verified implementation before the full candidate workflow.
3. Keep destructive workflow checks on synthetic/copied Vaults and the independent Phase 7.5 iOS build outside every Road v0.3 macOS gate.

## Known candidate, not active scope

The Phase 8 [issue classification](acceptance/phase8.md#issue-分级) records the next-Road candidates. The side navigation's Flashcard destination not retaining the current Paper context remains P2: usable but awkward.

## History boundary

Road v0.1 Cache/Outline behavior, old planning debates, frozen status pages, and the Phase 8.5 proposal live under [archive](archive/README.md). Human explanations live under [manual](manual/README.md). Neither defines current behavior.
