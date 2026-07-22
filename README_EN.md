# keikeu

> A local-first fanfiction writing utility that turns existing inspiration into durable Markdown Papers, then uses Flashcards to focus expansion.

[简体中文](README.md) | English

## Current status

The code implements the `Paper Markdown → Flashcard → external prose editor` core. Road v0.2 Phases 0–7 engineering, macOS file-service smoke, and Phase 8 real-author one-shot and two-session short/medium acceptance are complete and marked by local annotated tag `v0.2.0`. Road archival remains a developer decision.

Phase 7.5 is an independent lightweight iOS build for rapid testing. Its responsive UI, app-sandbox Vault, and on-device fixes are complete on a separate branch; it is not a merge gate in the macOS Road. Road v0.3 Phase 6 Flashcard/daily-card/keyboard engineering is complete, and Phase 7 documentation calibration, full macOS candidate smoke, and product acceptance are next. The runtime reads Paper v2/v3, writes Paper/index v3, and supports one-level Library operations, Paper selection and bounded Flashcard navigation, and a once-per-local-day start card. See [PROJECT](docs/PROJECT.md) for live coordinates.

## Current runtime flow

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

- **Paper:** required current Summary, frozen first-save copy, ordered optional Highlights, and flat optional Tags.
- **Flashcard:** a read-only, Summary-first projection that starts on page 1 on every open or Paper switch; position is not persisted.
- **Library:** searches, opens, soft-deletes, and restores Papers through a local index.
- **Vault:** selects paths only under the current user's Home, validates before switching, and byte-verifies copied unsafe legacy Vaults; Apple App Sandbox is not enabled yet.
- **External editor:** prose always remains outside keikeu.

## Product principles

- Local-first; Markdown is the author asset and the JSON index is rebuildable.
- Never silently rewrite, overwrite, upload, or judge author text.
- No keikeu accounts, cloud backend, telemetry, or background sync.
- OS-exposed folders such as iCloud Drive may be selected as ordinary paths.
- No fandom database, AI ghostwriting, community, or built-in prose editor.

The product contract lives in [SPEC](docs/SPEC.md); reviewable constraints live in [RULES](docs/RULES.md).

## Development

Python `>=3.11,<3.14` is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
flet run src/keikeu_app/main.py
```

## Repository map

```text
README.md                 public entry and real commands
AGENTS.md                 agent operating discipline and read order
docs/PROJECT.md           current coordinates, module entry points, next gate
docs/SPEC.md              product source of truth
docs/RULES.md             engineering, interaction, data, and evidence rules
docs/design/              executable visual system and interaction specimen
docs/architecture/        modules, data flow, lifecycle, and ADRs
docs/acceptance/          supporting evidence; not an independent status source
docs/manual/              supplementary human guides; never normative
docs/generated/           rebuildable and disposable observations
docs/archive/             read-only history; excluded from cold starts
src/keikeu_core/          pure-Python domain and file logic
src/keikeu_app/           Flet shell, pages, and device-local state
tests/                    verifiable implementation facts
```

Hard rule: `keikeu_core` must not import Flet. Only the core layer owns Markdown I/O.

## Documentation entry points

| Question | Single entry point |
| --- | --- |
| Why the product exists, its scope and non-goals | [SPEC](docs/SPEC.md) |
| Current state and next gate | [PROJECT](docs/PROJECT.md) |
| Rules a change must obey | [RULES](docs/RULES.md) |
| Modules and data flow | [Architecture map](docs/architecture/architecture.html) |
| Visual tokens and component states | [Design system](docs/design/design.html) |
| User actions and success/error paths | [Interaction map](docs/design/interaction.html) |
| How agents work | [AGENTS](AGENTS.md) |
| Human-facing design, Git, and ethics guides | [Human manuals](docs/manual/README.md) |
| Historical rationale and snapshots | [Archive](docs/archive/README.md) |

## Route

```text
v0.1        archived macOS Cache / Outline pre-alpha
v0.2        macOS Paper / Flashcard Core; product acceptance complete, Road closeout pending
Phase 7.5   independent lightweight iOS rapid-test build
Phase 8.5   Road v0.3 preparation; precursor to the next Mac version
Road v0.3   macOS Paper Library; Phase 6 / CP4 complete, Phase 7 next
Pre-Advance optional Markdown Outline; never blocks the core flow
later       iPhone/iPad file-service capability, Android, Windows
```

## License

Code and accompanying documentation are licensed under [GPL-3.0-or-later](LICENSE). User-created Papers, Vaults, and exports are not keikeu assets; their rights remain with their authors.
