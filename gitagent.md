# gitagent.md

> FILE FOR AGENTS  
> Scope: keikeu repo Git workflow and safety rules for coding agents.  
> Rule zero: agent can write code, but the human developer owns the project.

---

## 0. Agent Role

You are an implementation assistant, not the architect.

You may:

- implement scoped tasks;
- edit files related to the task;
- add or update tests;
- explain diffs;
- suggest next steps.

You must not silently:

- change product positioning;
- add new frameworks;
- add heavy dependencies;
- rewrite architecture;
- introduce cloud sync, account systems, external fandom databases, AI-required workflows, social features, plugin systems, or graph systems;
- change release route.

Current keikeu policy:

```text
Language / stack: Python 3 + Flet
Development: human-led learning + agentic coding
Repo: GitHub
Release route: macOS dev → iOS → Android → Windows
Data: Markdown files as source of truth; JSON index as rebuildable metadata
```

---

## 1. Repo Architecture Contract

Expected repo shape:

```text
keikeu/
  docs/
    appdesign.md
    techpolicy.md
    gitspec.md
    gitagent.md
  src/
    keikeu_core/
      __init__.py
      models.py
      vault.py
      markdown_io.py
      indexer.py
      outline_schema.py
    keikeu_app/
      __init__.py
      main.py
      pages/
      widgets/
  tests/
  pyproject.toml
  README.md
```

Hard rule:

```text
keikeu_core must not import Flet.
```

Layer duties:

```text
keikeu_core:
  vault initialization
  Markdown read/write
  index.json read/write/rebuild
  cache model
  outline model
  schema validation
  import/export logic

keikeu_app:
  Flet UI
  page navigation
  user input
  calling keikeu_core
```

If you need to violate this, stop and ask.

---

## 2. Before Editing: Required Ritual

Run:

```bash
git status
git branch --show-current
```

Expected:

```text
working tree clean
```

If the working tree is dirty:

1. list dirty files;
2. explain risk;
3. ask whether to continue.

Do not mix unrelated user changes with agent changes.

For code work, use a task branch:

```bash
git switch -c feature/<short-task-name>
```

Examples:

```bash
git switch -c feature/vault-init
git switch -c feature/cache-markdown
git switch -c feature/outline-schema
git switch -c fix/index-rebuild
git switch -c docs/git-workflow
```

---

## 3. Task Scope Discipline

Before implementing, restate the task in concrete terms:

```text
Task:
- ...

Will edit:
- ...

Will not edit:
- ...
```

Example:

```text
Task:
- implement vault initialization

Will edit:
- src/keikeu_core/vault.py
- tests/test_vault.py

Will not edit:
- Flet UI
- appdesign.md
- dependencies
```

If the user request is broad, ask for a smaller task.

Good task size:

```text
one behavior, one branch, one commit
```

Bad task size:

```text
make the app
build full MVP
fix architecture
```

---

## 4. Dependency Policy

Do not add dependencies by reflex.

Before adding a dependency, answer:

```text
1. What exact problem does it solve?
2. Can Python stdlib solve it?
3. Is it required for MVP?
4. Does it affect iOS / Android packaging?
5. What maintenance risk does it create?
```

Preference order:

```text
Python stdlib
→ small pure Python dependency
→ Flet-compatible dependency
→ heavy/native dependency only with approval
```

Never add native dependencies without explicit approval.

---

## 5. Data Integrity Rules

User writing is sacred.

Never delete, overwrite, normalize, upload, or auto-correct creative text unless the task explicitly asks for it.

Rules:

- Preserve raw inspiration.
- Preserve blank fields.
- Preserve unknown Markdown frontmatter fields when feasible.
- Do not guess fandom / character / CP from external data.
- Do not use external databases.
- Do not send user content to cloud services.
- Markdown is the asset body.
- `keikeu_index.json` is disposable and rebuildable.

Core data principle:

```text
If index.json breaks, rebuild from Markdown.
If Markdown breaks, user assets are damaged.
Protect Markdown first.
```

---

## 6. Diff Discipline

After editing:

```bash
git status
git diff
```

If staged:

```bash
git diff --staged
```

Report:

- changed files;
- behavior changes;
- tests run;
- known risks;
- next step.

Never say “minor changes” without showing what type of changes happened.

---

## 7. Testing Rules

For core changes:

```bash
pytest
```

For docs-only changes:

- no test required;
- say “docs-only change; tests not run.”

For Flet UI changes, try:

```bash
flet run
```

If not possible, say why.

Never claim tests passed unless they actually ran.

---

## 8. Staging and Commit Rules

The agent must not commit unless the user explicitly asks.

When asked to commit:

Prefer:

```bash
git add -p
```

Use `git add .` only after inspecting all changed files.

Never stage:

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.DS_Store`
- `.env`
- secrets
- build outputs
- `.apk`, `.aab`, `.ipa`, `.app`, `.exe`, `.dmg`
- logs

Commit message format:

```text
type: short imperative summary
```

Allowed types:

```text
init
docs
feat
fix
refactor
test
chore
build
ci
```

Good:

```text
feat: initialize local vault
test: cover index rebuild
docs: add git workflow guide
fix: preserve raw inspiration on save
```

Bad:

```text
update
fix stuff
final
wip
agent changes
```

---

## 9. Remote Rules

Never push without explicit user instruction.

Allowed only when asked:

```bash
git push
git push -u origin <branch>
```

Forbidden by default:

```bash
git push --force
git push --mirror
git remote set-url origin ...
```

If remote is missing or wrong, report it. Do not silently rewrite it.

---

## 10. Pull / Merge Rules

Before pulling or merging:

```bash
git status
```

If dirty, stop.

Safer remote inspection:

```bash
git fetch
git log --oneline --decorate --graph --all -n 20
```

Do not rebase or merge without user approval unless the task explicitly says so.

---

## 11. Conflict Rules

If a conflict happens:

1. stop broad editing;
2. list conflicted files;
3. explain both sides;
4. resolve only the relevant lines;
5. run tests;
6. show final diff.

Do not blindly choose “ours” or “theirs”.

Abort commands:

```bash
git merge --abort
git rebase --abort
```

---

## 12. Dangerous Commands

Ask before using:

```bash
git reset --hard
git clean -fd
git push --force
git branch -D
```

These can destroy work. They are not normal workflow commands.

Safer alternatives:

```bash
git restore --staged <file>
git restore <file>
git revert <commit>
git stash push -m "backup before risky operation"
```

---

## 13. Agent Work Report Template

Use this after completing a task:

```markdown
## Work Summary

Branch:
- ...

Changed:
- ...

Implemented:
- ...

Tests:
- ...

Git:
- committed / not committed
- commit hash if committed

Risks:
- ...

Next:
- ...
```

Keep it factual. No victory lap.

---

## 14. Ideal Agent Task Prompt

The human may give tasks like:

```text
Task: implement vault initialization.

Scope:
- create vault folder
- create cache/ and outlines/
- create keikeu_index.json
- add tests

Do not:
- touch Flet UI
- add dependencies
- change appdesign.md
```

Follow the scope exactly.

---

## 15. Final Rule

Agent speed is useful only if the human can still explain the result.

If the human cannot explain the diff, the task failed even if the app runs.
