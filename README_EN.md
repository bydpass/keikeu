# keikeu

> A local-first fanfiction writing utility that turns existing inspiration into durable Markdown Papers, then uses Flashcards to focus expansion.

[简体中文](README.md) | English

## Current status

The code implements the `Paper Markdown → Flashcard → external prose editor` core. Road v0.2 Phases 0–7 engineering, macOS file-service smoke, and Phase 8 real-author one-shot and two-session short/medium acceptance are complete and marked by local annotated tag `v0.2.0`.

Phase 7.5 is an independent lightweight iOS build for rapid testing. Its responsive UI, app-sandbox Vault, and on-device fixes are complete on a separate branch; it is not a merge gate in the macOS Road. Road v0.3 engineering, macOS candidate smoke, and CP6 real-author acceptance are complete: retrieval was faster and clear, the external-editor handoff was clear, and no unresolved P0/P1 was reported. Its design and acceptance records are now [read-only history](docs/archive/road-v0-3/README.md); no v0.3 tag was created. Road v0.4 Gate A, Gate B, product acceptance, and macOS 15.7+ compatibility have passed. The only desktop runtime is now Vue/Tauri with a local Python sidecar; Flet was retired in CP14. See [PROJECT](docs/PROJECT.md) for live coordinates.

## Current runtime flow

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

- **Paper:** required current Summary, frozen first-save copy, ordered optional Highlights, and flat optional Tags.
- **Flashcard:** a read-only, Summary-first projection that starts on page 1 on every open or Paper switch; position is not persisted.
- **Library:** searches and sorts Papers by all/unfiled/one-level-folder scope, with drag/menu/batch moves, branching, Trash, and restore.
- **Vault:** selects paths only under the current user's Home, validates before switching, and byte-verifies copied unsafe legacy Vaults; Apple App Sandbox is not enabled yet.
- **External editor:** prose always remains outside keikeu.

## Road v0.3 archive

The [final CP6 record](docs/archive/road-v0-3/acceptance/road_v0_3.md) is stored with the product, visual, interaction, architecture, ADR, and Planbook records in the [version archive](docs/archive/road-v0-3/README.md). Archival does not change the Vault, runtime, or Git history.

## Product principles

- Local-first; Markdown is the author asset and the JSON index is rebuildable.
- Never silently rewrite, overwrite, upload, or judge author text.
- No keikeu accounts, cloud backend, telemetry, or background sync.
- OS-exposed folders such as iCloud Drive may be selected as ordinary paths.
- No fandom database, AI ghostwriting, community, or built-in prose editor.

Stable product boundaries live in [SPEC](docs/SPEC.md); reviewable constraints live in [RULES](docs/RULES.md).

## Development

Python `>=3.11,<3.14`, Node/npm `22.23.1`/`10.9.8`, and Rust/Cargo
`1.88.0` are required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip install -r requirements-build.lock
npm --prefix frontend ci
.venv/bin/python scripts/build_sidecar.py
npm --prefix frontend run tauri:dev
```

## Repository map

```text
README.md                 public entry and real commands
AGENTS.md                 agent operating discipline and read order
PLAN_revised.md           Road v0.4 execution plan
RULE_FOR_UNDERSTANDING.md Road v0.4 understanding and approval gate
docs/PROJECT.md           current coordinates, module entry points, next gate
docs/SPEC.md              Road v0.4 product and author-control boundary
docs/RULES.md             engineering, interaction, data, and evidence rules
docs/design/              active Road v0.4 visual and interaction maps
docs/architecture/        active Road v0.4 architecture map and ADRs
docs/acceptance/          supporting evidence; not an independent status source
docs/manual/              supplementary human guides; never normative
docs/generated/           rebuildable and disposable observations
docs/archive/             read-only history; excluded from cold starts
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
| Road v0.4 target architecture and current runtime | [Architecture map](docs/architecture/architecture.html) |
| Road v0.4 visual direction | [Design map](docs/design/design.html) |
| Road v0.4 interaction and migration order | [Interaction map](docs/design/interaction.html) |
| How agents work | [AGENTS](AGENTS.md) |
| Human-facing design, Git, and ethics guides | [Human manuals](docs/manual/README.md) |
| Historical rationale and snapshots | [Archive](docs/archive/README.md) |

## Route

```text
v0.1        archived macOS Cache / Outline pre-alpha
v0.2        macOS Paper / Flashcard Core; product acceptance complete, Road closeout pending
Phase 7.5   independent lightweight iOS rapid-test build
Phase 8.5   Road v0.3 preparation; precursor to the next Mac version
Road v0.3   macOS Paper Library; CP6 product accepted, design and acceptance records archived
Road v0.4   Vue/Tauri frontend replacement complete; CP14 accepted
Pre-Advance optional Markdown Outline; never blocks the core flow
later       iPhone/iPad file-service capability, Android, Windows
```

## License

Code and accompanying documentation are licensed under [GPL-3.0-or-later](LICENSE). User-created Papers, Vaults, and exports are not keikeu assets; their rights remain with their authors.
