# keikeu Rules

> Authority: reviewable stack, engineering, interaction, data, Git, and evidence constraints. Product definitions live in [SPEC](SPEC.md); agent operating procedure lives in [AGENTS](../AGENTS.md).

## 1. Authority order

1. Author assets and observed disk state.
2. `src/` plus passing tests for runtime facts.
3. [SPEC](SPEC.md) for intended product behavior.
4. This file for implementation discipline.
5. The Road v0.4 [understanding gate](../RULE_FOR_UNDERSTANDING.md) for checkpoint teaching and review; it never overrides §7 Git authority.
6. [PROJECT](PROJECT.md) for current coordinates.
7. Generated observations and archive history, which never override active sources.

When intent and runtime differ, change code, change the active specification, or record a temporary deviation in an ADR. Never let two answers remain active.

During a staged Road, SPEC and the HTML maps may describe the approved target while `PROJECT.md`, `src/`, and `tests/` identify the current implementation Phase. The target/current label and next convergence gate must remain explicit until the final architecture calibration.

## 2. Architecture

- The current desktop runtime is Vue/Vite JavaScript through a narrow Tauri/Rust host and one JSONL Python sidecar, with Python `>=3.11,<3.14`, author-owned Markdown, and rebuildable JSON metadata.
- Flet was the accepted parity baseline through Gate A and product acceptance; CP14 removes it only after those gates and the macOS 15.7+ compatibility gate passed.
- The Python application service is transport-agnostic and owns orchestration behind JSONL. Rust and Vue do not duplicate product rules.
- The developer owns architecture, dependencies, data models, build commands, and release artifacts; agent output must remain explainable and reviewable.
- `keikeu_core` is pure Python and never imports Flet, Vue, Tauri, Rust, JSONL transport, or another GUI toolkit.
- `markdown_io.py` exclusively owns Paper Markdown parsing and serialization.
- `vault.py` exclusively owns Home containment, supported Paper-path validation, active/Trash enumeration, code allocation across those paths, and destructive filesystem moves.
- GUI code calls the application service; it never renders Markdown or edits index JSON.
- App pages pass validated Vault-relative Paper paths; they never recover a path by guessing `cache/<code>.md`.
- Markdown is canonical author content. Index and device state are disposable.
- Keep explicit files and control flow. Add abstractions only after a second real use exists.
- Prefer existing code, Python stdlib, platform features, then already-installed dependencies.
- New runtime dependencies require a concrete MVP need, packaging impact, maintenance risk, and developer approval.
- No localhost, HTTP, WebSocket, telemetry, updater, or other network behavior is authorized.
- Rust is limited to Tauri lifecycle, sidecar ownership, JSONL request matching, native directory selection, and Python-validated open/reveal.

## 3. Author text and privacy

- Never silently delete, overwrite, normalize, auto-correct, summarize, rewrite, merge, score, train on, upload, or expose author text.
- Preserve the frozen initial Summary, current Summary, Paper/Highlight display names, Highlight content and order, intentionally blank optional fields, and feasible unknown frontmatter.
- Required Summary fails explicitly before disk write.
- Name validation trims only outer whitespace, rejects line breaks/control characters and overlength input, and stores the remaining author text unchanged. NFC+casefold is a comparison key, never a disk rewrite.
- Never ask for prose, inspirations, names, relationships, Vault paths, secrets, or private drafts in chat or acceptance records.
- No telemetry, analytics, account, remote API, hidden background service, or external corpus without explicit product authorization.

## 4. Persistent operations

- Save through same-directory temporary files and safe replacement; never expose a partially written Paper.
- Reject silent overwrite after external modification, deletion, movement, or code collision.
- Resolve every durable-write target and require it to be the current user's Home or a descendant; reject symlink escape before writing.
- Validate a Vault candidate completely before atomically replacing selected-Vault config.
- Delete means soft-delete for current Paper unless an explicitly specified migration contract says otherwise.
- Recovery never overwrites another asset or rewrites a historical Paper code. A conflict stays in Trash and is reported.
- Migration, delete, restore, conflict, and provider-folder changes start on fixtures or copied Vaults.
- Classify an unsafe configured Vault read-only before copying. Copy only ordinary directories and regular files into a new Home-contained destination without following symlinks; any symlink or unsupported/special entry aborts with source and config untouched. Verify the regular-file manifest and bytes.
- Parse Papers and rebuild/validate the index only for a v2/v3 safe copy before config switch. For v0.1, run the existing read-only preflight/manifest validation on the safe copy, switch config atomically to it, then enter the existing migration gate there; cancellation or failure leaves that unmodified safe copy selected. Never parse v0.1 as v2/v3 or write the unsafe source.
- Preserve and report externally created duplicate codes; block mutations involving them rather than renaming either asset.
- Active Trash and permanent delete operate on explicit validated Paper paths, use `unlink` per file, and only `rmdir` verified-empty directories. Recursive cleanup is allowed only for an isolated migration staging tree created by keikeu.
- A destructive migration requires a full backup outside the active Vault but still under Home, staging validation, a readable report, and safe failure behavior.
- Disclose changes to selected Vault, device state, persistent config, signing, or generated platform projects before execution and report the result.

## 5. Interaction

- Keep the author in control: destructive, migration, rename, and recovery actions are explicit and explain consequences.
- Required-field errors block only the unsafe action; optional-field guidance never blocks.
- Every core flow covers default, empty, error, disabled/in-progress, and recovery states where applicable.
- Flashcard remains read-only and Summary-first; it never becomes a progress tracker or prose editor.
- Use responsive layouts, safe areas, keyboard reachability, readable contrast, visible focus, and text wrapping.
- Every drag operation has a keyboard-reachable menu equivalent. Highlight rows expose a drag handle plus **上移/下移** menu actions; reordering does not announce a redundant toast.
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

- Default release order is macOS core, iPhone/iPad capability, Android, then Windows; optional Outline work never blocks the core.
- Before MVP, do not add a plugin architecture, complex graph system, AI-required workflow, social system, external fandom database, or premature Windows/Linux parity.

## 7. Git

- The human owns the diff and repository history. Agent speed never replaces human review or grants architecture or remote authority.
- Before editing, run `git status --short --branch` and `git branch --show-current`. Dirty work requires every dirty file, overlap, and mixing risk to be named, then human confirmation.
- Start implementation from a clean tree unless the human explicitly accepts named existing changes. One implementation Phase uses one branch and one focused capability group.
- After editing, inspect status and both unstaged and staged diffs. Stage exact files only; never use broad staging before reviewing every included path.
- Never stage secrets, environments, caches, `.DS_Store`, logs, build outputs, generated app bundles, or signing data.
- Do not commit unless explicitly asked. A commit has one purpose, an accurate message, and remains safe to review or revert.
- Never push or change remotes without explicit approval. Fetch is inspection; pull, merge, and rebase change local history or files and require a clean tree plus explicit task authority.
- Never rebase shared or public history. Force-push requires explicit approval and `--force-with-lease`; plain `--force` is forbidden.
- Resolve conflicts by reading both sides, preserving intent, limiting edits to the conflict, inspecting the result, and rerunning relevant checks. Never blindly choose ours or theirs.
- Hard reset, clean, forced branch deletion, branch deletion, destructive restore, and history overwrite require explicit approval and exact targets. Prefer revert or other recoverable operations when they fit.
- Before handoff, report branch, HEAD, worktree, staged/committed/pushed state, checks, risks, and the safest next command.

## 8. Evidence

- A focused test proves only the behavior it exercises.
- Automated test temporary files stay under the ignored repository path `tests/test-vault/`; tests never select or mutate a real Vault.
- A synthetic-Vault smoke does not prove a real provider service or real-author workflow.
- A platform build does not prove launch, relaunch, persistence, file access, or product acceptance unless each was observed.
- “Engineering complete,” “file-service smoke complete,” “product accepted,” and “Road archived” are separate conclusions.
- Never copy an old pass count forward as a current result. Record command, state, date when material, and known omissions.
- Docs-only changes run `scripts/check_docs.py` and `git diff --check`; application tests are reported as not run.

## 9. Exceptions

A deliberate exception must be narrow, reversible, named in the relevant diff, and recorded as an ADR when it changes architecture or durable policy. The ADR states context, decision, consequences, expiry or revisit condition, and current status.
