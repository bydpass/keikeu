# keikeu

> keikeu is a local-first writing utility that helps fan creators turn raw inspiration into editable Markdown outlines.

English | [简体中文](README.md)

## Current status

keikeu Road v0.1 is complete and merged into `main`. It is currently a macOS
pre-alpha development preview: the core creative workflow is usable, but it has
not been released as a production build.

The implementation follows [`appdesign.md`](appdesign.md) and
[`techpolicy.md`](techpolicy.md). The Road v0.1 execution record lives in
[`memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md`](memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md).

## Core flow

```text
raw inspiration → cache Markdown → editable recipe ticket / outline → exported Markdown
```

- **Cache** — low-friction capture of a raw idea. Your words are preserved verbatim, never summarized or rewritten.
- **Outline** — a structured Markdown file derived from a cache: title, raw inspiration, fandom, characters / CP, content elements, plot, ending type, and relations.
- **Library** — search and filter local assets, then open them in keikeu, the system editor, or Finder.

## Completed in Road v0.1

- Stable Outline Markdown schema with round-trip content elements, ending text, and three-line relation blocks.
- Markdown export through the system save dialog, using a byte-identical vault copy after confirmation and leaving no changes on cancel.
- Soft deletion into `.trash/` for caches and outlines, with collision avoidance and automatic index exclusion.
- Action-driven cache status: save, convert, and archive actions advance state without a conflicting manual status selector.
- Local relation picker for prequel, sequel, IF, side story, and same-series links without hand-typed paths.
- Library integration with system open, Finder reveal, a vault location entry, and safe non-macOS fallbacks.
- Warm-paper visual tokens, Chinese-first interface copy, and a lighter navigation shell.
- Current test baseline: `112 passed`.

## Product principles

- Local-first.
- Markdown files are user assets.
- `keikeu_index.json` is rebuildable metadata.
- No account system before MVP.
- No cloud sync before MVP.
- No external fandom / character / CP database.
- No AI-required workflow.

## What keikeu is

- inspiration cache
- outline editor
- local Markdown vault tool
- writing preparation utility for fan creators

## What keikeu is not

- AI writing generator
- social platform
- commission marketplace
- fandom database
- Obsidian / Notion replacement
- cloud writing suite

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
| [`memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md`](memory/specs/9d033db326295874d1f32f23325e430e0461396d/planbook_road_v0_1.md) | Road v0.1 execution handbook and phase definitions |
| [`memory/specs/9d033db326295874d1f32f23325e430e0461396d/spec_road_v0_1.md`](memory/specs/9d033db326295874d1f32f23325e430e0461396d/spec_road_v0_1.md) | Road v0.1 behavior specification and acceptance criteria |

## Roadmap

```text
v0.1 — macOS development preview
v0.2 — iOS internal build
v0.3 — Android APK
v0.4 — Windows preview
```

## License

License: TBD.
