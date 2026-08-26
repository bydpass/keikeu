---
name: keikeu-routine
description: Enforce keikeu's project-local workflow for coding, debugging, refactoring, testing, and documentation changes. Use when a task will modify the repository; do not use for read-only review, research, planning, or product discussion unless it proceeds to repository edits.
---

# keikeu Routine

Follow `AGENTS.md`, `docs/SPEC.md`, and `docs/RULES.md`; this skill compresses their workflow and does not override them.

## Start hook

Run this gate immediately after the skill is selected and before the first repository edit.

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

## Optional terminology hook

Run this hook only when the developer explicitly invokes `$vibehub`, asks for a plain-language
term explanation, or says they want to learn from the current change. Ordinary repository work
must not trigger VibeHub or another external resolver.

1. Select at most three terms that name changed UI elements, data or runtime elements, or workflow gates and materially help the developer review the change. Skip unchanged concepts and generic command names.
2. Invoke `$vibehub` to explain each selected term in this change's context. Give its resolver only a de-identified term or behavior; never send source, author content, secrets, internal errors, URLs, emails, or local paths.
3. Add a concise `术语诠释` section to the handoff: state what each term means here, why it appears, and one boundary it does not cover. Use only links returned by VibeHub for clear matches.
4. If no term needs explanation or the resolver is unavailable, continue the handoff without inventing links or opening a lesson. This hook is explanatory only and does not authorize extra project edits, browser work, or scope.

## Stop hook

Run this gate immediately before the final response for every repository-changing task.

1. Inspect the final diff and `git status --short --branch`; verify that only intended files changed.
2. Run the optional Terminology hook only when its explicit user-intent condition is met.
3. Summarize what changed and why.
4. Report implementation, automated evidence, and developer QA as separate states.
5. Report data, provider, external-editor, platform, and acceptance risks plus staged, committed, and pushed state.
6. If a commit was explicitly authorized, follow the exact-staging and `aic` procedure in `docs/RULES.md` §7, then inspect the resulting commit. DeepSeek `aic` has standing developer authorization for this repository after the staged diff is reviewed and found free of secrets and author content: name DeepSeek and report the staged boundary, but do not ask again for provider approval. Explicit commit authority is still required; another provider, a sensitive or unexpected diff, or revoked authorization requires a new decision. Treat the authorized invocation and the commit it creates as one transaction without a second authorization.
7. After the final accepted Road checkpoint commit, follow `docs/RULES.md` §8 for the separate Road snapshot closeout.
8. After the final worktree state, checks, and any authorized commit or Road snapshot are complete, refresh the ignored local context route at `build/context/keikeu-context.txt` with:

   ```bash
   .venv/bin/python scripts/build_context_pack.py
   ```

   Append repeated `--path path/to/file` arguments only for the smallest reviewed set of tracked files the next coding agent needs; the authority files are included automatically. Confirm that the header records the current branch, HEAD, selected-file status, selected/skipped counts, and current-local-tree source, then review the included-file boundaries. Never select author content, secrets, ignored data, private or external paths, or unrelated cold evidence. Never stage or upload the route or treat it as authority, test evidence, or acceptance: it is a disposable local handoff artifact. Atomic generation preserves the previous file on failure; report the exact error and that the route is stale instead of hand-editing it or claiming it was refreshed.
9. Give the safest next command.
