# Repository Guidelines

## Project Structure & Module Organization

keikeu is a local-first Python/Flet app for turning existing fanfiction inspiration into durable Markdown Papers and presenting them through a limited-context Flashcard view while prose remains in an external editor. The current code still reflects the archived v0.1 Cache/Outline model; Road v0.2 performs the macOS migration. Source lives under `src/`: `src/keikeu_core/` contains pure Python models, vault setup, Markdown I/O, and index rebuilding, and Road v0.2 will add an isolated legacy migration module; `src/keikeu_app/` contains Flet UI shell, pages, and widgets. Tests live in `tests/` and mirror the source modules.

Root docs are authoritative: `appdesign.md` for product behavior, `techpolicy.md` for stack policy, `gitspec.md` for human Git workflow, and `gitagent.md` for agent workflow. Active Road behavior and order live in `memory/specs/spec_road_v0_2.md` and `memory/specs/planbook_road_v0_2.md`; the v0.1 archive is historical only.

## Build, Test, and Development Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
flet run src/keikeu_app/main.py
keikeu
```

Use `python -m pytest tests/test_markdown_io.py` for a single file, or add `-k round_trip` for focused cases. Run commands from the repo root; pytest relies on `pythonpath = ["src"]`.

## Coding Style & Naming Conventions

Target Python `>=3.11,<3.14`. Use 4-space indentation, type hints on public APIs, `snake_case` for modules/functions, and `PascalCase` for classes. Keep comments short and only where behavior is not obvious.

`keikeu_core` must never import Flet or any GUI package. Serialization belongs in `markdown_io.py`; GUI pages must call core public functions rather than building Markdown or JSON directly.

## Testing Guidelines

Use `pytest`. Core behavior should be covered with direct filesystem tests; UI tests should instantiate page builders with fake pages and avoid launching Flet when possible. Before committing, run the full suite with `python -m pytest` and add focused regression tests for bug fixes.

## Commit & Pull Request Guidelines

Follow the repo's compact scoped history style, such as `init:full_restart`, `init: Scaffold finished`, or `fix: index rebuild`. Keep commits focused. PRs should include a summary, affected files, test results, and screenshots for visible UI changes.

## Product Constraints

Never auto-rewrite author text. First save freezes a draft copy while the current Summary remains author-editable. Markdown files are the user asset; `keikeu_index.json` and per-device Flashcard position are disposable metadata. Do not add a keikeu cloud backend, accounts, external fandom databases, AI ghostwriting, social features, plugin systems, graph/worldbuilding databases, image generation, a built-in prose editor, or mandatory Outline generation before MVP. User-selected OS file-service folders such as iCloud Drive are allowed; keikeu must treat them as ordinary local paths and must not integrate provider accounts or APIs.
