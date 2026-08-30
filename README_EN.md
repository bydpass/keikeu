# keikeu

> A local-first fanfiction writing utility that turns existing inspiration into durable, editable card-page Markdown Papers.

[简体中文](README.md) | English

## Current status

Road v0.6 is complete and archived: production uses Paper v4, Index v4, and protocol v2; the Paper itself is the ordered editable card-page artifact. The obsolete normal-runtime chain is gone, the unknown-result and manual-repair gate passed, and the first-author gate passed with no unresolved P0/P1.

Road v0.7 passed CP0–CP8. On 2026-08-26 the developer completed the physical-keyboard macOS native-candidate-window check, passed CP8 Gate D, and explicitly declared Road v0.7 product and implementation work complete. Paper v4, Index v4, and protocol v2 remain unchanged. Final checkpoint `2f03aee` is bound by the independent [Road snapshot](docs/archive/snapshots/road-v0-7.html). CP6 completed one bounded real-v4-Vault author gate and consumed that authorization; no later real-Vault operation, push, tag, signing, packaging, or release was performed. The Road v0.8 [cross-platform direction and documentation draft](PLAN_road_v0_8.md) is approved for this synchronization, but an executable CP0 seed is not approved and the Road has not started. The existing close-guard deviation must first be fixed narrowly and reverified independently rather than hidden inside the cross-platform work.

The product documentation and source were rechecked against the completed Road v0.7 baseline on 2026-08-26. That audit found that normal-close protection for the App-root pending intent is still scoped to `PaperView`; this is an implementation deviation, not a change to the accepted design contract, and [PROJECT](docs/PROJECT.md) records it as an independent blocker before Road v0.8 starts. A separate developer TUI and four technical manuals were added on 2026-08-29; the local handoff route moved to root `CONTEXT.md` on 2026-08-30. These developer tools do not change the product UI, runtime chain, or acceptance state.

Phase 7.5 is an independent lightweight iOS build for rapid testing. Its responsive UI, app-sandbox Vault, and on-device fixes are complete on a separate branch; it is not a merge gate in the macOS Road. Road v0.3 engineering, macOS candidate smoke, and CP6 real-author acceptance are complete: retrieval was faster and clear, the external-editor handoff was clear, and no unresolved P0/P1 was reported. Its design and acceptance records are now [read-only history](docs/archive/road-v0-3/README.md); no v0.3 tag was created. Road v0.4 Gate A, Gate B, product acceptance, and macOS 15.7+ compatibility have passed. The only desktop runtime is now Vue/Tauri with a local Python sidecar; Flet was retired in CP14. Road v0.5 is also complete and archived: Paper Desk, save baselines, departure protection, Flashcard/Library continuity, the whole-app Quiet Desk visual system, and fixed scrolling behavior are accepted. See [PROJECT](docs/PROJECT.md) for live coordinates.

## Current runtime flow

```text
existing inspiration → edit and save a card-page Paper → external prose editor
```

- **Paper:** at least one ordered card page; the page title is always editable, content is author Markdown, and type is Summary/Snapshot/Whisper or empty; save commits the whole Paper once.
- **Library:** searches the whole Paper and sorts by all/unfiled/one-level-folder scope, with single-Paper move, branching, Trash, and restore; drag, multi-select, and batch move are not implemented.
- **Vault:** selects paths only under the current user's Home, validates before switching, and byte-verifies copied unsafe legacy Vaults; Apple App Sandbox is not enabled yet.
- **External editor:** prose always remains outside keikeu.

See [PROJECT](docs/PROJECT.md) for the accepted CP8 composition, evidence layers, and Road closeout boundary.

## Road v0.3 archive

The [final CP6 record](docs/archive/road-v0-3/acceptance/road_v0_3.md) is stored with the product, visual, interaction, architecture, ADR, and Planbook records in the [version archive](docs/archive/road-v0-3/README.md). Archival does not change the Vault, runtime, or Git history.

## Road v0.4 completion record

The [CP14 acceptance record](docs/acceptance/road_v0_4_cp14.md), [planning archive](docs/archive/road-v0-4/README.md), and [complete construction snapshot](docs/archive/snapshots/refactor-retire-flet-after-road-v0-4-acceptance.html) preserve CP0–CP14, the architecture migration, gates, fixes, test evolution, and compatibility evidence.

## Road v0.5 completion record

The [Road v0.5 construction snapshot](docs/archive/snapshots/road-v0-5.html) binds final checkpoint `d900953` and records CP0–CP7 branches, commits, scope, changes, checks, QA, omissions, and risks. Road v0.5 is complete and archived. No tag or push was created; signing, notarization, DMG packaging, and public distribution remain separate decisions.

## Road v0.6 completion record

The [Road v0.6 construction snapshot](docs/archive/snapshots/road-v0-6.html) binds final checkpoint `18a1024` and records the Paper v4 contract, Core, migration, UI, vertical cutover, safety gate, and real-author acceptance evidence. The Road is closed; no tag, push, or release claim was created.

## Road v0.7 completion record

The [Road v0.7 construction snapshot](docs/archive/snapshots/road-v0-7.html) binds final checkpoint `2f03aee` and records CP0–CP8, continuous editing flow, responsive anchors, Figma alignment, and physical-keyboard native IME evidence. The Road is complete and archived; no tag, push, signing, package, or release was created.

## Product principles

- Local-first; Markdown is the author asset and the JSON index is rebuildable.
- Never silently rewrite, overwrite, upload, or judge author text.
- No keikeu accounts, cloud backend, telemetry, or keikeu-managed background sync.
- The current desktop runtime may select OS-exposed folders such as iCloud Drive as ordinary paths; the planned shared iCloud Documents Vault is not implemented.
- No fandom database, AI ghostwriting, community, or built-in prose editor.

Stable product boundaries live in [SPEC](docs/SPEC.md); reviewable constraints live in [RULES](docs/RULES.md).

## Development

Python `>=3.11,<3.14`, Node/npm `22.23.2`/`10.9.8`, and Rust/Cargo
`1.88.0` are required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip install -r requirements-build.lock
npm --prefix frontend ci
./dev
.venv/bin/python scripts/build_sidecar.py
npm --prefix frontend run tauri:dev
```

Use `./dev` for daily work: press `a` to reuse the sidecar or `b` to rebuild
before launch. It also shows owned-process logs and local docs; the final two
commands remain available for direct troubleshooting.

## Repository map

```text
README.md                 public entry and real commands
dev                       developer TUI for launch, process logs, and local docs
AGENTS.md                 agent operating discipline and read order
docs/PROJECT.md           current coordinates, module entry points, next gate
docs/SPEC.md              accepted CP8 boundary and unimplemented cross-platform target
docs/RULES.md             engineering, interaction, data, and evidence rules
docs/design/              CP8-accepted visual and interaction maps and design
docs/architecture/        current/target architecture map and ADRs
docs/acceptance/          supporting evidence; not an independent status source
docs/manual/              supplementary human guides; never normative
docs/archive/             read-only history; excluded from cold starts
docs/archive/road-v0-4/   Road v0.4 planning and understanding-gate archive
CONTEXT.md                ignored local agent route; never authoritative
src/keikeu_core/          pure-Python domain and file logic
src/keikeu_bridge/        application service, JSONL protocol, and sidecar
frontend/                 Vue/Vite UI and Tauri/Rust host
tests/                    verifiable implementation facts
```

Hard rule: `keikeu_core` must not depend on any GUI or transport. Only the core
layer owns Markdown I/O.

## Documentation entry points

| Question | Single entry point |
| --- | --- |
| Stable product purpose and author-control boundary | [SPEC](docs/SPEC.md) |
| Current state and next gate | [PROJECT](docs/PROJECT.md) |
| Rules a change must obey | [RULES](docs/RULES.md) |
| Current architecture | [Architecture map](docs/architecture/architecture.html) |
| Current Road v0.7 interface visual specification | [Design map](docs/design/design.html) |
| Current Road v0.7 interface interaction specification | [Interaction map](docs/design/interaction.html) |
| How agents work | [AGENTS](AGENTS.md) |
| Human-facing development, design, Git, and ethics guides | [Human manuals](docs/manual/README.md) |
| Historical rationale and snapshots | [Archive](docs/archive/README.md) |

## Route

```text
v0.1        archived macOS Cache / Outline pre-alpha
v0.2        macOS Paper / Flashcard Core; product accepted, local annotated tag v0.2.0, archive separate
Phase 7.5   independent lightweight iOS rapid-test build
Phase 8.5   Road v0.3 preparation; precursor to the next Mac version
Road v0.3   macOS Paper Library; CP6 product accepted, design and acceptance records archived
Road v0.4   Vue/Tauri frontend replacement complete; CP14 accepted
Road v0.5   Quiet Desk UI and interaction closeout complete; CP7 accepted and archived
Road v0.6   Paper v4 card-page reconstruction; CP7 accepted and archived
Road v0.7   CP8 accepted and archived; final checkpoint 2f03aee
Road v0.8   cross-platform foundations + iPhone test candidate; direction documented, CP0 seed unapproved; close-guard fix/recheck first
Road v0.9   iOS/macOS first Alpha + formal-promotion Gate; not started
Road v0.10  Android development + second Alpha; not started
Pre-Advance optional Markdown Outline; outside Road v0.7 and unscheduled, never blocks the core flow
later       decide the Windows Road from both Alpha rounds; Linux and watchOS unscheduled
```

## License

Code and accompanying documentation are licensed under [GPL-3.0-or-later](LICENSE). User-created Papers, Vaults, and exports are not keikeu assets; their rights remain with their authors.
