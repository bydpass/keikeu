# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo status

Road v0.1 is archived at tag `v0.1.0`. The current Python/Flet code still implements the legacy `Cache → Outline` pre-alpha. Road v0.2 is a deliberate product-model migration; do not assume the code already matches the target docs.

Current target authority:

- `appdesign.md` — Paper/Flashcard product truth
- `memory/specs/spec_road_v0_2.md` — behavior and migration contract
- `memory/specs/planbook_road_v0_2.md` — macOS-first implementation order
- `memory/specs/road_pre_advance.md` — deferred optional Outline work

Do not resurrect older Memo/Ticket/SOP designs or treat the v0.1 seven-field Outline as the new default.

## What keikeu is

keikeu is a local-first pre-writing and writing-focus tool for private single-author fanfiction.

Target pipeline: **Paper Markdown (纸片) → Flashcard → external prose editor**

- **Paper** — one work unit intended to become prose: required current Summary, frozen first-save draft copy, ordered optional Highlights, and optional flat Tags.
- **Flashcard** — a read-only projection: Summary first, then one card per Highlight; it remembers last position in per-device disposable state.
- **Outline** — deferred to Pre-Advance; it is not part of the Road v0.2 core flow.

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
- **No database. No keikeu cloud backend/account/background sync. No external AI API.** A user-selected vault may live in an OS file-service folder such as iCloud Drive.

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

The bullets below describe the current v0.1 code until each Road v0.2 phase replaces it. Follow the v0.2 spec for target behavior; preserve the core/app boundary during migration.

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

1. **Author text stays under author control.** Never summarize or rewrite it. First save freezes an immutable draft copy; the author may later edit the current Summary.
2. **Markdown files are the user asset.** `keikeu_index.json` is auxiliary and must be rebuildable from Markdown alone.
3. **No AI-required workflow.** The tool must function fully offline with no external API.
4. **GUI must be caveman-usable.** Open → type → click → file saved. No CLI required.
5. **Local-first before MVP.** No keikeu account, cloud backend, telemetry, or external database. OS-provided third-party file-service folders are allowed when selected by the user.
6. **No creative progress state.** Asset health, trash, and disposable UI position are not writing-progress states.

## Hard out-of-scope before MVP

Do not propose or implement:

- keikeu-operated cloud sync, cloud backend, or account system
- external fandom / character / CP database
- AI ghostwriting, summarization, or automatic rewriting
- social or community features
- plugin architecture
- graph view or world-building DB
- commission marketplace
- Windows-first work
- image generation
- writing therapy / coaching features
- built-in prose editor
- mandatory Outline generation
