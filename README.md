# keikeu

> keikeu is a local-first writing utility that helps fan creators turn raw inspiration into editable Markdown outlines.

English | [简体中文](READMECN.md)

## Current status

keikeu is in early restart development.

The old codebase has been deleted. The current implementation follows
[`appdesign.md`](appdesign.md) and [`techpolicy.md`](techpolicy.md).

It is a development preview, not production-ready.

## Core flow

```text
raw inspiration → cache Markdown → outline Markdown
```

- **Cache** — low-friction capture of a raw idea. Your words are preserved verbatim, never summarized or rewritten.
- **Outline** — a structured Markdown file derived from a cache: title, raw inspiration, fandom, characters / CP, content warnings, plot, ending type, relations.

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
| [`gitspec.md`](gitspec.md) | Human Git workflow manual |
| [`gitagent.md`](gitagent.md) | Agent Git workflow rules |

## Roadmap

```text
v0.1 — macOS development preview
v0.2 — iOS internal build
v0.3 — Android APK
v0.4 — Windows preview
```

## License

License: TBD.
