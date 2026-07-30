---
name: keikeu-routine
description: Enforce keikeu's project-local workflow for coding, debugging, refactoring, testing, and documentation changes. Use when a task will modify the repository; do not use for read-only review, research, planning, or product discussion unless it proceeds to repository edits.
---

# keikeu Routine

Follow `AGENTS.md`, `docs/SPEC.md`, and `docs/RULES.md`; this skill compresses their workflow and does not override them.

## Before editing

1. Read the relevant authority and every caller affected by a behavior change.
2. Run:

   ```bash
   git status --short --branch
   git branch --show-current
   ```

3. Apply the Git gate in `docs/RULES.md` §7. Stop for unresolved worktree or authority conflicts.
4. For Road work, verify that the current branch is the checkpoint branch required by `docs/RULES.md` §7 before editing.
5. For every repository change, state:

   ```text
   Task:
   - ...
   Will edit:
   - ...
   Will not edit:
   - ...
   ```

6. For bugs, use the caller trace to patch the shared root cause. For other tasks, choose the smallest patch that satisfies the declared scope.

## Implement

- Confirm the behavior is required by the declared scope. Reuse existing code, then the standard library, platform features, and installed dependencies; write only the minimum new code.
- Preserve author content and existing behavior unless the task requires otherwise.
- Do not add abstractions for later. Add a dependency or capability only when the current task requires it, and disclose it before execution.
- Develop and verify migration, delete, recovery, and persistent-config changes only against fixtures, copies, or synthetic data, never the only real Vault.
- Leave one focused regression check for each bug fix.

## Verify

### Automated evidence

- Core or bridge change: run direct focused tests and the relevant Python checks.
- UI change: run focused Vitest, inspect `1220×780` and `920×680`, and run a real Tauri smoke when desktop APIs or lifecycle are involved.
- Docs-only change: run `.venv/bin/python scripts/check_docs.py` and `git diff --check`.
- Never claim a test, smoke, backup, or acceptance check that did not run.

### Developer QA

- Automated evidence proves implementation state, not QA or checkpoint acceptance.
- For skill, workflow, and plan changes, present the result section by section for developer review.
- For UI changes, show the default and minimum-window result; the developer judges comfort, visual taste, and interaction intuition.
- For product checkpoints, run the developer scenarios required by the Planbook or SPEC.
- Do not mark a checkpoint passed unless the developer declared YOLO in advance or explicitly says "passed."

## Handoff

1. Inspect the final diff and `git status --short --branch`; verify that only intended files changed.
2. Summarize what changed and why.
3. Report implementation, automated evidence, and developer QA as separate states.
4. Report data, provider, external-editor, platform, and acceptance risks plus staged, committed, and pushed state.
5. If a commit was explicitly authorized, follow the exact-staging and `aic` procedure in `docs/RULES.md` §7, then inspect the resulting commit.
6. After the final accepted Road checkpoint commit, follow `docs/RULES.md` §8 for the separate Road snapshot closeout.
7. Give the safest next command.
