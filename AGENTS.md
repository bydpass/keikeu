# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Repo status

Pre-code repository. `main` has zero commits, no source files, no package manifest, no build / test / lint tooling. The only artifacts are spec documents under `.spec/`. **Read `.spec/keikeu_SPEC_v0.md` before doing anything else** — it is the product source of truth.

## What keikeu is

keikeu is a fanwork *idea → brief* tool for shippers and fic-commissioners.

- **Input** — a single field labeled **饼胚** (*peibei*, "raw dough"): a shipping ramble, scene craving, AU premise, plot seed, or unshaped fandom thought.
- **Output** — that one input fans out into three Markdown views: a self-use **SOP**, a commission **Brief**, and an inspiration **Card**.
- **Slogan** — *Turn "I want to see this" into "here is how to write / commission / display it."*

## Product invariants

These hold regardless of which GUI framework or packaging strategy gets chosen later.

1. **饺子醋 (*jiaozicu*, "dumpling vinegar") is the anchor.** It is the must-see moment the user actually craves. Every structured output exists to preserve it. Never flatten it into a generic outline.
2. **One input, three windows.** SOP, Brief, and Card all derive from the single 饼胚 field. Do not split the flow into separate inputs.
3. **GUI must be caveman-usable.** End users should not need CLI, Python knowledge, or config editing. Open → type → click → copy Markdown.
4. **Not an AI ghostwriter.** keikeu structures briefs, not prose. Do not generate full fiction; preserve the user's voice and craving.
5. **Hard out-of-scope (do not propose):**
   - accounts
   - cloud sync
   - community publishing
   - commission marketplace
   - payments
   - image generation
   - multi-user collaboration
   - world-building DB
   - full-text generation
   - copyright / platform moderation

## Tech stack (locked by TECH SPEC v0.1)

@.spec/techspec.md

Concrete decisions already locked:

- **Language:** Python, ≥3.11 and <3.14.
- **GUI:** a simple desktop GUI. Framework not yet picked.
- **Generator:** local mock / rule-based. No external AI API in v0.1.
- **Storage:** no database. Markdown can be saved manually or copied to clipboard.
- **Data flow:** `raw idea → KeikeuSpec → SOP Markdown / Brief Markdown / Card Markdown`. `KeikeuSpec` is the in-memory product data type.

## Open implementation decisions

TECH SPEC v0.1 deliberately leaves these unresolved:

- GUI framework (e.g. Tkinter, PySide6, Flet, web shell).
- Packaging and distribution (PyInstaller, Briefcase, plain `pip`, etc.).
- File layout and module breakdown.

Picking a GUI framework is the natural first step before writing any code. If asked to "just try something" with no framework decision yet, confirm that means picking one now.

## Commands

None defined yet. Populate this section once a GUI framework is picked and build / test tooling is added.

## Terminology

| Term | Role |
|---|---|
| 饼胚 (*bingpei*) | The raw idea blob the user types into the single input field. |
| 饺子醋 (*jiaozicu*) | The must-see moment that anchors the whole brief. Non-negotiable. |
| 饺子 (*jiaozi*) | The supporting plot/structure built around the 饺子醋 to make it land. |
| SOP | Self-use writing SOP (first of three output views). |
| Brief | Commission brief for handing to a writer or artist (second view). |
| Card | Inspiration card — compressed, shareable, archivable version (third view). |

## File pointers

- `.spec/keikeu_SPEC_v0.md` — product spec v0.1 (Chinese), authoritative.
- `.spec/techspec.md` — TECH SPEC v0.1 (English), locks Python version, GUI direction, generator strategy.
- `.spec/IO_example.md` — minimal I/O example showing what a 饼胚 looks like in / structured plan out.
- `.Codex/settings.local.json` — local Codex permissions (currently only `rtk ls *` and `rtk read *`).
