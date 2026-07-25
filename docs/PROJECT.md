# keikeu Project Map

> Authority: current coordinates, module entry points, documentation index, and next gate. Product behavior belongs in [SPEC](SPEC.md); rules belong in [RULES](RULES.md).

Updated: 2026-07-25

## Current coordinates

| Track | State | Evidence boundary |
| --- | --- | --- |
| Road v0.2 engineering Phases 0–7 | Complete | Paper v2, migration, recovery, macOS UI, Flashcard, Outline retirement, and macOS file-service smoke are implemented and recorded. |
| Road v0.2 Phase 8 product acceptance | Complete | The author completed the real one-shot and two-session short/medium scenarios; no P0/P1 was reported. P2/P3 observations are recorded separately. |
| Phase 7.5 lightweight iOS | Quick-test build complete on an independent branch | Responsive shell and app-sandbox Vault were exercised on `codex/fix-ios-device-readiness`. This is a lightweight iOS version for rapid testing, not a step in the macOS Road sequence. |
| Phase 8.5 / Road v0.3 preparation | Complete | Documentation reform, authority maps, link gate, browser QA, and bounded Graphify trial completed before Road v0.3 construction. The fresh-agent audit remained unperformed and is not retroactively claimed. |
| Road v0.3 | Product accepted; design archive complete | Phase 0–7 engineering, CP5 macOS candidate smoke, and CP6 real-author scenarios are complete. Retrieval was faster and clear, external-editor handoff was clear, and no unresolved P0/P1 was reported. The [version archive](archive/road-v0-3/README.md) is read-only; no v0.3 tag, commit, or push is implied. |
| Next Road | Not in implementation | Active visual, interaction, and architecture pages are transition boundaries. Implementation waits for an approved SPEC, Planbook, maps, and matching RULES updates. |

Phase 8 product acceptance is complete. Road v0.2 is marked by local annotated tag `v0.2.0` at `d0feac0269a5619f5dbf27c04347ba69c5665b42`; archival remains a separate developer decision. Automated tests, platform smoke, and author acceptance remain distinct evidence.

Phase 7.5 and the macOS Roads are separate tracks. The lightweight iOS test version is not a merge gate for the next macOS Road.

Road v0.3 product decisions, implementation, macOS candidate smoke, and product acceptance are complete. Its detailed SPEC, Planbook, maps, ADRs, and CP6 record are archived. The accepted Python/Flet runtime remains available until a separately approved Road replaces it; archival does not authorize runtime removal or data migration.

## Product flow

```text
Paper Markdown → Flashcard → external prose editor
```

See [SPEC](SPEC.md) for the stable product boundary. The accepted Road v0.3 interaction detail is historical and lives in its [archive](archive/road-v0-3/design/interaction.html).

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

The active [architecture page](architecture/architecture.html) records the transition boundary; the implemented Road v0.3 lifecycle view is [archived](archive/road-v0-3/architecture/architecture.html).

## Documentation map

```text
README
  └─ PROJECT ── current coordinates and the next gate
       ├─ AUTHORITY ── product / rules / agent procedure
       ├─ VIEWS ────── design / interaction / architecture
       ├─ EVIDENCE ─── tests / acceptance / generated observations
       └─ CONTEXT ──── human manuals / ADRs / read-only archive
```

- **Authority:** [SPEC](SPEC.md) preserves stable product and author-control boundaries during the Road transition; [RULES](RULES.md) owns engineering, interaction, data, Git, and evidence constraints; [AGENTS](../AGENTS.md) owns agent procedure. Runtime facts come from [`src/`](../src/) and [`tests/`](../tests/).
- **Views:** [design](design/design.html), [interaction](design/interaction.html), and [architecture](architecture/architecture.html) currently state that the next Road is not active. They must be replaced only by an approved Road.
- **Evidence:** [acceptance](acceptance/README.md) links completed Road v0.2 evidence and the archived Road v0.3 CP6 record. The frozen [2cc40ba status snapshot](archive/snapshots/feat-complete-road-v0-3-candidate.html) shows the earlier CP5 boundary. [generated](generated/README.md) remains rebuildable observation; the [cold-start audit](cold_start_report.md) is dated historical evidence, not a claim about the transition pages.
- **Context:** [ADR 0001](architecture/decisions/0001-document-authority.md) explains the authority split. Road v0.3 ADR 0002/0003 and its design set live in the [version archive](archive/road-v0-3/README.md). [Manual](manual/README.md) teaches people; [archive](archive/README.md) preserves superseded records. Neither overrides authority.

## Commands

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/check_docs.py
flet run src/keikeu_app/main.py
```

Application tests must not be inferred from documentation checks. Platform smoke and author acceptance require their own evidence.

## Open gates

1. Approve the next Road's active SPEC, Planbook, visual map, interaction map, architecture map, and required RULES changes.
2. Keep the accepted Python/Flet runtime until the replacement Road reaches its own parity and real-author acceptance gate.
3. Treat tag, commit, push, signing, distribution, and any real-Vault migration as separate developer decisions.

## Known candidate, not active scope

The Phase 8 [issue classification](acceptance/phase8.md#issue-分级) records the next-Road candidates. The side navigation's Flashcard destination not retaining the current Paper context remains P2: usable but awkward.

## History boundary

Road v0.1/v0.2 history, Road v0.3 design and acceptance, old planning debates, frozen status pages, and the Phase 8.5 proposal live under [archive](archive/README.md). Human explanations live under [manual](manual/README.md). Neither defines current or future Road behavior.
