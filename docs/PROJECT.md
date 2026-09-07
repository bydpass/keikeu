# keikeu Project Map

> Authority: current coordinates, module entry points, documentation index, and next gate. Product behavior belongs in [SPEC](SPEC.md); rules belong in [RULES](RULES.md).

Updated: 2026-09-07 (Road v0.8 CP2 shared Core checked; CP3 integration next)

## Current coordinates

| Track | State | Evidence boundary |
| --- | --- | --- |
| Road v0.2 engineering Phases 0–7 | Complete | Paper v2, migration, recovery, macOS UI, Flashcard, Outline retirement, and macOS file-service smoke are implemented and recorded. |
| Road v0.2 Phase 8 product acceptance | Complete | The author completed the real one-shot and two-session short/medium scenarios; no P0/P1 was reported. P2/P3 observations are recorded separately. |
| Phase 7.5 lightweight iOS | Quick-test build complete on an independent branch | Responsive shell and app-sandbox Vault were exercised on `codex/fix-ios-device-readiness`. This is a lightweight iOS version for rapid testing, not a step in the macOS Road sequence. |
| Phase 8.5 / Road v0.3 preparation | Complete | Documentation reform, authority maps, link gate, browser QA, and bounded Graphify trial completed before Road v0.3 construction. The fresh-agent audit remained unperformed and is not retroactively claimed. |
| Road v0.3 | Product accepted; design archive complete | Phase 0–7 engineering, CP5 macOS candidate smoke, and CP6 real-author scenarios are complete. Retrieval was faster and clear, external-editor handoff was clear, and no unresolved P0/P1 was reported. The [version archive](archive/road-v0-3/README.md) is read-only; no v0.3 tag, commit, or push is implied. |
| Road v0.4 | Complete; CP14 accepted | [CP14 evidence](acceptance/road_v0_4_cp14.md) records accepted Flet retirement, Python `234`, Vue `48`, Rust `10`, and the authorized final beta engineering build/launch/relaunch smoke. The one-time exception is consumed; compatibility remains CP13-only evidence. |
| Road v0.5 | Complete; CP7 accepted and Road archived | CP0 `11c2149`, CP1 `a2ff5cb`, CP2 `30b54ac`, CP3 `c7b9caf`, CP4 `371f4e8`, CP5 `1e87ad4`, CP6 `4753d1d`, and CP7 `d900953` form the linear Road. The [CP6 report](acceptance/road-v0-5/cp6-dogfood/report.md) records product acceptance; the [CP7 report](acceptance/road-v0-5/cp7-fixed-sidebars/report.md) records the final UI gate. The [Road snapshot](archive/snapshots/road-v0-5.html) binds the final checkpoint and records scope, checks, QA, omissions, and risks. |
| Road v0.6 | Complete; CP7 accepted and Road archived | Planning approval is `9bb722a`; CP0 `08626a9`, CP1 `cc41eff`, CP2 `8c9dae9`, CP3 `48f88a4`, CP4 `8c0ba33`, CP5 `30f2491`, CP6 `02d8ed5`, and CP7 `18a1024` form the linear Road. [CP7 evidence](acceptance/road-v0-6/cp7-author/report.md) records the de-identified real-author flow, one native-confirmation P1 and its fix/retest, and no remaining P0/P1. The [Road snapshot](archive/snapshots/road-v0-6.html) binds the CP7 checkpoint; tag, push and release remain separate, unperformed decisions. |
| Road v0.7 | Complete; CP8 accepted and Road archived | CP0 `fb52b55`, CP1 `8019969`, CP2 `55d45fc`, CP3 `55b5313`, CP4 `6f69310`, CP5 `3259c42`, CP6 `e22b691`, CP7 `1e17cea`, and CP8 `2f03aee` form the checkpoint ledger. The developer explicitly accepted CP8 and declared Road v0.7 complete on 2026-08-26. The [CP8 report](acceptance/road-v0-7/cp8-responsive-navigation/report.md) separates engineering and developer QA; the [Road snapshot](archive/snapshots/road-v0-7.html) binds the final checkpoint. CP6 completed one bounded real-v4-Vault author Gate and consumed that authorization; no later real-Vault operation, push, tag, signing, package, or release was performed. |
| Post-Road developer tooling | TUI implemented; technical manuals current | `./dev` provides owned-process launch/log control and local document browsing; the [manual index](manual/README.md) now routes to TUI, stack, testing/evidence, and build/packaging guides. The ignored root `CONTEXT.md` is a disposable agent handoff artifact. None changes product UI, protocol, Vault behavior, or acceptance. |
| Road v0.8 | CP2 shared Rust Core accepted under advance YOLO | The developer rolled back the prior CP0–CP4 attempt on 2026-09-07, retaining the accepted [close guard](acceptance/close-guard-2026-09-04.md). The [revised plan](../PLAN_road_v0_8.md) and [change map](architecture/road-v0-8-changes.html) show retained Mac functionality and proposed iPhone/Rust/iCloud work. The old branches are historical attempts, not current code or acceptance evidence. The developer authorized CP0–CP5 with advance YOLO and local checkpoint commits in an isolated worktree. The [CP0 host contract](design/road-v0-8-host-contract.md) freezes the new method ownership. [CP1](acceptance/road-v0-8/cp1-apple.md) proves native probe byte round trips on Mac/iPhone, preservation and relaunch; Tauri iOS builds. [CP2](acceptance/road-v0-8/cp2-core.md) adds reviewed golden parity, pinned local file operations and read-only reconciliation; product integration is still pending. Platform batch A is complete; candidate batch B remains pending. CP5 acceptance still requires all mandatory device/provider evidence. Desktop parity and Python retirement remain an independent prerequisite to external Alpha. |
Phase 8 product acceptance is complete. Road v0.2 is marked by local annotated tag `v0.2.0` at `d0feac0269a5619f5dbf27c04347ba69c5665b42`; archival remains a separate developer decision. Automated tests, platform smoke, and author acceptance remain distinct evidence.
Road v0.3 product decisions, implementation, macOS candidate smoke, and product acceptance are complete. Its detailed SPEC, Planbook, maps, ADRs, and CP6 record are archived. Its accepted Python/Flet runtime served as the Road v0.4 parity baseline until all replacement gates passed; CP14 retires it without changing or migrating Vault data. Road v0.4 CP0 is committed at `8407941` on `codex/road-v04-cp0`; CP1 at `b718ed8`; CP2 at `42dfa68`; CP3 at `e72f155`; CP4 at `0d86847`; CP5 at `f19da31`; CP6 at `b52622f`; CP7 at `067c50c`; CP8 at `f12374c`; CP9 at `2c2df7c`; CP10 at `992f9ca`; CP11 at `908fd85`; and CP12 at `6efd039`. CP13 workflow candidate `a6db6d2` and its macOS 15.7+ evidence were accepted in `4d510cc` on `codex/road-v04-cp13`. CP14 was accepted on 2026-07-26 and completes the Road on `codex/road-v04-cp14`; its checkpoint commit is that branch's HEAD.

## Road v0.4 CP2 evidence

- `.venv/bin/python -m pytest -q` — `286 passed` on 2026-07-25.
- The real Flet runtime rendered an isolated Vault picker for about 10 seconds and exited cleanly on Ctrl-C. This smoke bypassed configured Vault and device state, so it did not touch author data or persistent app state.
- `src/keikeu_app/` has no direct `keikeu_core` import; builder tests now inject and exercise `KeikeuService`.

## Road v0.4 CP3 boundary

- The archived Road v0.4 [`protocol.md`](archive/road-v0-4/protocol.md) records every method, params/result shape, known errors, mutation/retry rule, session token, service mapping, and a manual hello example.
- [`protocol.py`](../src/keikeu_bridge/protocol.py) owns validation and dispatch only; [`sidecar.py`](../src/keikeu_bridge/sidecar.py) owns stdin/stdout only. Neither contains Paper, Vault, Markdown, search, Trash, or migration rules.
- A repeated `system.hello` changes `session_id` and clears transient preview/edit/preflight handles. EOF exits normally; the dispatcher invokes each mutation once and never retries.
- Host timeouts, crash ownership, request queueing, response-loss `commit_unknown`, and child cleanup remain CP4 Rust responsibilities.
- `.venv/bin/python -m pytest -q` completed with `321 passed`; an interactive sidecar hello returned one protocol-v1 response and EOF exited with code `0` on 2026-07-25.

## Road v0.4 CP4 evidence

- Rust owns one sidecar behind a single worker queue. Startup and manual restart perform `system.hello`;
  mutation response loss becomes `commit_unknown` and is never retried.
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
- During CP4 the tracked app minimum was macOS `13.3`, and the approved Xcode
  27 beta workstation failed to load Rust 1.88 proc-macros (`E0463`) at that
  target. A one-run `11.0` override proved assembly only. CP12 supersedes that
  floor with tracked macOS `15.0`; the CP4 `.app` remains non-production evidence.

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
  because the CP4 beta attempt could not compile the then-tracked `13.3`; this
  is neither CP12 nor CP13 evidence.
- No real Vault or persistent workstation state changed; the fixture was
  removed. No permission, dependency, schema, service/Core, or Rust code changed.

## Road v0.4 CP7 evidence

- Historical Road v0.4 CP7 evidence records the then-current read-only card selection, navigation, Summary context, and page-1 reset behavior; that implementation was later retired by Road v0.6.
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
- [CP12 evidence](acceptance/road_v0_4_cp12.md) records the macOS 15.0 production bundle smoke, accepted de-identified real-author A/B, and non-blocking InputMethodKit diagnostic.

## Road v0.6 CP0 toolchain

CP0 observed the approved engineering workstation on 2026-08-02:

| Tool | Observed | CP0 judgment |
| --- | --- | --- |
| Node / npm | `22.23.2` / `10.9.8` | Exact Road v0.6 lock |
| Rust / Cargo | `1.88.0` / `1.88.0` | Exact lock; host `aarch64-apple-darwin` |
| Python | `3.13.15` | Within `>=3.11,<3.14` |
| macOS | `27.0 (26A5388g)`, Apple Silicon | Road v0.6 engineering exception only |
| Xcode | `27.0 (27A5194q)` | Road v0.6 engineering exception only |

The narrow Road v0.6 macOS/Xcode beta policy is recorded in [ADR-0006](architecture/decisions/0006-road-v0-6-beta-engineering-exception.md). It permits engineering only, expires when stable 27 arrives, is not inherited by later betas, and proves neither compatibility nor release readiness. Historical Road v0.4 policy remains in [ADR-0005](architecture/decisions/0005-beta-toolchain-engineering-exception.md).

## Current product flow

```text
accepted:  Road v0.7 CP8 responsive navigation + CP7 continuous flow / whole-folder Trash on unchanged Paper v4 / Index v4 / protocol v2
git:       final checkpoint 2f03aee; independent Road snapshot archived after it
road:      product, implementation, checkpoint and documentation closeout complete; no tag/push/release
next:      CP3 iPhone local creation, host routing, export and draft recovery
```

**Independent close-guard repair accepted, 2026-09-05:** The 2026-08-26 audit found App-root pending intent protected only by a PaperView listener. The current working-tree candidate moves the listener to App, blocks in-flight writes across Paper/Library/Vault, retains unknown-result snapshots, and routes macOS menu Quit through window close. Frontend tests (128), Rust tests (12) and listed native window/response-loss scenarios passed. The developer then manually confirmed that all normal exit paths are protected except force quit, passing the independent prerequisite. The [report and code guide](acceptance/close-guard-2026-09-04.md) separates agent-run coverage from developer manual acceptance and records an unintended tool relaunch that updated the real daily-card state. This is an independent pre-Road repair, not CP0 or a guarantee against force quit, crashes or power loss. The repair is retained in baseline `5ff26fe`.

## Road v0.7 CP5 evidence

Python `265`, Vitest `77`, Rust `12` and every build/format/docs/bundle gate passed. An isolated fake Home and synthetic Vault completed startup, two-page save, Library/Vault, native dirty confirmation, `920×680`, Index, repair and `commit_unknown` no-replay paths in Tauri; `library.branch=1`, exactly two Papers, normal sidecar SHA restoration and zero recorded child residue were verified. This is synthetic engineering/platform evidence, not real-provider or CP6 acceptance; WebView console and native IME were not separately claimed. On 2026-08-21 the developer separately passed CP6; the [CP6 report](acceptance/road-v0-7/cp6-author/report.md) records the Gate-level judgment, de-identified v4/ready/current postflight, unreported detail boundary, clean lifecycle, and Road-extension hold.

## Current runtime map (Paper v4 + protocol v2)

| Area | Responsibility | Source | Direct evidence |
| --- | --- | --- | --- |
| Domain model | Paper v4/CardPage validation; frozen legacy model exists only in the migration module | [`models.py`](../src/keikeu_core/models.py), [`legacy_v3.py`](../src/keikeu_core/legacy_v3.py) | [`test_models_v4.py`](../tests/test_models_v4.py), [`test_migration_v4.py`](../tests/test_migration_v4.py) |
| Markdown | Strict Paper v4 parse/render, exact create/CAS/Branch, plus frozen legacy readers for migration | [`markdown_io.py`](../src/keikeu_core/markdown_io.py), [`legacy_v3.py`](../src/keikeu_core/legacy_v3.py) | [`test_markdown_v4.py`](../tests/test_markdown_v4.py) |
| Vault | Home/path validation, one-level active/Trash enumeration, global code allocation, per-Paper lifecycle, crash-visible whole-folder atomic Trash/restore, identity-pinned fd-relative permanent folder deletion, copy verification, atomic config | [`vault.py`](../src/keikeu_core/vault.py) | [`test_vault.py`](../tests/test_vault.py) |
| Index | rebuildable Index v4, all-page search, first-page preview, page titles, folder/Trash projection and isolated errors | [`indexer.py`](../src/keikeu_core/indexer.py) | [`test_indexer_v4.py`](../tests/test_indexer_v4.py) |
| Migration | explicit v0.1→v3 then v2/v3→v4 preflight, verified backup, loss audit, safe replacement and resume | [`migration_v01.py`](../src/keikeu_core/migration_v01.py), [`migration_v4.py`](../src/keikeu_core/migration_v4.py) | [`test_migration_v01.py`](../tests/test_migration_v01.py), [`test_migration_v4.py`](../tests/test_migration_v4.py) |
| Application service | startup schema Gate, Paper v4 save/reconcile, locator, Library v4, migration, structured errors and validated system targets | [`service.py`](../src/keikeu_bridge/service.py), [`dto.py`](../src/keikeu_bridge/dto.py) | [`test_bridge_service.py`](../tests/test_bridge_service.py) |
| JSONL sidecar | protocol v2 strict DTO/method classification, session-bound tokens, stdin/stdout isolation and one-shot mutations | [`protocol.py`](../src/keikeu_bridge/protocol.py), [`sidecar.py`](../src/keikeu_bridge/sidecar.py) | [`test_bridge_protocol.py`](../tests/test_bridge_protocol.py) |
| Tauri/Rust host | one sidecar, serialized requests, lifecycle cleanup, native directory picker/confirmation, and validated open/reveal | [`lib.rs`](../frontend/src-tauri/src/lib.rs), [`commands.rs`](../frontend/src-tauri/src/commands.rs), [`bridge.rs`](../frontend/src-tauri/src/bridge.rs) | Cargo tests in `bridge.rs`; cargo build checks host/command wiring |
| Vue app shell | startup/Vault/migration gates, App-root pending durable intent and restart ownership; accepted CP8 one-row `56px` Shell. App owns the accepted Tauri close guard; Paper retains dirty/departure checks; see the independent evidence above | [`App.vue`](../frontend/src/App.vue), [`bridge.js`](../frontend/src/bridge.js), [`PaperView.vue`](../frontend/src/PaperView.vue) | [`App.test.js`](../frontend/src/App.test.js), [`bridge.test.js`](../frontend/src/bridge.test.js), [`PaperView.test.js`](../frontend/src/PaperView.test.js) |
| Vue Paper slice | accepted CP7 continuous Paper flow plus accepted CP8 all-page horizontal roller, portrait bounded Markdown field and bottom action Anchor; CSV-style Tags, native details, whole-Paper save, saving lock and dirty departure remain unchanged | [`PaperView.vue`](../frontend/src/PaperView.vue), [`PaperV4Workbench.vue`](../frontend/src/PaperV4Workbench.vue), [`tagsCsv.js`](../frontend/src/tagsCsv.js) | [`PaperView.test.js`](../frontend/src/PaperView.test.js), [`PaperV4Workbench.test.js`](../frontend/src/PaperV4Workbench.test.js), [`tagsCsv.test.js`](../frontend/src/tagsCsv.test.js) |
| Vue Library slice | CP7 composition-safe query/top-layer Paper preview plus accepted CP8 portrait `范围 / 排序` and `新文件夹` sticky Anchors with native Popovers; landscape sidebar, sort and inline creation remain | [`LibraryView.vue`](../frontend/src/LibraryView.vue), [`LibraryV4Projection.vue`](../frontend/src/LibraryV4Projection.vue) | [`LibraryView.test.js`](../frontend/src/LibraryView.test.js), [`LibraryV4Projection.test.js`](../frontend/src/LibraryV4Projection.test.js) |
| Vue Vault/migration slice | Road v0.7 quiet normal context, explicit maintenance entry, native directory intent, candidate locator, relocation/two-stage migration and restart readback | [`VaultView.vue`](../frontend/src/VaultView.vue), [`bridge.js`](../frontend/src/bridge.js) | [`VaultView.test.js`](../frontend/src/VaultView.test.js), [`bridge.test.js`](../frontend/src/bridge.test.js) |
| Device state | disposable once-per-local-day start-card claim; no page position | [`local_state.py`](../src/keikeu_bridge/local_state.py) | [`test_local_state.py`](../tests/test_local_state.py) |

The active [architecture page](architecture/architecture.html) describes the single Vue/Tauri/JSONL/Python runtime. The superseded Road v0.3 Flet lifecycle view is [archived](archive/road-v0-3/architecture/architecture.html).

## Documentation map

```text
README ── PROJECT ── current coordinates and the next gate
       ├─ AUTHORITY ── product / rules / agent procedure
       ├─ VIEWS ────── design / interaction / architecture
       ├─ EVIDENCE ─── tests / acceptance / generated observations
       └─ CONTEXT ──── human manuals / ADRs / ignored task pack / read-only archive
```

- **Authority:** [SPEC](SPEC.md) owns the accepted CP8 product boundary and labels the documented-but-unimplemented cross-platform target plus its explicit CP0 seed Gate; the [Paper v4 design](design/road-v0-6-paper-v4-design.md) owns unchanged grammar/protocol; the [App Shell design](design/road-v0-7-app-shell-design.md) owns CP6 history and the accepted CP7/CP8 matrices; the archived Chinese [Road v0.7 plan](archive/road-v0-7/PLAN_road_v0_7.md) owns its completed Gate order, while the active [Road v0.8 plan](../PLAN_road_v0_8.md) owns the next target Gate order. [RULES](RULES.md) owns implementation discipline; [AGENTS](../AGENTS.md) owns agent procedure. Runtime facts come from [`src/`](../src/) and [`tests/`](../tests/).
- **Views:** [design](design/design.html), [interaction](design/interaction.html), and [architecture](architecture/architecture.html) mirror the accepted CP8 presentation on unchanged Paper v4/Index v4/protocol v2. They do not independently prove Gate D or release.
- **Companion:** the [interactive planbook](design/road-v0-7-planbook.html) presents CP0–CP8 history but remains non-authoritative and is not implementation or Gate evidence.
- **Evidence:** [acceptance](acceptance/README.md) links the passed Road v0.7 [CP0](acceptance/road-v0-7/cp0-contract/report.md), [CP1](acceptance/road-v0-7/cp1-grayscale/report.md), [CP2](acceptance/road-v0-7/cp2-shell/report.md), [CP3](acceptance/road-v0-7/cp3-paper/report.md), [CP4](acceptance/road-v0-7/cp4-library-vault/report.md), [CP5](acceptance/road-v0-7/cp5-integration/report.md), [CP6](acceptance/road-v0-7/cp6-author/report.md), [CP7](acceptance/road-v0-7/cp7-continuous-flow/report.md), and [CP8](acceptance/road-v0-7/cp8-responsive-navigation/report.md) reports plus earlier-Road evidence; archive remains dated history rather than active authority.
- **Context:** [ADR 0001](architecture/decisions/0001-document-authority.md) explains the authority split; [ADR 0008](architecture/decisions/0008-whole-folder-trash-lifecycle.md) records the developer-approved whole-folder Trash exception. Road v0.3 design history, Road v0.4 planning history, and the Road [v0.5](archive/snapshots/road-v0-5.html)/[v0.6](archive/snapshots/road-v0-6.html)/[v0.7](archive/snapshots/road-v0-7.html) construction snapshots are read-only records. [Manual](manual/README.md) teaches people; [archive](archive/README.md) preserves history. The ignored root `CONTEXT.md` contains a reviewed local working-tree route for the next coding task; it is neither authority nor evidence and is never tracked or uploaded by the builder.

## Commands

```bash
./dev  # preferred local developer entry; added 2026-08-29
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/build_sidecar.py
npm --prefix frontend run test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml
npm --prefix frontend run tauri:build
.venv/bin/python scripts/check_docs.py
```

Application tests must not be inferred from documentation checks. Platform smoke and author acceptance require their own evidence.

## Post-Road decisions

Road v0.4–v0.7 are complete. Road v0.7 ends at CP8 checkpoint `2f03aee`; its independent [snapshot](archive/snapshots/road-v0-7.html) records scope, evidence, QA, omissions and risks. Paper v4/Index v4/protocol v2 and the complete-folder lifecycle remain unchanged. CP6 consumed its bounded real-Vault authorization. The independent close-guard smoke report discloses a later tool-induced startup outside the isolated Home; no author mutation was initiated there. Push, tag and release remain unperformed; the temporary development bundle is not distribution evidence. The revised [v0.8 plan](../PLAN_road_v0_8.md) requires an iPhone/Mac sync candidate followed by independent desktop parity and Python product-runtime retirement before the first external Alpha. The current worktree was rolled back to `5ff26fe`; the close guard remains accepted. Review of the new visible plan and explicit restart of engineering are next; no old CP acceptance carries over automatically. Candidate acceptance, unified-core convergence, Road v0.9 first Alpha/promotion, Road v0.10 Android/second Alpha, and the subsequent Windows decision remain separate future gates.

## History boundary

Road v0.1/v0.2 history, Road v0.3 design and acceptance, Road v0.4 planning, Road v0.5–v0.7 construction snapshots, old planning debates, frozen status pages, and the Phase 8.5 proposal live under [archive](archive/README.md). Human explanations live under [manual](manual/README.md). Neither overrides the active SPEC and RULES.
