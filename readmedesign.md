# README rewrite

Modify:

```text
README.md
```

Create:

```text
READMECN.md
```

`README.md` is the English version.
`READMECN.md` is the Simplified Chinese version.

The two files should contain the same information, but wording does not need to be line-by-line identical.

## Goal

Create a clean public-facing README for the restarted keikeu repo.

The README must explain:

* what keikeu is
* current development status
* what problem it solves
* what it does not try to be
* how the project is structured
* how to set up the development environment
* how to run tests
* how to launch the app after Flet scaffold exists
* where the canonical design docs live
* the release route

The README must not pretend the app is already production-ready.

---

### Required Sections

Both `README.md` and `READMECN.md` must include:

1. Project title
2. One-line product description
3. Current status
4. Core flow
5. Product principles
6. What keikeu is
7. What keikeu is not
8. Development setup
9. Test command
10. Run command
11. Repo structure
12. Documentation map
13. Roadmap
14. License status

---

### Content Requirements

#### 1. Project description

English:

```text
keikeu is a local-first writing utility that helps fan creators turn raw inspiration into editable Markdown outlines.
```

Simplified Chinese:

```text
keikeu 是一个本地优先的写作辅助工具，用来帮助同人创作者把零碎灵感整理成可继续写作的 Markdown 大纲。
```

#### 2. Current status

Must clearly state:

```text
keikeu is in early restart development.
The old codebase has been deleted.
The current implementation follows docs/appdesign.md and docs/techpolicy.md.
```

Chinese version should say:

```text
keikeu 当前处于重启后的早期开发阶段。
旧代码库已经清空。
当前实现以 docs/appdesign.md 与 docs/techpolicy.md 为准。
```

#### 3. Core flow

Must include:

```text
raw inspiration → cache Markdown → outline Markdown
```

Chinese version:

```text
原始灵感 → 灵感 cache Markdown → 大纲 Markdown
```

#### 4. Product principles

Must include:

```text
- Local-first.
- Markdown files are user assets.
- keikeu_index.json is rebuildable metadata.
- No account system before MVP.
- No cloud sync before MVP.
- No external fandom / character / CP database.
- No AI-required workflow.
```

Chinese version:

```text
- 本地优先。
- Markdown 文件是用户资产本体。
- keikeu_index.json 是可重建的软件索引。
- MVP 前不做账号系统。
- MVP 前不做云同步。
- 不接入外部 fandom / 角色 / CP 数据库。
- 不把 AI 作为必要工作流。
```

#### 5. What keikeu is

Must include:

```text
- inspiration cache
- outline editor
- local Markdown vault tool
- writing preparation utility for fan creators
```

Chinese version:

```text
- 灵感缓存工具
- 大纲编辑器
- 本地 Markdown vault 工具
- 面向同人创作者的写作准备工具
```

#### 6. What keikeu is not

Must include:

```text
- AI writing generator
- social platform
- commission marketplace
- fandom database
- Obsidian / Notion replacement
- cloud writing suite
```

Chinese version:

```text
- AI 代写工具
- 社交平台
- 约稿交易平台
- fandom 数据库
- Obsidian / Notion 替代品
- 云端写作套件
```

---

### Development Setup

If `pyproject.toml` already exists, include real commands.

Expected commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

If Flet entry point already exists, include:

```bash
flet run src/keikeu_app/main.py
```

If the Flet entry point does not exist yet, write:

```text
Flet run command will be finalized after the app shell is created.
```

Do not invent commands that do not work.

---

### Repo Structure

Include this structure if scaffold exists:

```text
docs/
  appdesign.md      product design source of truth
  techpolicy.md     technical policy
  gitspec.md        Git workflow for humans
  gitagent.md       Git workflow for agents

src/
  keikeu_core/      core logic; must not import Flet
  keikeu_app/       Flet UI layer

tests/
  core tests
```

Must include this hard rule:

```text
keikeu_core must not import Flet.
```

Chinese version:

```text
keikeu_core 不得 import Flet。
```

---

### Documentation Map

Mention:

```text
docs/appdesign.md
```

as product design source of truth.

Mention:

```text
docs/techpolicy.md
```

as technical stack and implementation policy.

Mention:

```text
docs/gitspec.md
```

as human Git workflow manual.

Mention:

```text
docs/gitagent.md
```

as agent Git workflow rules.

---

### Roadmap

Use the current release route:

```text
v0.1 — macOS development preview
v0.2 — iOS internal build
v0.3 — Android APK
v0.4 — Windows preview
```

Chinese version:

```text
v0.1 — macOS 开发预览版
v0.2 — iOS 内测版
v0.3 — Android APK
v0.4 — Windows 预览版
```

---

### License

If no license has been selected yet, write:

```text
License: TBD.
```

Do not claim an open-source license unless a `LICENSE` file exists.

---

### Do Not

Do not include:

* old Memo → Ticket → SOP / Brief / Card pipeline
* old CustomTkinter stack
* old `.spec/` references
* old commands from the deleted codebase
* claims that the app is production-ready
* fake install commands
* marketing hype
* AI-first positioning

---

### Verification

After README rewrite:

```bash
git status
git diff README.md READMECN.md
```

Expected:

```text
Only README.md and READMECN.md changed.
No source code changed.
No dependency file changed.
```

Suggested commit:

```bash
git add README.md READMECN.md
git commit -m "docs: rewrite project readme"
```
