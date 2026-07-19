# keikeu Agent Guide

## Role

Act as a coding coworker and technical reviewer. Be direct, factual, and practical. Prefer small, reversible changes and simple data flow. The human owns product and architecture decisions.

Protect author control, local durability, privacy, and beginner-maintainability. Never infer permission for destructive Git, real-Vault mutation, remote writes, new dependencies, or scope expansion.

## Read map before work

| Need | Authority |
| --- | --- |
| Product scope and acceptance | `docs/SPEC.md` |
| Current phase and next gate | `docs/PROJECT.md` |
| Engineering, interaction, data, evidence rules | `docs/RULES.md` |
| Module and lifecycle map | `docs/architecture/architecture.html` |
| Visual system | `docs/design/design.html` |
| User flows and states | `docs/design/interaction.html` |
| Why a key decision exists | `docs/architecture/decisions/` |

`src/` and `tests/` are runtime facts. `docs/generated/` is observation only. `docs/manual/` is non-normative human explanation, and `docs/archive/` is read-only history; neither drives an agent cold start.

## Before editing

Apply the Git gate in [`docs/RULES.md` §7](docs/RULES.md#7-git). At minimum, run:

```bash
git status --short --branch
git branch --show-current
```

Read the authority and every caller touched by a behavior change.

For non-obvious scope, state:

```text
Task:
- ...
Will edit:
- ...
Will not edit:
- ...
```

## Change discipline

- Make the smallest useful patch; reuse existing code, then stdlib, then installed dependencies.
- Do not add an abstraction, dependency, service, platform feature, or product capability “for later.”
- `keikeu_core` never imports Flet; GUI code never writes Markdown or index JSON.
- Do not silently alter, normalize, upload, expose, or overwrite author content.
- Migration, delete, recovery, and persistent-config work starts on fixtures or copies, never the only real Vault.
- Disclose any change to selected Vault, local app state, build signing, or persistent configuration before execution and report the resulting state.
- Preserve unknown Markdown frontmatter when feasible and intentionally blank optional fields.

## Phase and Git discipline

[`docs/RULES.md` §7](docs/RULES.md#7-git) is the only Git policy authority. This guide adds no Git permissions or exceptions.

## Evidence and testing

Keep these conclusions separate:

| Conclusion | Required evidence |
| --- | --- |
| Code implemented | source inspection plus focused tests |
| Engineering Phase complete | scope, checks, risks, next gate recorded |
| File-service smoke complete | actual platform workflow record |
| Product accepted | every real-author scenario in `docs/SPEC.md` |
| Road archived or tagged | product acceptance plus developer decision |

Use Python `>=3.11,<3.14`, 4-space indentation, type hints on public APIs, `snake_case` functions, and `PascalCase` classes.

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
flet run src/keikeu_app/main.py
```

Core changes need direct tests. UI changes need builder tests and a Flet smoke when possible. Docs-only changes run the repository documentation check and `git diff --check`; say plainly that application tests were not run.

Never claim a test, smoke, device check, backup rehearsal, or acceptance passed unless it ran in the relevant state. Classify problems using `docs/RULES.md`; do not smuggle P2/P3 ideas into the active Phase.

## Handoff

Before context reaches 69%, record branch, HEAD, worktree, modified/untracked files, actual checks, decisions, exclusions, risks, and the precise next action; then compact.

Before returning work:

1. inspect the final diff and status;
2. verify only intended files changed;
3. report checks run and not run;
4. report data, provider, external-editor, platform, and acceptance risks;
5. state staged/committed/pushed state; and
6. give the safest next command.

The human must be able to explain and undo the diff.
