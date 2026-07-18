# keikeu Rules

> Authority: reviewable engineering, interaction, data, Git, and evidence constraints. Product definitions live in [SPEC](SPEC.md); agent operating procedure lives in [AGENTS](../AGENTS.md).

## 1. Authority order

1. Author assets and observed disk state.
2. `src/` plus passing tests for runtime facts.
3. [SPEC](SPEC.md) for intended product behavior.
4. This file for implementation discipline.
5. [PROJECT](PROJECT.md) for current coordinates.
6. Generated observations and archive history, which never override active sources.

When intent and runtime differ, change code, change the active specification, or record a temporary deviation in an ADR. Never let two answers remain active.

## 2. Architecture

- `keikeu_core` is pure Python and never imports Flet or another GUI toolkit.
- `markdown_io.py` exclusively owns Paper Markdown parsing and serialization.
- GUI code calls public core APIs; it never renders Markdown or edits index JSON.
- Markdown is canonical author content. Index and device state are disposable.
- Keep explicit files and control flow. Add abstractions only after a second real use exists.
- Prefer existing code, Python stdlib, platform features, then already-installed dependencies.
- New runtime dependencies require a concrete MVP need, packaging impact, maintenance risk, and developer approval.

## 3. Author text and privacy

- Never silently delete, overwrite, normalize, auto-correct, summarize, rewrite, merge, score, train on, upload, or expose author text.
- Preserve the frozen initial Summary, current Summary, Highlight order, intentionally blank optional fields, and feasible unknown frontmatter.
- Required Summary fails explicitly before disk write.
- Never ask for prose, inspirations, names, relationships, Vault paths, secrets, or private drafts in chat or acceptance records.
- No telemetry, analytics, account, remote API, hidden background service, or external corpus without explicit product authorization.

## 4. Persistent operations

- Save through same-directory temporary files and safe replacement; never expose a partially written Paper.
- Reject silent overwrite after external modification, deletion, movement, or code collision.
- Delete means soft-delete for current Paper unless an explicitly specified migration contract says otherwise.
- Recovery never overwrites another asset. Rename or cancel is explicit.
- Migration, delete, restore, conflict, and provider-folder changes start on fixtures or copied Vaults.
- A destructive migration requires external full backup, staging validation, readable report, and safe failure behavior.
- Disclose changes to selected Vault, device state, persistent config, signing, or generated platform projects before execution and report the result.

## 5. Interaction

- Keep the author in control: destructive, migration, rename, and recovery actions are explicit and explain consequences.
- Required-field errors block only the unsafe action; optional-field guidance never blocks.
- Every core flow covers default, empty, error, disabled/in-progress, and recovery states where applicable.
- Flashcard remains read-only and Summary-first; it never becomes a progress tracker or prose editor.
- Use responsive layouts, safe areas, keyboard reachability, readable contrast, visible focus, and text wrapping.
- Motion may clarify state but cannot be required to understand or complete a task.
- System file services are ordinary paths. Do not pretend to manage provider sync, accounts, timing, or conflict merges.

## 6. Scope and classification

| Level | Meaning | Response |
| --- | --- | --- |
| P0 | data loss, silent text change, unsafe continuation, migration/delete damage | stop writes and repeated experiments; preserve the original Vault; record de-identified steps only |
| P1 | common primary flow cannot complete or is frequently blocked | record shortest reproduction and frequency; fix and reverify before acceptance |
| P2 | usable but inefficient, unclear, or awkward | put in the next-Road candidate pool; do not widen the active Phase |
| P3 | preference, wording, visual polish | record only if useful; it does not affect acceptance |

No feature enters an acceptance or bug-fix Phase by being adjacent, attractive, or convenient.

## 7. Git

- Check status and branch before editing. Dirty work requires a named-file overlap and mixing-risk review plus human confirmation.
- One implementation Phase uses one branch and one focused capability group.
- Inspect before staging; stage exact files only. Never stage secrets, caches, environments, `.DS_Store`, logs, build output, or signing data.
- Do not commit unless asked. Never push, merge, rebase public history, force-push, hard-reset, clean, delete branches, or overwrite files without explicit approval.
- A commit should have one purpose, be explainable in one sentence, and remain safe to review or revert.

## 8. Evidence

- A focused test proves only the behavior it exercises.
- A synthetic-Vault smoke does not prove a real provider service or real-author workflow.
- A platform build does not prove launch, relaunch, persistence, file access, or product acceptance unless each was observed.
- “Engineering complete,” “file-service smoke complete,” “product accepted,” and “Road archived” are separate conclusions.
- Never copy an old pass count forward as a current result. Record command, state, date when material, and known omissions.
- Docs-only changes run `scripts/check_docs.py` and `git diff --check`; application tests are reported as not run.

## 9. Exceptions

A deliberate exception must be narrow, reversible, named in the relevant diff, and recorded as an ADR when it changes architecture or durable policy. The ADR states context, decision, consequences, expiry or revisit condition, and current status.
