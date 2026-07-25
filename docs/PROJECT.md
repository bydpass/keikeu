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
| Road v0.4 | CP2 — Flet adapter rewired | The runnable Flet baseline now routes startup/Vault, Paper, Flashcard, Library, migration, and validated system actions through `KeikeuService`; no Flet module imports `keikeu_core`. CP3 JSONL work is next, while Vue/Tauri manifests remain blocked on stable tooling and dependency approval. |

Phase 8 product acceptance is complete. Road v0.2 is marked by local annotated tag `v0.2.0` at `d0feac0269a5619f5dbf27c04347ba69c5665b42`; archival remains a separate developer decision. Automated tests, platform smoke, and author acceptance remain distinct evidence.

Phase 7.5 and the macOS Roads are separate tracks. The lightweight iOS test version is not a merge gate for the next macOS Road.

Road v0.3 product decisions, implementation, macOS candidate smoke, and product acceptance are complete. Its detailed SPEC, Planbook, maps, ADRs, and CP6 record are archived. The accepted Python/Flet runtime remains available until a separately approved Road replaces it; archival does not authorize runtime removal or data migration.

Road v0.4 CP0 is committed at `8407941` on `codex/road-v04-cp0`; CP1 is committed at `b718ed8` on `codex/road-v04-cp1`; CP2 is implemented on `codex/road-v04-cp2`. Each checkpoint uses its own `codex/road-v04-cpN` branch created from the previous accepted checkpoint.

## Road v0.4 CP2 evidence

- `.venv/bin/python -m pytest -q` — `286 passed` on 2026-07-25.
- The real Flet runtime rendered an isolated Vault picker for about 10 seconds and exited cleanly on Ctrl-C. This smoke bypassed configured Vault and device state, so it did not touch author data or persistent app state.
- `src/keikeu_app/` has no direct `keikeu_core` import; builder tests now inject and exercise `KeikeuService`.

## Road v0.4 CP0 toolchain observation

Observed on 2026-07-25; these are facts, not an approved lock:

| Tool | Observed | CP0 judgment |
| --- | --- | --- |
| Node / npm | `22.23.1` / `10.9.8` | Stable candidate; not locked |
| Rust / Cargo | `1.83.0` / `1.83.0` | Stable candidate; host `aarch64-apple-darwin`; not locked |
| Python / PyInstaller | `3.13.14` / not installed | Python candidate only; build dependency not approved |
| macOS | `27.0 (26A5388g)`, arm64 | Beta; prohibited for the production Road environment |
| Xcode | `27.0 (27A5194q)` from `Xcode-beta.app` | Beta; no stable Xcode installation found |

No version file, manifest, lockfile, package, or selected developer directory changed. CP0 cannot freeze the production toolchain until a stable macOS/Xcode environment is available or the developer explicitly revises the Road rule.

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
| Application service | UI-neutral startup/Vault, Paper, Flashcard, Library, migration, structured errors, DTOs, and validated system targets | [`service.py`](../src/keikeu_bridge/service.py), [`dto.py`](../src/keikeu_bridge/dto.py) | [`test_bridge_service.py`](../tests/test_bridge_service.py) |
| App shell | Vault/migration identity gates, vault-relative Paper routing, and custom Library scope sidebar | [`main.py`](../src/keikeu_app/main.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Paper UI | create/update with Paper and Highlight names, immutable code, drag/menu ordering, delete, handoff | [`paper_page.py`](../src/keikeu_app/pages/paper_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Flashcard UI | named Summary-first projection, Paper selector, page-1 reset, list/arrow/jump navigation | [`flashcard_page.py`](../src/keikeu_app/pages/flashcard_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Device state | disposable once-per-local-day start-card claim; no Flashcard position | [`local_state.py`](../src/keikeu_bridge/local_state.py); Flet compatibility import remains | [`test_local_state.py`](../tests/test_local_state.py) |
| Library UI | folder scopes, scoped search/sort, selection, drag/menu/batch moves, branch, Trash/recovery, system handoff | [`library_page.py`](../src/keikeu_app/pages/library_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |

The active [architecture page](architecture/architecture.html) distinguishes the accepted current Flet runtime from the approved Road v0.4 target; the implemented Road v0.3 lifecycle view is [archived](archive/road-v0-3/architecture/architecture.html).

## Documentation map

```text
README
  └─ PROJECT ── current coordinates and the next gate
       ├─ AUTHORITY ── product / rules / agent procedure
       ├─ VIEWS ────── design / interaction / architecture
       ├─ EVIDENCE ─── tests / acceptance / generated observations
       └─ CONTEXT ──── human manuals / ADRs / read-only archive
```

- **Authority:** [SPEC](SPEC.md) owns Road v0.4 product scope; [RULES](RULES.md) owns engineering, interaction, data, Git, and evidence constraints; the [Planbook](../PLAN_revised.md) owns execution order; the [understanding gate](../RULE_FOR_UNDERSTANDING.md) owns checkpoint teaching; [AGENTS](../AGENTS.md) owns agent procedure. Runtime facts come from [`src/`](../src/) and [`tests/`](../tests/).
- **Views:** [design](design/design.html), [interaction](design/interaction.html), and [architecture](architecture/architecture.html) describe the approved Road v0.4 target and label the current Flet implementation separately.
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

1. Start CP3 on `codex/road-v04-cp3` from the accepted CP2 HEAD; add the JSONL dispatcher, handshake, session-bound handles, and contract tests without creating frontend/Rust manifests.
2. Provide a stable macOS/Xcode environment, then approve exact Node, Rust, Python build, Vue, Tauri, test, and PyInstaller versions before CP4 creates frontend/Rust manifests or lockfiles.
3. Treat tag, push, signing, distribution, and any real-Vault operation as separate developer decisions.

## Known candidate, not active scope

The Phase 8 [issue classification](acceptance/phase8.md#issue-分级) records the next-Road candidates. The side navigation's Flashcard destination not retaining the current Paper context remains P2: usable but awkward.

## History boundary

Road v0.1/v0.2 history, Road v0.3 design and acceptance, old planning debates, frozen status pages, and the Phase 8.5 proposal live under [archive](archive/README.md). Human explanations live under [manual](manual/README.md). Neither overrides the active Road v0.4 authority.
