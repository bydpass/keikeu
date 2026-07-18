# keikeu Product Specification

> Authority: product purpose, users, scope, durable objects, user-visible behavior, non-goals, and product acceptance. Runtime implementation is proven by `src/` and `tests/`.

## 1. Definition

keikeu is a private, local-first pre-writing and writing-focus tool for a single fanfiction author.

It serves the moment when inspiration already exists but has not yet become stable prose:

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

keikeu organizes existing inspiration. It does not generate inspiration, ghostwrite prose, or host the finished work.

## 2. Primary user

The primary user:

- writes alone and keeps work private;
- prefers local, inspectable files;
- already has fragments, images, dialogue, or scenes in mind;
- needs a light bridge into prose, not a project-management system;
- writes one-shots and short/medium work first; and
- wants final authority over every word.

Heavy planners, teams, marketplaces, community operators, and AI-generation users are not primary targets. Long-form and optional Outline work may be explored later without blocking the core flow.

## 3. Author asset contract

Author assets belong to the author.

- Paper Markdown is durable, readable, and repairable with ordinary text tools.
- `keikeu_index.json` is disposable metadata and can be rebuilt.
- Flashcard position is disposable per-device state outside the Vault.
- keikeu never silently summarizes, rewrites, normalizes, judges, uploads, or merges creative text.
- The author-saved current Summary is authoritative; the first successful save also freezes a read-only initial copy.

## 4. Paper

One Paper is one work unit intended to become prose. Its durable creative fields are:

1. **Summary** — required current expression of the work's spark.
2. **Highlights** — ordered optional writing anchors; each becomes one Flashcard.
3. **Tags** — flat optional search labels.

It also stores a stable neutral code, the frozen first-save Summary, creation/update timestamps, optional preserved legacy title, and feasible unknown frontmatter.

Paper does not contain a title field, creative-progress status, linked Outline, fixed fandom/relationship taxonomy, prose body, task state, or completion percentage.

### Required behavior

- A blank Summary blocks saving and leaves the prior disk version unchanged.
- First save copies Summary into the immutable initial Summary.
- Later saves may edit current Summary but preserve the initial copy.
- Highlights preserve author order; blank items are omitted.
- Tags trim outer whitespace and remove exact duplicates while preserving first appearance.
- Empty Highlights and Tags save successfully with non-blocking guidance.
- A new neutral code follows `K-YYYYMMDD-NNN`; changing a saved code is an explicit rename that cannot overwrite another file.
- External deletion, movement, or modification must not be silently overwritten.

### Durable shape

```markdown
---
type: paper
schema_version: 2
code: K-20260713-001
created: 2026-07-13 17:30
updated: 2026-07-13 17:45
---

# K-20260713-001

## 初稿副本

[first saved Summary]

## Summary

[current Summary]

## Highlights

1. [ordered anchor]

## Tags

- [flat tag]
```

Empty optional sections keep their headings so the file remains predictable and hand-repairable.

## 5. Flashcard

Flashcard is a read-only projection, not another asset:

```text
cards = [current Summary] + ordered Highlights
```

It shows only the current card, `x / n`, previous/next controls, temporary Summary context on Highlight cards, and a return-to-Paper action.

It never provides card editing, adjacent-card previews, completion/skip state, prose input, or writing-progress tracking.

The last position is stored by Paper code on each device. Missing, corrupt, or out-of-range state falls back safely without changing Paper Markdown.

## 6. Library

Library is a local retrieval surface, not a project manager. It supports:

- search by Paper code, Summary, and Tags;
- open Paper or Flashcard;
- open Markdown through the operating system;
- reveal a file or Vault where the platform supports it;
- rebuild the index and isolate damaged Paper errors; and
- soft-delete and restore Paper without byte loss.

It does not provide boards, deadlines, progress filters, graph queries, world-building databases, or complex taxonomy management.

## 7. Vault and network boundary

```text
vault/
  cache/<paper-code>.md
  .trash/cache/
  keikeu_index.json

device-local, outside vault:
  config                 selected Vault
  state                  Flashcard positions
```

keikeu has no account, cloud backend, telemetry, provider API, hidden service, or background sync. A user-selected iCloud Drive, Dropbox, or OneDrive folder is treated only as an OS-exposed path. Availability, remote transfer, and conflicts remain provider responsibilities.

Core work must remain usable offline whenever files are locally available. Provider conflict copies are unknown files; keikeu never auto-merges creative text.

## 8. Migration and recovery

v0.1 migration is explicit and reversible once through an external backup:

1. inspect the old Vault without writing;
2. copy the full Vault to a timestamped location outside the active Vault;
3. convert Cache files in staging;
4. validate every converted Paper;
5. atomically switch only after all conversions pass;
6. remove old active Outline files only after validation; and
7. retain a readable report and the external backup.

Any failure leaves the old active Vault intact. Old blank inspiration cannot be guessed from title or notes. Old Outline is not converted or shown; it survives only in the backup.

Soft-deleted current Papers move under `.trash/cache/`. Restore cannot overwrite an active code; the user chooses a new code or cancels.

## 9. Platform allocation

- **macOS:** primary v0.2 acceptance platform; Paper, Library, Flashcard, migration, recovery, and OS file-service folders.
- **iPhone:** capture/edit Paper and full-screen Flashcard; current 7.5 work uses an app-sandbox local Vault while file-service access remains a later capability.
- **iPad:** future Paper/Library plus Flashcard beside an external editor using system multitasking.

All platforms use the same Paper model. keikeu never reads the external prose document.

## 10. Outline position

Outline is not part of Road v0.2. The current flow, navigation, new Vault, Paper save, Library, and Flashcard cannot depend on it.

An optional future Markdown Outline may support mixed or long-form writers, but it must be independently validated, remain subordinate to the Paper → Flashcard flow, and must not resurrect the v0.1 seven-field schema by default.

## 11. Explicit non-goals before acceptance

- AI summary, rewriting, continuation, ranking, or evaluation
- built-in prose editor or chapter manager
- keikeu cloud, account, sync engine, or collaboration
- social feed, publishing, marketplace, or public author/work database
- external fandom, character, relationship, or work corpus
- graph/world-building database, canvas, timeline, or scene board
- mandatory Outline generation or cross-Paper Flashcard deck
- analytics, profiling, telemetry, or covert background behavior

## 12. Acceptance

### Engineering evidence

Source inspection and tests must cover:

- required Summary and immutable first-save copy;
- stable Markdown round trips and explicit rename;
- rebuildable index with damaged-file isolation;
- safe delete/restore and external-change refusal;
- Summary-first Flashcard projection and local position fallback;
- explicit v0.1 preflight, external backup, staging, failure safety, and report;
- no reachable old Outline workflow; and
- ordinary local-folder and macOS provider-folder smoke.

Engineering evidence proves implementation behavior, not usefulness.

### Product evidence

Road v0.2 product acceptance requires de-identified real-author results for both:

1. one real one-shot flow: Paper → Flashcard → Paper → external editor; and
2. one short/medium workflow across two sessions, including Flashcard position and Paper/Flashcard navigation.

The record must state whether Summary-first feels natural, whether returning to Paper is frequent, whether any P0/P1 occurred, and whether the external-editor handoff is clear. Author prose, inspirations, names, relationships, and Vault paths must never enter the record.

Only after P0/P1 is absent or fixed and reverified may the developer decide whether to archive or tag the Road. The supporting record and safe procedure live in [`acceptance/`](acceptance/README.md).
