> **ARCHIVED — READ ONLY.** Historical Git manual; current repository rules live in [`docs/RULES.md`](../RULES.md).

# gitspec.md

> FILE FOR HUMAN  
> Scope: practical Git operation manual for keikeu development.  
> Goal: build complete operation thinking, not memorize random commands.

---

## 0. Git Mental Model

Git is three things:

```text
time machine
safety lock
incident recorder
```

It is not just a GitHub upload button.

Core idea:

```text
working tree → staging area → commit history → remote
```

Meaning:

```text
working tree:
  your current files

staging area:
  the exact changes you choose for the next commit

commit:
  a named checkpoint

remote:
  GitHub copy of your repo
```

Your daily loop is:

```text
observe → branch → edit → inspect → test → stage → commit → merge → push
```

No blind commits. No black-box agent diffs.

---

## 1. Status First

Use this constantly:

```bash
git status
```

It tells you:

- current branch;
- changed files;
- staged files;
- untracked files;
- whether you are ahead/behind remote.

Before any important command, run:

```bash
git status
```

This is your cockpit display. Do not fly blind.

---

## 2. Inspect Changes

Show unstaged changes:

```bash
git diff
```

Show staged changes:

```bash
git diff --staged
```

Show recent commits:

```bash
git log --oneline --decorate -n 10
```

Show branch graph:

```bash
git log --oneline --decorate --graph --all -n 20
```

Show one commit:

```bash
git show <commit-hash>
```

Rule:

```text
If you do not understand the diff, do not commit it.
```

---

## 3. First Repo Setup

Inside project folder:

```bash
git init
git branch -M main
git status
```

Create baseline:

```bash
mkdir -p docs src tests
touch README.md pyproject.toml
```

Add and commit:

```bash
git add README.md pyproject.toml docs/
git commit -m "init: create keikeu project baseline"
```

Connect GitHub:

```bash
git remote add origin <repo-url>
git push -u origin main
```

Check remote:

```bash
git remote -v
```

---

## 4. keikeu Standard Work Loop

Use this for almost every task:

```bash
git status
git switch -c feature/<task-name>

# edit files

git status
git diff

# run tests if code changed
pytest

git add -p
git diff --staged
git commit -m "type: short summary"

git switch main
git merge feature/<task-name>
git branch -d feature/<task-name>
git push
```

This looks slow. It is not.  
It prevents repo rot.

---

## 5. Branch Thinking

`main` should be stable.

Use feature branches for scoped work:

```bash
git switch -c feature/vault-init
git switch -c feature/cache-markdown
git switch -c feature/outline-schema
git switch -c feature/flet-cache-page
```

Use fix branches for bugs:

```bash
git switch -c fix/index-rebuild
```

Use docs branches for documentation:

```bash
git switch -c docs/git-workflow
```

Branch rule:

```text
one task, one branch
```

Bad branch:

```text
feature/mvp
```

Good branch:

```text
feature/vault-init
```

A giant branch is just a corpse pile with a name tag.

---

## 6. Commit Thinking

A commit is a clean checkpoint.

Good commit:

- has one purpose;
- can be explained in one sentence;
- can be reverted safely;
- leaves the repo in a runnable or at least understandable state.

Commit format:

```text
type: short imperative summary
```

Types:

```text
init      repo/project setup
docs      documentation
feat      new behavior
fix       bug fix
refactor  cleanup without behavior change
test      tests
chore     maintenance/config
build     packaging/build config
ci        automation
```

Examples:

```bash
git commit -m "init: create python package skeleton"
git commit -m "docs: add git workflow guides"
git commit -m "feat: initialize local vault"
git commit -m "feat: write cache markdown file"
git commit -m "test: cover outline schema"
git commit -m "fix: rebuild index from markdown files"
```

Bad:

```bash
git commit -m "update"
git commit -m "fix"
git commit -m "final"
git commit -m "changes"
```

---

## 7. Staging

Stage a file:

```bash
git add <file>
```

Stage interactively:

```bash
git add -p
```

Stage all:

```bash
git add .
```

Recommended:

```bash
git add -p
```

Why: it lets you commit only the hunks you understand.

Unstage one file:

```bash
git restore --staged <file>
```

Unstage all:

```bash
git restore --staged .
```

---

## 8. Undo Commands

### Undo unstaged edits in one file

```bash
git restore <file>
```

Danger: destroys current edits in that file.

### Unstage but keep edits

```bash
git restore --staged <file>
```

### Fix last commit message

```bash
git commit --amend -m "docs: add git workflow guides"
```

Use before push.

### Undo last commit but keep changes staged

```bash
git reset --soft HEAD~1
```

### Undo last commit and keep changes unstaged

```bash
git reset --mixed HEAD~1
```

### Destroy last commit and changes

```bash
git reset --hard HEAD~1
```

`--hard` is a chainsaw. Do not use while tired.

### Safe rollback after push

```bash
git revert <commit-hash>
```

Prefer `revert` on `main`.

---

## 9. Stash

Use stash for temporary storage.

Save:

```bash
git stash push -m "wip outline editor"
```

List:

```bash
git stash list
```

Restore and remove latest stash:

```bash
git stash pop
```

Restore but keep stash:

```bash
git stash apply
```

Drop stash:

```bash
git stash drop stash@{0}
```

Rule:

```text
stash is a pocket, not a warehouse
```

Do not stack ten mystery stashes.

---

## 10. Remote / GitHub

Show remote:

```bash
git remote -v
```

Add remote:

```bash
git remote add origin <repo-url>
```

Push first time:

```bash
git push -u origin main
```

Push later:

```bash
git push
```

Fetch remote state:

```bash
git fetch
```

Pull:

```bash
git pull
```

Safer habit:

```bash
git fetch
git status
```

Then decide what to do.

---

## 11. Merge

Merge feature branch:

```bash
git switch main
git merge feature/<task-name>
```

Delete merged branch:

```bash
git branch -d feature/<task-name>
```

Force delete:

```bash
git branch -D feature/<task-name>
```

Use `-D` only when intentionally discarding branch work.

Abort merge:

```bash
git merge --abort
```

---

## 12. Rebase

Rebase rewrites history.

Beginner rule:

```text
Avoid rebase until merge workflow feels boring.
```

Allowed later for your own unpushed feature branch:

```bash
git switch feature/<task-name>
git rebase main
```

Never rebase public/shared `main`.

Abort:

```bash
git rebase --abort
```

---

## 13. Conflict Handling

Conflict marker:

```text
<<<<<<< HEAD
current branch version
=======
incoming version
>>>>>>> feature/name
```

Workflow:

```bash
git status
# open conflicted files
# edit manually
git add <resolved-file>
git commit
```

Rules:
- read both sides;
- preserve intent;
- do not blindly choose ours/theirs;
- run tests after resolving.

---

## 14. `.gitignore` Baseline

Create `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/
env/

# Secrets
.env
.env.*
*.pem
*.key

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Build outputs
build/
dist/
*.apk
*.aab
*.ipa
*.app
*.exe
*.dmg

# Logs
*.log
```

Do not ignore source code, docs, tests, or important config.

---

## 15. Agentic Coding Workflow

Before asking agent to code:

```bash
git status
git switch -c feature/<task-name>
```

Give scoped instruction:

```text
Task: implement vault initialization.
Scope:
- create cache/ and .trash/cache/
- create keikeu_index.json
- add tests

Do not:
- touch UI
- add dependencies
- change product docs
```

After agent edits:

```bash
git status
git diff
pytest
git add -p
git diff --staged
git commit -m "feat: initialize local vault"
```

Rule:

```text
Agent writes code. Human owns the diff.
```

---

## 16. keikeu First Commit Plan

After repo reset, make these commits.

### Commit 1: project docs

```bash
git add README.md pyproject.toml docs/appdesign.md docs/techpolicy.md docs/gitspec.md docs/gitagent.md
git commit -m "init: create keikeu project baseline"
```

### Commit 2: package skeleton

```bash
mkdir -p src/keikeu_core src/keikeu_app tests
touch src/keikeu_core/__init__.py
touch src/keikeu_app/__init__.py
touch tests/__init__.py
git add src tests
git commit -m "init: create python package skeleton"
```

### Commit 3: gitignore

```bash
touch .gitignore
# paste ignore rules
git add .gitignore
git commit -m "chore: add gitignore"
```

### Commit 4: first feature branch

```bash
git switch -c feature/vault-init
# implement vault init
pytest
git add -p
git commit -m "feat: initialize local vault"
git switch main
git merge feature/vault-init
git branch -d feature/vault-init
```

---

## 17. Emergency Protocol

When something feels wrong:

```bash
git status
git log --oneline --decorate -n 10
git diff
```

Do not panic-run:

```bash
git reset --hard
git clean -fd
git push --force
```

If current uncommitted work matters:

```bash
git stash push -m "emergency backup"
```

If a committed change broke `main`:

```bash
git revert <commit-hash>
```

If you are confused:

```text
stop, copy terminal output, ask
```

---

## 18. Version Tags

Use tags for release checkpoints.

Create tag:

```bash
git tag -a v0.1.0 -m "v0.1.0 macOS dev preview"
```

Push tag:

```bash
git push origin v0.1.0
```

Suggested route:

```text
v0.1.0  archived macOS Cache / Outline pre-alpha
v0.2.0  macOS Paper / Flashcard Core
later   iPhone / iPad file-service parity
later   Android / Windows
```

---

## 19. Operation Checklist

Before coding:

```text
[ ] git status clean
[ ] correct branch
[ ] task is small
[ ] no unnecessary dependency
```

Before commit:

```text
[ ] git diff reviewed
[ ] tests run or docs-only noted
[ ] staged changes checked
[ ] commit message specific
```

Before push:

```text
[ ] main is stable
[ ] latest commits make sense
[ ] no secrets/build junk staged
```

---

## 20. Final Rule

Small branches.  
Small commits.  
Readable history.  
No blind agent diffs.

This is how keikeu avoids becoming another corpse pile.
