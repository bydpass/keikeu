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

### How the layers talk

- **Serialization lives only in `markdown_io.py`.** Each asset is one Markdown file: a flat `key: value` frontmatter block fenced by `---`, then `#`/`##` sections. There is **no PyYAML** — frontmatter scalars are hand-escaped (`\\`, `\n`, `\r`) so they round-trip exactly. Body sections are keyed by **byte-exact CJK headers** (e.g. `## 1. 原始灵感`); a content line identical to a known header is an unsupported edge case (documented in the module). Enums are `str`-backed (`models.py`) so they write straight into frontmatter with no translation table. Authoritative scalars (status, enums, datetimes) live in frontmatter; free-text prose lives in the body and is preserved verbatim (invariant 1).
- **`write_*` vs `update_*`.** `write_cache`/`write_outline` pick a fresh collision-free filename; `update_cache`/`update_outline` overwrite an existing path. Both share one private `_render_*` so the GUI never serializes by hand.
- **The index is disposable.** Pages call `indexer.rebuild_index(vault)` after every save; `load_index` silently rebuilds a missing/corrupt/wrong-shape index by re-reading the Markdown (never deletes or rewrites a user asset — invariant 2). `list_caches`/`list_outlines` are therefore total (never crash on a damaged index).
- **GUI wiring.** `keikeu_app/main.py` builds one `AppContext` (vault + navigation/open callbacks) in `_build_shell` and hands it to each page builder (`build_cache_page`, `build_outline_editor_page`, `build_library_page`). Pages reach core only through its public functions and route navigation back through the context's callbacks. Config (`~/.keikeu_config.json`) is an app-layer concern; core's `vault` functions take the config path injected.

## Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

# Run all tests (pytest config sets pythonpath=src, testpaths=tests)
python -m pytest

# Run a single test file / test
python -m pytest tests/test_markdown_io.py
python -m pytest tests/test_markdown_io.py -k round_trip

# Run app (either form; `keikeu` is the console script -> keikeu_app.main:run)
flet run src/keikeu_app/main.py
keikeu
```

`pyproject.toml` uses hatchling with an explicit `packages` list and a
`src` -> `` sources remap, so modules import as `keikeu_core` / `keikeu_app`
(no `src.` prefix). Tests rely on `pythonpath = ["src"]`, so run pytest from
the repo root, not inside `tests/`.

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
