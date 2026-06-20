# Repository Guidelines

## Project Structure & Module Organization

This repository is currently documentation-first. The active source of truth lives at the repo root: `appdesign.md`, `techpolicy.md`, `gitspec.md`, `gitagent.md`, and `CLAUDE.md`. Old `.spec/` and CustomTkinter-era assumptions are retired.

When implementation starts, keep the planned split from `CLAUDE.md`:

```text
src/keikeu_core/   # pure Python, no Flet imports
src/keikeu_app/    # Flet UI only
tests/
```

`keikeu_core` owns models, Markdown I/O, vault/index logic, and schema validation. `keikeu_app` owns pages, widgets, and UI flow.

## Build, Test, and Development Commands

The scaffold does not exist yet, so these commands are provisional:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
flet run src/keikeu_app/main.py
```

Use `pytest` for automated tests once `tests/` exists. Run the Flet app locally for UI work only after the scaffold is in place.

## Coding Style & Naming Conventions

Target Python `>=3.11,<3.14`. Use 4-space indentation, type hints on public APIs, `snake_case` for functions/modules, `PascalCase` for classes, and short docstrings where behavior is not obvious.

Keep architecture strict: `keikeu_core` must remain GUI-free and testable without launching Flet. Do not add heavy or native dependencies without explicit approval. Prefer stdlib first.

## Testing Guidelines

Use `pytest`. Mirror source layout in tests, for example `tests/test_vault.py` for `src/keikeu_core/vault.py`. Favor core-layer tests first; UI tests should stay narrow and verify behavior that cannot be covered in core.

Before committing, run the relevant tests for every edited module.

## Commit & Pull Request Guidelines

Follow the repo's existing scoped style: `init: full_restart`, `docs: update guide`, `fix: index rebuild`. Keep commits focused to one task and use one branch per task, such as `feature/vault-init` or `docs/contributor-guide`.

PRs should include a concise summary, impacted files, test notes, and screenshots for UI changes. Do not mix architecture changes, dependency changes, and feature work in one PR.

## Product Constraints

Respect the MVP guardrails in `appdesign.md` and `techpolicy.md`: local-first, Markdown as the user asset, rebuildable JSON index, no cloud sync, no accounts, no social features, no plugin system, and no AI-required workflow.
