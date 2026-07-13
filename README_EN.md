# keikeu

> keikeu is a local-first fanfiction writing utility that turns existing inspiration into Markdown Papers and uses Flashcards to focus expansion.

English | [简体中文](README.md)

## Current status

keikeu Road v0.1 is complete and archived. The current code is still the old
`Cache → Outline` macOS pre-alpha. The new product contract is settled and the
project is preparing **Road v0.2: macOS Paper–Flashcard Core**. It has not been
released as a production build.

The implementation follows [`appdesign.md`](appdesign.md) and
[`techpolicy.md`](techpolicy.md) as its target. Road v0.2 behavior and execution
order live in [`spec_road_v0_2.md`](memory/specs/spec_road_v0_2.md) and
[`planbook_road_v0_2.md`](memory/specs/planbook_road_v0_2.md).

## Core flow

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

- **Paper** — one unit intended to become a piece of prose, with a required Summary, recommended Highlights and Tags, plus a frozen first-save draft copy.
- **Flashcard** — a Summary-first, limited-context read-only view; each Highlight becomes one card and the last position is remembered per device.
- **Library** — search Papers by code, Summary, and Tags, then open them in keikeu, the system editor, or Finder.
- **External prose editor** — formal prose always remains outside keikeu.

## Historical Road v0.1 baseline

- Stable Outline Markdown schema with round-trip content elements, ending text, and three-line relation blocks.
- Markdown export through the system save dialog, using a byte-identical vault copy after confirmation and leaving no changes on cancel.
- Soft deletion into `.trash/` for caches and outlines, with collision avoidance and automatic index exclusion.
- Action-driven cache status: save, convert, and archive actions advance state without a conflicting manual status selector.
- Local relation picker for prequel, sequel, IF, side story, and same-series links without hand-typed paths.
- Library integration with system open, Finder reveal, a vault location entry, and safe non-macOS fallbacks.
- Warm-paper visual tokens, Chinese-first interface copy, and a lighter navigation shell.
- Test baseline at archive time: `112 passed`.

These features describe the old product line. Road v0.2 will migrate Caches,
retire active Outlines, and replace the core interaction with Paper and Flashcard.

## Product principles

- Local-first.
- Markdown files are user assets.
- `keikeu_index.json` is rebuildable metadata.
- No keikeu account, cloud backend, or background sync.
- Users may place a vault in an OS file-service folder such as iCloud Drive.
- No external fandom / character / CP database.
- No AI ghostwriting or automatic rewriting of author text.

## What keikeu is

- Markdown Paper tool
- Flashcard writing-focus view
- local Markdown vault tool
- pre-writing utility for discovery-first and hybrid fanfiction authors

## What keikeu is not

- AI writing generator
- social platform
- commission marketplace
- fandom database
- Obsidian / Notion replacement
- cloud writing suite
- full prose editor

## Ethics

keikeu is built around a creator-first ethical baseline. Full reasoning lives in [`ethics.md`](ethics.md).

- Personal creative tool, not a fandom content platform.
- User-owned input only — no scraping, no reposting.
- No public rating, ranking, or aggregation.
- No creator or fanwork database.
- No unauthorized AI training, summarization, imitation, or embedding.
- Local-first by default; any remote model call must be opt-in.
- All generated output is editable; the user is always the final author.
- When convenience conflicts with a creator's boundary, the boundary wins.

## Development setup

Requires Python ≥3.11, <3.14.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Run tests

```bash
python -m pytest
```

### Run the app

```bash
flet run src/keikeu_app/main.py
```

## Repo structure

```text
appdesign.md      product design source of truth
techpolicy.md     technical policy
gitspec.md        Git workflow for humans
gitagent.md       Git workflow for agents

src/
  keikeu_core/    core logic; must not import Flet
  keikeu_app/     Flet UI layer

tests/            core and app tests
```

Hard rule:

```text
keikeu_core must not import Flet.
```

Core must be testable without launching the UI.

## Documentation map

| File | Role |
|---|---|
| [`appdesign.md`](appdesign.md) | Product design source of truth |
| [`techpolicy.md`](techpolicy.md) | Technical stack and implementation policy |
| [`ethics.md`](ethics.md) | Technical-ethics guide |
| [`readmedesign.md`](readmedesign.md) | README handbook design source of truth |
| [`gitspec.md`](gitspec.md) | Human Git workflow manual |
| [`gitagent.md`](gitagent.md) | Agent Git workflow rules |
| [`memory/specs/README.md`](memory/specs/README.md) | Current requirements and historical specification archive index |
| [`memory/specs/spec_road_v0_2.md`](memory/specs/spec_road_v0_2.md) | Road v0.2 behavior and migration contract |
| [`memory/specs/planbook_road_v0_2.md`](memory/specs/planbook_road_v0_2.md) | macOS-first execution handbook |
| [`memory/specs/audit_v01_to_v02_2026-07-13.md`](memory/specs/audit_v01_to_v02_2026-07-13.md) | Road v0.2 pre-implementation code audit and test baseline |
| [`memory/specs/road_pre_advance.md`](memory/specs/road_pre_advance.md) | Deferred optional Outline candidates |
| [`memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md`](memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md) | Road v0.1 execution handbook and phase definitions |
| [`memory/specs/9d033db326295874d1f32f23325e430e0461396d/spec_road_v0_1.md`](memory/specs/9d033db326295874d1f32f23325e430e0461396d/spec_road_v0_1.md) | Road v0.1 behavior specification and acceptance criteria |

## Roadmap

```text
v0.1 — archived macOS Cache / Outline pre-alpha
v0.2 — macOS Paper / Flashcard Core
later — iPhone / iPad file-service parity
Pre-Advance — optional Markdown Outline
later still — Android / Windows
```

## License

License: TBD.
