# keikeu Project Map

> Authority: current coordinates, module entry points, documentation index, and next gate. Product behavior belongs in [SPEC](SPEC.md); rules belong in [RULES](RULES.md).

Updated: 2026-07-26

## Current coordinates

| Track | State | Evidence boundary |
| --- | --- | --- |
| Road v0.2 engineering Phases 0–7 | Complete | Paper v2, migration, recovery, macOS UI, Flashcard, Outline retirement, and macOS file-service smoke are implemented and recorded. |
| Road v0.2 Phase 8 product acceptance | Complete | The author completed the real one-shot and two-session short/medium scenarios; no P0/P1 was reported. P2/P3 observations are recorded separately. |
| Phase 7.5 lightweight iOS | Quick-test build complete on an independent branch | Responsive shell and app-sandbox Vault were exercised on `codex/fix-ios-device-readiness`. This is a lightweight iOS version for rapid testing, not a step in the macOS Road sequence. |
| Phase 8.5 / Road v0.3 preparation | Complete | Documentation reform, authority maps, link gate, browser QA, and bounded Graphify trial completed before Road v0.3 construction. The fresh-agent audit remained unperformed and is not retroactively claimed. |
| Road v0.3 | Product accepted; design archive complete | Phase 0–7 engineering, CP5 macOS candidate smoke, and CP6 real-author scenarios are complete. Retrieval was faster and clear, external-editor handoff was clear, and no unresolved P0/P1 was reported. The [version archive](archive/road-v0-3/README.md) is read-only; no v0.3 tag, commit, or push is implied. |
| Road v0.4 | CP11 Gate B accepted; CP12 next | Gate B evidence covers shared tokens, four-width browser QA, fixed functional rails, and a uniquely identified `.app` across all four current surfaces. |

Phase 8 product acceptance is complete. Road v0.2 is marked by local annotated tag `v0.2.0` at `d0feac0269a5619f5dbf27c04347ba69c5665b42`; archival remains a separate developer decision. Automated tests, platform smoke, and author acceptance remain distinct evidence.

Phase 7.5 and the macOS Roads are separate tracks. The lightweight iOS test version is not a merge gate for the next macOS Road.

Road v0.3 product decisions, implementation, macOS candidate smoke, and product acceptance are complete. Its detailed SPEC, Planbook, maps, ADRs, and CP6 record are archived. The accepted Python/Flet runtime remains available until a separately approved Road replaces it; archival does not authorize runtime removal or data migration.

Road v0.4 CP0 is committed at `8407941` on `codex/road-v04-cp0`; CP1 at `b718ed8`; CP2 at `42dfa68`; CP3 at `e72f155`; CP4 at `0d86847`; CP5 at `f19da31`; CP6 at `b52622f`; CP7 at `067c50c`; CP8 at `f12374c`; CP9 at `2c2df7c`; and CP10 at `992f9ca`. CP11 Gate B is developer-accepted on `codex/road-v04-cp11`; CP12 starts only from its resulting focused commit.

## Road v0.4 CP2 evidence

- `.venv/bin/python -m pytest -q` — `286 passed` on 2026-07-25.
- The real Flet runtime rendered an isolated Vault picker for about 10 seconds and exited cleanly on Ctrl-C. This smoke bypassed configured Vault and device state, so it did not touch author data or persistent app state.
- `src/keikeu_app/` has no direct `keikeu_core` import; builder tests now inject and exercise `KeikeuService`.

## Road v0.4 CP3 boundary

- [`protocol.md`](protocol.md) records every method, params/result shape, known errors, mutation/retry rule, session token, service mapping, and a manual hello example.
- [`protocol.py`](../src/keikeu_bridge/protocol.py) owns validation and dispatch only; [`sidecar.py`](../src/keikeu_bridge/sidecar.py) owns stdin/stdout only. Neither contains Paper, Vault, Markdown, search, Trash, or migration rules.
- A repeated `system.hello` changes `session_id` and clears transient preview/edit/preflight handles. EOF exits normally; the dispatcher invokes each mutation once and never retries.
- Host timeouts, crash ownership, request queueing, response-loss `commit_unknown`, and child cleanup remain CP4 Rust responsibilities.
- `.venv/bin/python -m pytest -q` completed with `321 passed`; an interactive sidecar hello returned one protocol-v1 response and EOF exited with code `0` on 2026-07-25.

## Road v0.4 CP4 evidence

- Rust owns one sidecar behind a single worker queue. Startup and manual restart
  perform `system.hello`; mutation response loss becomes `commit_unknown` and
  is never retried.
- Vue receives only runtime status, structured bridge results, a directory
  picker, and validated open/reveal. Its capability grants no shell, dialog, or
  opener plugin permission; Rust exposes five explicit commands.
- `cargo test` completed with `10 passed`; Python remained at `321 passed`;
  Vitest completed with `2 passed`; Vite and documentation checks passed.
- A PyInstaller arm64 sidecar returned a protocol-v1 hello. Tauri dev and a
  provisional arm64 `.app` each started the packaged sidecar, and both host and
  child exited without residue after the smoke.
- `npm audit --omit=dev` reported zero production vulnerabilities. The complete
  development tree reports six high findings through the Vue test-utils
  formatting dependency chain; approved direct versions and lockfiles were not
  silently changed.
- The tracked app minimum remains macOS `13.3`. On the approved Xcode 27 beta
  workstation, standard release compilation at that deployment target fails to
  load Rust 1.88 proc-macros (`E0463`). A one-run `11.0` config override proved
  bundle assembly only; that `.app` is not production or CP13 evidence.

## Road v0.4 CP5 review evidence

- The editorial-workbench specimen uses synthetic in-memory Papers only. It
  never invokes the bridge and labels itself as disconnected from the Vault.
- The specimen is loaded through a development-only dynamic import at
  `?prototype=1`. The production bundle contains neither the specimen text nor
  its scoped CSS.
- Vitest completed with `5 passed`; the production Vite build and
  `git diff --check` passed.
- Browser checks at 1220×780, 920×680, 768×800, and 375×812 found no horizontal
  overflow or console warning/error. Search, Paper selection, and Highlight
  move-up worked with local state only.
- Form controls have labels, buttons have accessible names, landmarks are
  present, IDs are unique, and the reviewed text color pairs range from 5.41:1
  to 15.48:1 contrast.
- No historical screenshot baseline exists, so automated evidence did not
  approve taste. The developer reviewed and approved the rendered direction on
  2026-07-25; the tokens and layout rules are frozen for Gate A.

## Road v0.4 CP6 evidence

- [`PaperView.vue`](../frontend/src/PaperView.vue) owns visible Paper state but
  never files; Vue returns opaque `edit_token`, never parses Markdown or retries
  mutations. Startup and migration gates remain blocking.
- Vitest `15`, Python `321`, Rust `10`, compileall, Vite build, responsive
  browser QA, labels/IDs, and console checks passed.
- An isolated `.app` plus packaged sidecar covered daily-card entry, create/save,
  list/open, frozen initial Summary, keyboard Highlight reorder,
  `stale_snapshot`, `not_found`, soft delete, and clean host/child exit.
- The smoke used the documented one-run `minimumSystemVersion=11.0` override
  because beta cannot compile tracked `13.3`; this is neither CP12 nor CP13.
- No real Vault or persistent workstation state changed; the fixture was
  removed. No permission, dependency, schema, service/Core, or Rust code changed.

## Road v0.4 CP7 evidence

- [`FlashcardView.vue`](../frontend/src/FlashcardView.vue) keeps selection, navigation, Summary context, and position in memory; every open resets page 1.
- Vitest `21`, Vite build, responsive browser QA, accessibility, console, and return-to-Paper checks passed; no real Vault or native `.app` was used.

## Road v0.4 CP8–CP11 review evidence

- CP8 accepted Python-sorted query state, Trash isolation, system handoff, and responsive Library QA; its checkpoint commit is `f12374c`.
- CP9 adds one-shot Library mutations with partial-result handling and explicit permanent-delete gates, plus Vault preview/init/switch/relocate and migration.
- Vitest `48`, Python `321`, Rust `10`, compileall, Vite build, and four-width
  browser QA passed; labels, IDs, landmarks, console, and overflow checks passed.
- `tauri dev` rebuilt and launched the current Rust host in an isolated Home.
  macOS automation selected a stale registered release bundle for inspection,
  so no current-source native functional UI smoke is claimed.
- [CP10 Gate A evidence](acceptance/road_v0_4_cp10.md) maps the accepted Flet baseline to Python `321`, Vue `48`, Rust `10`, and current-source `.app` synthetic/copied-Vault smoke. No P0/P1 or product-code change was found.
- [CP11 Gate B evidence](acceptance/road_v0_4_cp11.md) records the accepted shared visual tokens, fixed functional rails, 5.41:1–15.48:1 contrast, four-width browser QA, visible keyboard focus, and a unique `.app` smoke across Vault, Paper, Flashcard, and Library.

## Road v0.4 toolchain

CP0 observed the workstation before approval:

| Tool | Observed | CP0 judgment |
| --- | --- | --- |
| Node / npm | `22.23.1` / `10.9.8` | Stable candidate; not locked |
| Rust / Cargo | `1.83.0` / `1.83.0` | Stable candidate; host `aarch64-apple-darwin`; insufficient for the resolved dependency graph |
| Python / PyInstaller | `3.13.14` / not installed | Python candidate only; build dependency not approved |
| macOS | `27.0 (26A5388g)`, arm64 | Beta; prohibited for the production Road environment |
| Xcode | `27.0 (27A5194q)` from `Xcode-beta.app` | Beta; no stable Xcode installation found |

The developer approved exact Road v0.4 dependencies and the current beta
macOS/Xcode workstation for CP4–CP12 engineering on 2026-07-25. This narrow
exception is recorded in [ADR-0005](architecture/decisions/0005-beta-toolchain-engineering-exception.md);
it does not satisfy the CP13 macOS 13.3+ compatibility gate. CP4 now locks
Node/npm `22.23.1`/`10.9.8`, Rust/Cargo `1.88.0`/`1.88.0`,
Python/PyInstaller `3.13.14`/`6.21.0`, and target
`aarch64-apple-darwin`.

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
| Vue Paper slice | Startup/daily gate, Paper DTO form, initial copy, keyboard save, Highlight ordering, soft delete, and structured recovery through the Tauri bridge | [`PaperView.vue`](../frontend/src/PaperView.vue), [`bridge.js`](../frontend/src/bridge.js) | [`PaperView.test.js`](../frontend/src/PaperView.test.js), [`bridge.test.js`](../frontend/src/bridge.test.js) |
| Flashcard UI | named Summary-first projection, Paper selector, page-1 reset, list/arrow/jump navigation | [`flashcard_page.py`](../src/keikeu_app/pages/flashcard_page.py) | [`test_app_pages.py`](../tests/test_app_pages.py) |
| Vue Flashcard slice | read-only Summary-first projection, in-memory navigation/reset, Summary context, and selected-Paper return | [`FlashcardView.vue`](../frontend/src/FlashcardView.vue), [`App.vue`](../frontend/src/App.vue) | [`FlashcardView.test.js`](../frontend/src/FlashcardView.test.js), [`App.test.js`](../frontend/src/App.test.js) |
| Vue Library slice | Python-owned query/mutation results, local selection, partial failures, folder/Trash gates, and validated system handoff | [`LibraryView.vue`](../frontend/src/LibraryView.vue), [`App.vue`](../frontend/src/App.vue) | [`LibraryView.test.js`](../frontend/src/LibraryView.test.js), [`App.test.js`](../frontend/src/App.test.js) |
| Vue Vault/migration slice | Native directory intent, opaque preview/preflight tokens, explicit relocation/migration confirmation, and blocking unknown-commit recovery | [`VaultView.vue`](../frontend/src/VaultView.vue), [`bridge.js`](../frontend/src/bridge.js) | [`VaultView.test.js`](../frontend/src/VaultView.test.js), [`bridge.test.js`](../frontend/src/bridge.test.js) |
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

- **Authority:** [SPEC](SPEC.md) owns Road v0.4 product scope; [RULES](RULES.md) owns engineering, interaction, data, Git, and evidence constraints; the [Planbook](../PLAN_revised.md) owns execution order; the [understanding gate](../RULE_FOR_UNDERSTANDING.md) owns checkpoint teaching; [AGENTS](../AGENTS.md) owns agent procedure. The [JSONL protocol](protocol.md) records the active local transport contract. Runtime facts come from [`src/`](../src/) and [`tests/`](../tests/).
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

1. Complete CP12 real-author scenarios and production bundle smoke.
2. Keep CP13 macOS 13.3+ compatibility separate from beta-workstation engineering evidence.
3. Treat tag, push, signing, distribution, and any real-Vault operation as separate developer decisions.

## History boundary

Road v0.1/v0.2 history, Road v0.3 design and acceptance, old planning debates, frozen status pages, and the Phase 8.5 proposal live under [archive](archive/README.md). Human explanations live under [manual](manual/README.md). Neither overrides the active Road v0.4 authority.
