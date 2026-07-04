# Repository Guidelines

## Project Structure & Module Organization

keikeu is a local-first Python/Flet app for turning raw inspiration into editable Markdown outlines. Source lives under `src/`: `src/keikeu_core/` contains pure Python models, vault setup, Markdown I/O, and index rebuilding; `src/keikeu_app/` contains Flet UI shell, pages, and widgets. Tests live in `tests/` and mirror the source modules, for example `tests/test_markdown_io.py` and `tests/test_app_pages.py`.

Root docs are authoritative: `appdesign.md` for product behavior, `techpolicy.md` for stack policy, `gitspec.md` for human Git workflow, and `gitagent.md` for agent workflow.

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

Preserve raw user inspiration verbatim. Markdown files are the user asset; `keikeu_index.json` is disposable metadata rebuilt from Markdown. Do not add cloud sync, accounts, external fandom databases, AI-required workflows, social features, plugin systems, graph/worldbuilding databases, or image generation before MVP.
