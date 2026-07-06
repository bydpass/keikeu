# Claude Handoff After Road v0.1 Phase 2

Date: 2026-07-06
Repo: `/Users/chenxi/kits/keikeu`
Current branch: `feature/export-markdown`

## Current Project Stage

Road v0.1 is in progress.

Completed:

- Phase 0: repo/spec/document baseline was prepared before implementation resumed.
- Phase 1: outline Markdown schema finalized in commit `6c2833e` (`feat: phase1_done`).
- Phase 2: outline Markdown export added in commit `2707cae` (`feat: export outline as markdown`).

Next planned work:

- Phase 3: `fix/soft-delete-archive`
- Spec source: `memory/specs/spec_road_v0_1.md`, WI-3
- Planbook source: `memory/specs/planbook_road_v0_1.md`, Phase 3

## Current Test Status

Last full test run:

```bash
.venv/bin/python -m pytest
```

Result:

```text
82 passed
```

Manual UI check:

- User manually tested the outline UI after Phase 2.
- The original `Unknown control: FilePicker` failure is fixed.
- Manual test passed before this handoff was written.

## Phase 1 Notes

Outline schema is now the WI-1 format:

- `Outline.content_warnings` is gone.
- Outline has `warning_setting`, `warning_cp_structure`, and `warning_elements`.
- `RelationType` values are user-facing Chinese labels: `前作`, `续作`, `IF`, `外传`, `同系列`.
- Markdown section 4 writes three labeled lines.
- Markdown section 6 writes `HE` / `BE` / `OE` for non-custom endings, or `custom_ending` text for custom.
- Markdown section 7 writes three-line relation blocks separated by blank lines.

Do not reintroduce the old pipe relation format or old `content_warnings` field.

## Phase 2 Notes

Outline editor now has `导出 Markdown`.

Behavior:

- Clicking export opens `ft.FilePicker.save_file`.
- If the user cancels, nothing is saved or exported.
- If the user confirms, the current outline is saved to the vault first.
- Export then copies the vault Markdown file byte-for-byte with `shutil.copy2`.
- Core remains unchanged; export is app-layer only.

Important Flet 0.85.3 trap:

- `ft.FilePicker` is a `Service`, not a normal `Control`.
- It must be attached through `page.services.append(export_picker)`.
- Do not put it in `page.overlay`; that caused `Unknown control: FilePicker`.
- `FilePicker.save_file(...)` is async and must be awaited.

Tests now guard this:

- `tests/test_app_pages.py` checks the picker lives in `page.services`, not `page.overlay`.
- Export tests cover saved outline export, unsaved draft export, and cancel behavior.

## Phase 3 Scope Reminder

Implement only WI-3 in the next phase:

- Add `.trash/cache/` and `.trash/outlines/` creation in `init_vault`.
- Keep `is_vault` tolerant; it must not require `.trash`.
- Add pure-core `soft_delete(vault: Path, rel_path: str) -> Path`.
- Move only `cache/*.md` and `outlines/*.md` into matching `.trash/` subdirs.
- Preserve bytes exactly.
- Avoid overwriting on duplicate names by suffixing the destination filename.
- Add tests that `.trash` content is not indexed.
- Add delete buttons to cache editor, outline editor, and Library rows.
- Replace cache status dropdown with a read-only status badge.
- State transitions are action-driven:
  - Save does not change status.
  - Convert to outline sets `drafting`; saving generated outline sets `outlined`.
  - Archive button sets `archived`.
  - Archived cache remains editable and stays archived on save.

Do not implement restore UI, graph view, relation picker, Library open/reveal, or visual redesign in Phase 3. Those belong to later phases.

## Project Red Lines

- `keikeu_core` must not import Flet or any GUI package.
- Serialization belongs in `src/keikeu_core/markdown_io.py`.
- GUI pages must call core public functions rather than building Markdown or JSON directly.
- Do not add dependencies.
- Do not edit `appdesign.md`, `techpolicy.md`, `gitspec.md`, or `gitagent.md` for Phase 3.
- Preserve raw inspiration verbatim.
- Markdown files are the user asset; `keikeu_index.json` is disposable metadata.

## Git Workflow Reminder

Before Phase 3:

```bash
git status
git switch -c fix/soft-delete-archive
```

If the worktree is not clean, stop and ask the user before editing.

