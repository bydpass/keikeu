# keikeu Project Map

> Authority: current coordinates, module entry points, documentation index, and next gate. Product behavior belongs in [SPEC](SPEC.md); rules belong in [RULES](RULES.md).

Updated: 2026-07-21

## Current coordinates

| Track | State | Evidence boundary |
| --- | --- | --- |
| Road v0.2 engineering Phases 0–7 | Complete | Paper v2, migration, recovery, macOS UI, Flashcard, Outline retirement, and macOS file-service smoke are implemented and recorded. |
| Road v0.2 Phase 8 product acceptance | Complete | The author completed the real one-shot and two-session short/medium scenarios; no P0/P1 was reported. P2/P3 observations are recorded separately. |
| Phase 7.5 lightweight iOS | Quick-test build complete on an independent branch | Responsive shell and app-sandbox Vault were exercised on `codex/fix-ios-device-readiness`. This is a lightweight iOS version for rapid testing, not a step in the macOS Road sequence. |
| Phase 8.5 / Road v0.3 preparation | Documentation reform implemented; review pending | This is the precursor to the next macOS version. Current evidence covers the authority map, HTML maps, archive, link gate, browser QA, and bounded Graphify trial; independent fresh-agent cold start was not run. |

Phase 8 product acceptance is complete. Road archival or tagging remains a separate developer decision after final checks against the candidate commit. Automated tests, platform smoke, and author acceptance remain distinct evidence.

Phase 7.5 and Phase 8.5 are separate tracks: Phase 7.5 is the independent lightweight iOS test version; Phase 8.5 prepares Road v0.3 and the next macOS version. Phase 7.5 is not a merge gate for Phase 8.5.

## Product flow

```text
Paper Markdown → Flashcard → external prose editor
```

See [SPEC](SPEC.md) for the contract and [interaction.html](design/interaction.html) for executable state examples.

## Runtime map

| Area | Responsibility | Source | Direct evidence |
| --- | --- | --- | --- |
| Domain model | Paper validation and normalization | [`models.py`](../src/keikeu_core/models.py) | [`test_models.py`](../tests/test_models.py) |
| Markdown | Paper parse, render, safe update, rename | [`markdown_io.py`](../src/keikeu_core/markdown_io.py) | [`test_markdown_io.py`](../tests/test_markdown_io.py) |
| Vault | initialization, soft delete, restore, config | [`vault.py`](../src/keikeu_core/vault.py) | [`test_vault.py`](../tests/test_vault.py) |
| Index | rebuildable Paper search metadata and errors | [`indexer.py`](../src/keikeu_core/indexer.py) | [`test_indexer.py`](../tests/test_indexer.py) |
| v0.1 migration | preflight, external backup, staging, swap | [`migration_v01.py`](../src/keikeu_core/migration_v01.py) | [`test_migration_v01.py`](../tests/test_migration_v01.py) |
| App shell | Vault gate, routing, desktop/mobile navigation | [`main.py`](../src/keikeu_app/main.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Paper UI | create, update, rename, delete, handoff | [`paper_page.py`](../src/keikeu_app/pages/paper_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Flashcard UI | Summary-first projection and navigation | [`flashcard_page.py`](../src/keikeu_app/pages/flashcard_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Device state | disposable per-device card position | [`local_state.py`](../src/keikeu_app/local_state.py) | [`test_local_state.py`](../tests/test_local_state.py) |
| Library UI | search, health, system open, trash restore | [`library_page.py`](../src/keikeu_app/pages/library_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |

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
- **Views:** [design](design/design.html) shows visual tokens and component states; [interaction](design/interaction.html) shows user paths and states; [architecture](architecture/architecture.html) shows modules, dependencies, and data lifecycles.
- **Evidence:** [acceptance](acceptance/README.md) holds the completed Phase 8 evidence; the used SOP is archived at its commit baseline. [generated](generated/README.md) holds rebuildable observations; the [cold-start audit](cold_start_report.md) records the Phase 8.5 evidence boundary. None defines intent by itself.
- **Context:** [ADR 0001](architecture/decisions/0001-document-authority.md) explains this split; [manual](manual/README.md) teaches people; [archive](archive/README.md) preserves superseded records. Manual and archive never override authority.

## Commands

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/check_docs.py
flet run src/keikeu_app/main.py
```

Application tests must not be inferred from documentation checks. Platform smoke and author acceptance require their own evidence.

## Open gates

1. Review the Phase 8.5 documentation diff; optionally authorize an independent fresh-agent run to strengthen the structural [cold-start audit](cold_start_report.md).
2. Run final tests, compile, documentation checks, diff checks, and a macOS candidate-build smoke.
3. Review the Phase 8 [P2/P3 candidates](acceptance/phase8.md#issue-分级) as Road v0.3 inputs without widening v0.2, then decide whether to archive/tag the Road.
4. Define the minimum Phase 8.5 scope for the next macOS version; keep the independent Phase 7.5 iOS test build outside that gate.

## Known candidate, not active scope

The Phase 8 [issue classification](acceptance/phase8.md#issue-分级) records the next-Road candidates. The side navigation's Flashcard destination not retaining the current Paper context remains P2: usable but awkward.

## History boundary

Road v0.1 Cache/Outline behavior, old planning debates, frozen status pages, and the Phase 8.5 proposal live under [archive](archive/README.md). Human explanations live under [manual](manual/README.md). Neither defines current behavior.
