# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo status

Repository reset in commit `172dca3` (`init: full_restart`). All old Python source deleted. Documentation only. Implementation starts fresh from `appdesign.md`.

Old design (Memo → Ticket → SOP/Brief/Card, CustomTkinter, `.spec/`) is gone. Do not resurrect it.

## What keikeu is

keikeu is a local-first tool that helps fan creators turn raw inspiration into editable Markdown outlines saved in a personal vault.

Pipeline: **inspiration cache (灵感缓存) → outline Markdown (大纲)**

- **Cache** — low-friction capture of a raw idea. Preserve the user's words verbatim. Do not summarize, flatten, or evaluate.
- **Outline** — a structured Markdown file derived from a cache: title, raw inspiration, fandom, characters/CP, content warnings, plot, ending type, relations.

## Canonical docs

All design authority lives in these root files:

| File | Role |
|---|---|
| `appdesign.md` | Product design source of truth (pipeline, pages, data model, dev order) |
| `techpolicy.md` | Fixed stack and technical policy |
| `gitspec.md` | Human Git operation manual |
| `gitagent.md` | Agent Git workflow rules |

Do not edit these files during implementation unless a product decision changes.

## Fixed stack

- **Language:** Python ≥3.11, <3.14
- **GUI:** Flet (locked)
- **Storage:** Markdown files (user asset body) + `keikeu_index.json` (rebuildable metadata)
- **No database. No cloud sync. No external AI API.**

## Architecture contract

```
src/
  keikeu_core/     # pure Python — NO Flet imports allowed
    models.py
    vault.py
    markdown_io.py
    indexer.py
  keikeu_app/      # Flet GUI layer — calls keikeu_core only
    main.py
    pages/
    widgets/
tests/
```

Hard rule: `keikeu_core` must never import Flet or any GUI framework. Core must be testable without launching UI.

## Commands

*Provisional — scaffold does not exist yet. Update when `pyproject.toml` is created.*

```bash
# Setup (once scaffold exists)
python3.13 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

# Run tests
.venv/bin/python -m pytest

# Run app
flet run src/keikeu_app/main.py
```

## Product invariants

1. **Raw inspiration is preserved verbatim.** Never summarize or rewrite the user's input.
2. **Markdown files are the user asset.** `keikeu_index.json` is auxiliary and must be rebuildable from Markdown alone.
3. **No AI-required workflow.** The tool must function fully offline with no external API.
4. **GUI must be caveman-usable.** Open → type → click → file saved. No CLI required.
5. **Local-first before MVP.** No cloud sync, no account system, no external database.

## Hard out-of-scope before MVP

Do not propose or implement:

- cloud sync or account system
- external fandom / character / CP database
- AI-required workflow (AI may assist but must not be required)
- social or community features
- plugin architecture
- graph view or world-building DB
- commission marketplace
- Windows-first work
- image generation
- writing therapy / coaching features
