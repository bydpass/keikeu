# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo status

**v0.1 shipped** (commit `15f73a7`, Version_Hana), then **realigned to the neo spec** (neo-0.1): the product is reframed as a 3-function pipeline 灵光池(Memo) → 配方票(Ticket) → 试药包(ReviewKit), and the shipped code was renamed to that vocabulary (`KeikeuSpec`→`Ticket`, added `Memo`; `generate_spec`→`make_ticket`). Shipped surface = Memo capture + Ticket with SOP/Brief/Card output modes (CustomTkinter GUI, rule-based generator, 9 passing tests). **ReviewKit is roadmap v0.2 — not built.** Authoritative spec: `.spec/keikeu_SPEC.md`. Ship log: `tasks/task001-checkpoint.md`.

## What keikeu is

keikeu is a fanwork pre-writing tool — the *幽灵助手* (ghost assistant) of a 同人药剂师. It listens to inspiration, structures it into an executable recipe, and (later) produces a review kit. It does **not** write the work for you.

Pipeline: **灵光池(Memo) → 配方票(Ticket) → 试药包(ReviewKit)**.

- **Memo (灵光池)** — low-friction capture of a raw idea: a shipping ramble, scene craving, AU premise, plot seed, unshaped fandom thought. Preserve the user's words; do not interrogate or flatten. (Legacy name 饼胚 = a Memo's raw input.)
- **Ticket (配方票)** — the core: one Memo is structured into an executable brief. The Ticket fans out into three Markdown output modes: a self-use **SOP**, a commission **Brief**, and an inspiration **Card**.
- **ReviewKit (试药包)** — v0.2: after the author writes a prototype draft, generate critique materials (an AI `skill.md`, a human beta-reader sheet, a revision log). Analyze only; never rewrite by default.
- **Slogan** — *别让好灵感烂在仓库里 — turn "I want to see this" into "here is how to write / commission / display it."*

## Product invariants

These hold across all versions.

1. **饺子醋 (*jiaozicu*, "dumpling vinegar") is the anchor.** It is the must-see moment the user actually craves. Every structured output exists to preserve it. Never flatten it into a generic outline.
2. **One Memo, one Ticket, three modes.** SOP, Brief, and Card all derive from a single Memo via one Ticket. Do not split capture into multiple inputs.
3. **GUI must be caveman-usable.** End users should not need CLI, Python knowledge, or config editing. Open → type → click → copy Markdown.
4. **Not an AI ghostwriter.** keikeu structures briefs, not prose. Do not generate full fiction; preserve the user's voice and craving. ReviewKit analyzes; it does not rewrite by default.
5. **Hard out-of-scope (do not propose):**
   - accounts / login
   - cloud sync / mobile sync
   - community publishing, comments, rankings (CP 热榜)
   - commission marketplace / payments
   - image generation
   - multi-user collaboration
   - world-building DB
   - full-text / auto-continuation generation
   - plugin system
   - copyright / platform moderation

## Tech stack (locked by TECH SPEC)

@.spec/techspec.md

Concrete decisions already locked:

- **Language:** Python, ≥3.11 and <3.14.
- **GUI:** CustomTkinter desktop app (locked; neo's "tkinter" wording is generic).
- **Generator:** local mock / rule-based. No external AI API in v0.1.
- **Storage:** no database. Markdown can be saved manually or copied to clipboard.
- **Data flow:** `raw idea → Memo → Ticket → SOP Markdown / Brief Markdown / Card Markdown`. `Memo` and `Ticket` are the in-memory product data types (`Ticket` is the structured brief; `KeikeuSpec` was its pre-neo name).

## Open implementation decisions

TECH SPEC v0.1 deliberately leaves these unresolved:

- Packaging and distribution (PyInstaller, Briefcase, plain `pip`, etc.).
- Whether to add a real LLM-backed generator behind a strategy boundary post-v0.1.

GUI framework is now locked: **CustomTkinter** (per Task 001).

## Commands

Setup (requires Python 3.11–3.13; Homebrew users may need `brew install python-tk@3.13`):

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .
```

Run the GUI:

```bash
.venv/bin/python -m keikeu.app
```

Run tests:

```bash
.venv/bin/python -m pytest        # all tests
.venv/bin/python -m pytest tests/test_generator.py::test_empty_input_raises  # single test
```

Regenerate `examples/output_sample.md` from `examples/bug_cp.txt`:

```bash
.venv/bin/python -c "
from pathlib import Path
from keikeu.generator import make_ticket
from keikeu.renderers import render_sop, render_brief, render_card
raw = Path('examples/bug_cp.txt').read_text(encoding='utf-8')
ticket = make_ticket(raw)
out = '\n\n---\n\n'.join([render_sop(ticket), render_brief(ticket), render_card(ticket)])
Path('examples/output_sample.md').write_text(out, encoding='utf-8')
"
```

## Terminology

| Term | Role |
|---|---|
| Memo (灵光池) | The captured raw idea blob (`Memo.raw`). Low-friction; preserve verbatim. |
| 饼胚 (*bingpei*) | Legacy alias for a Memo's raw input. |
| Ticket (配方票) | The structured brief generated from a Memo. In-memory type `Ticket`. |
| 饺子醋 (*jiaozicu*) | The must-see moment that anchors the whole brief. Non-negotiable. (`Ticket.jiaozi_cu`) |
| 饺子 (*jiaozi*) | The supporting plot/structure built around the 饺子醋 to make it land. (`Ticket.jiaozi`) |
| ReviewKit (试药包) | v0.2 critique materials (skill.md + human beta sheet + revision log). Not built. |
| SOP | Self-use writing SOP — Ticket output mode 1. |
| Brief | Commission brief for a writer/artist — Ticket output mode 2. |
| Card | Inspiration card, compressed/shareable — Ticket output mode 3. |

## File pointers

- `.spec/keikeu_SPEC.md` — product spec (neo-0.1, Chinese), authoritative.
- `.spec/techspec.md` — TECH SPEC (neo-0.1, English), locks Python version, CustomTkinter, generator strategy, real `src/` layout.
- `.spec/IO_example.md` — I/O shapes for Memo / Ticket / ReviewKit.
- `.claude/settings.local.json` — local Claude permissions (currently only `rtk ls *` and `rtk read *`).
