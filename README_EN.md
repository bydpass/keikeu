# keikeu

> A local-first fanfiction writing utility that turns existing inspiration into durable Markdown Papers, then uses Flashcards to focus expansion.

[简体中文](README.md) | English

## Current status

The code implements the `Paper Markdown → Flashcard → external prose editor` core. Road v0.2 Phases 0–7 engineering and macOS file-service smoke work are recorded. Phase 8 still lacks complete real-author evidence for a one-shot and a two-session short/medium workflow, so the macOS MVP is not yet product-accepted and the Road is not archived.

iOS 7.5 has responsive UI, an app-sandbox Vault, and on-device fix evidence. It is a separate platform-engineering track, not a substitute for macOS product acceptance. See [PROJECT](docs/PROJECT.md) for the live coordinates.

## Core flow

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

- **Paper:** required current Summary, frozen first-save copy, ordered optional Highlights, and flat optional Tags.
- **Flashcard:** a read-only, Summary-first projection; position is disposable per-device state.
- **Library:** searches, opens, soft-deletes, and restores Papers through a local index.
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
| Historical rationale and snapshots | [Archive](docs/archive/README.md) |

## Route

```text
v0.1        archived macOS Cache / Outline pre-alpha
v0.2        macOS Paper / Flashcard Core; product acceptance in progress
iOS 7.5     device shell and local-Vault engineering validation
Pre-Advance optional Markdown Outline; never blocks the core flow
later       iPhone/iPad file-service capability, Android, Windows
```

## License

Code and accompanying documentation are licensed under [GPL-3.0-or-later](LICENSE). User-created Papers, Vaults, and exports are not keikeu assets; their rights remain with their authors.
