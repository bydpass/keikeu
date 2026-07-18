> **ARCHIVED — READ ONLY.** Historical README brief; current navigation lives in [`README.md`](../../README.md).

# README rewrite

Maintain:

```text
README.md      # Simplified Chinese
README_EN.md   # English
```

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

Both `README.md` and `README_EN.md` must include:

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
keikeu is a local-first fanfiction writing utility that turns existing inspiration into durable Markdown Papers and uses Flashcards to focus expansion.
```

Simplified Chinese:

```text
keikeu 是一个本地优先的同人写作辅助工具：把已有灵感整理成 Markdown 纸片，再用 Flashcard 帮作者聚焦扩写。
```

#### 2. Current status

Must clearly state:

```text
Road v0.1 is archived; the current code still implements the legacy Cache / Outline pre-alpha.
The target product contract is Road v0.2: macOS Paper / Flashcard Core.
The target follows appdesign.md, techpolicy.md, and memory/specs/spec_road_v0_2.md.
```

Chinese version should say:

```text
Road v0.1 已归档；当前代码仍实现旧 Cache / Outline pre-alpha。
目标产品契约是 Road v0.2：macOS Paper / Flashcard Core。
目标以 appdesign.md、techpolicy.md 与 memory/specs/spec_road_v0_2.md 为准。
```

#### 3. Core flow

Must include:

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

Chinese version:

```text
已有灵感 → Paper Markdown → Flashcard → 外部正文编辑器
```

#### 4. Product principles

Must include:

```text
- Local-first.
- Markdown files are user assets.
- keikeu_index.json is rebuildable metadata.
- No keikeu account, cloud backend, or background sync.
- User-selected OS file-service folders such as iCloud Drive are allowed.
- No external fandom / character / CP database.
- No AI ghostwriting or automatic rewriting of author text.
```

Chinese version:

```text
- 本地优先。
- Markdown 文件是用户资产本体。
- keikeu_index.json 是可重建的软件索引。
- 不做 keikeu 账号、云后端或后台同步。
- 允许用户选择 iCloud Drive 等系统文件服务目录。
- 不接入外部 fandom / 角色 / CP 数据库。
- 不使用 AI 代写或自动改写作者文字。
```

#### 5. What keikeu is

Must include:

```text
- Markdown Paper tool
- Flashcard writing-focus view
- local Markdown vault tool
- pre-writing utility for fanfiction authors
```

Chinese version:

```text
- Markdown 纸片工具
- Flashcard 写作聚焦界面
- 本地 Markdown vault 工具
- 面向同人小说作者的写前辅助工具
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
- full prose editor
```

Chinese version:

```text
- AI 代写工具
- 社交平台
- 约稿交易平台
- fandom 数据库
- Obsidian / Notion 替代品
- 云端写作套件
- 完整正文编辑器
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
appdesign.md        product design source of truth
techpolicy.md       technical policy
gitspec.md          Git workflow for humans
gitagent.md         Git workflow for agents

memory/specs/
  spec_road_v0_2.md      active behavior specification
  planbook_road_v0_2.md  macOS-first execution handbook

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
appdesign.md
```

as product design source of truth.

Mention:

```text
techpolicy.md
```

as technical stack and implementation policy.

Mention:

```text
gitspec.md
```

as human Git workflow manual.

Mention:

```text
gitagent.md
```

as agent Git workflow rules.

---

### Roadmap

Use the current release route:

```text
v0.1 — archived macOS Cache / Outline pre-alpha
v0.2 — macOS Paper / Flashcard Core
later — iPhone / iPad file-service parity
Pre-Advance — optional Markdown Outline
later still — Android / Windows
```

Chinese version:

```text
v0.1 — 已归档的 macOS Cache / Outline pre-alpha
v0.2 — macOS Paper / Flashcard Core
后续 — iPhone / iPad 文件服务对齐
Pre-Advance — 可选 Markdown Outline
更后 — Android / Windows
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
