# keikeu Product Specification

> Authority: Road v0.3 product purpose, users, durable objects, user-visible behavior, non-goals, and acceptance. Current implementation state is tracked in [PROJECT](PROJECT.md); runtime facts are proven by `src/` and `tests/`.

## 1. Definition

keikeu is a private, local-first pre-writing and writing-focus tool for a single fanfiction author.

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

keikeu organizes existing inspiration. It does not generate inspiration, ghostwrite prose, or host the finished work.

## 2. Primary user

The primary user writes alone, keeps work private, prefers inspectable local files, and needs a light bridge from fragments to prose rather than a project-management system.

Heavy planners, teams, marketplaces, community operators, and AI-generation users are not primary targets. Optional Outline work may be explored later without blocking the core flow.

## 3. Author asset contract

- Paper Markdown is durable, readable, and repairable with ordinary text tools.
- `keikeu_index.json` is disposable metadata and can be rebuilt.
- Device state is disposable, outside the Vault, and stores only the last daily-card date.
- keikeu never silently summarizes, rewrites, normalizes, judges, uploads, merges, or overwrites creative text.
- The author-saved current Summary is authoritative; the first successful save freezes a read-only initial copy.

## 4. Paper

One Paper is one work unit intended to become prose. It stores:

1. an optional display name;
2. a required current Summary;
3. ordered optional Highlights, each with optional display name and required content; and
4. flat optional Tags.

It also stores a stable neutral code, frozen first-save Summary, timestamps, optional preserved legacy title, and feasible unknown frontmatter.

Paper does not contain creative-progress status, linked Outline, fixed fandom taxonomy, prose body, task state, or completion percentage.

### Required behavior

- A new code follows `K-YYYYMMDD-NNN`, is unique across active and Trash paths, and becomes immutable after creation. There is no code-rename action.
- Paper and Highlight display names trim outer whitespace; blank becomes `None`. A nonblank name is one line, at most 200 Unicode code points, and contains no control characters. Unicode, emoji, punctuation, and duplicate display names are allowed.
- Names are stored exactly as trimmed author input. Comparison and sorting use `unicodedata.normalize("NFC", value).casefold()` without silently rewriting disk text.
- A blank Summary blocks saving and leaves the prior disk version unchanged.
- First save copies Summary into the immutable initial Summary. Later saves preserve that copy.
- A Highlight with blank content is omitted together with its name. Remaining Highlights preserve author order.
- Highlight drag handles have a keyboard-reachable menu with equivalent **上移** and **下移** actions. Reordering produces no toast.
- Tags trim outer whitespace and remove exact duplicates while preserving first appearance.
- Empty Highlights and Tags save successfully with non-blocking guidance.
- External deletion, movement, or modification must not be silently overwritten.

### Durable shape

```markdown
---
type: paper
schema_version: 3
code: K-20260721-001
display_name: 雪中的无人车
created: 2026-07-21T10:30:00
updated: 2026-07-21T10:45:00
---

# K-20260721-001

## 初稿副本

[first saved Summary]

## Summary

[current Summary]

## Highlights

1. 名称：车轮痕迹
   内容：
   [ordered multiline anchor]

## Tags

- [flat tag]
```

Empty optional sections keep their headings. Schema v2 remains readable as unnamed Highlights; the next successful save writes v3. Mixed v2/v3 Vaults are supported and never silently bulk-rewritten.

## 5. Flashcard

Flashcard is a read-only projection:

```text
cards = [current Summary] + ordered Highlight content
```

It supports Paper selection, a clickable card list, previous/next buttons, left/right arrows, a bounded numeric page jump, temporary Summary context on Highlight cards, and return to Paper.

Every open, Paper switch, and app restart begins on page 1. Position is not persisted. Invalid jumps do not move; first/last-edge attempts do not wrap and produce a short non-modal message.

Flashcard never edits content, previews adjacent cards, records completion, accepts prose, or tracks writing progress.

## 6. Library and folders

Library is a local retrieval surface. It supports:

- fixed scopes for all Papers, unfiled Papers, one-level folders, and Trash;
- search within the current scope by display name, code, Summary, Tags, and Highlight names;
- sorting by display name, updated time, or created time;
- dense Paper rows, single drag or menu move, selection, and batch move;
- branch copy from the saved disk version with a new code and timestamps;
- open Paper or Flashcard, system-open Markdown, reveal, refresh, and index rebuild; and
- Paper/folder soft-delete, restore, and explicit permanent deletion with per-item results.

Folders are real directories directly under `cache/`. Folder names trim outer whitespace and must be one line, 1–200 Unicode code points, contain no control characters, and exclude `/`, `:`, `.`, `..`, leading `.`, and reserved names `cache`, `.trash`, `keikeu_index.json`, `全部 Paper`, `未归类`, and `Trash` under NFC+casefold comparison.

Folders may be empty. Deeper directories and symlinks are errors that keikeu reports but does not write through. Externally created duplicate codes are preserved and reported; mutations involving them are blocked until the author resolves them.

Library is not a board, deadline tracker, graph database, world-building system, or Finder clone.

## 7. Vault, path, and network boundary

```text
vault/
  cache/
    <code>.md
    <folder>/<code>.md
  .trash/cache/
    <code>.md
    <folder>/<code>.md
  keikeu_index.json

device-local, under the current user's Home:
  config                 selected Vault
  state                  last_daily_card_date only
```

Durable Vault, config, state, and interactive smoke writes must resolve to the current user's Home or a descendant. Symlink escape, another user's Home, `/Volumes`, application bundles, `/tmp`, `/private/tmp`, and `/var/folders` are rejected for durable writes.

keikeu has no account, cloud backend, telemetry, provider API, hidden service, or background sync. An OS-exposed iCloud Drive, Dropbox, or OneDrive directory is an ordinary path only when it satisfies the Home boundary. Availability, transfer, and conflicts remain provider responsibilities; conflict copies are unknown files and are never auto-merged.

Road v0.3 does not claim Apple App Sandbox protection. Application-level Home checks remain mandatory until a separately reviewed distribution phase enables and verifies sandbox entitlements.

## 8. Vault switching, migration, and recovery

Vault switching classifies a candidate before changing config: valid Vault, empty directory requiring confirmation to initialize, or non-empty non-Vault rejection. A valid switch previews Paper count; config changes atomically only after validation.

If selected config points outside Home, keikeu immediately stops writes and first classifies the source read-only. Relocation never follows or dereferences symlinks: it copies only ordinary directories and regular files into a new Home-contained destination. Any symlink or unsupported/special entry reports an error and aborts relocation with the source and config untouched. Before format-specific validation, the copy's regular-file manifest and bytes must match the source.

For a v2/v3 copy, keikeu additionally parses every supported Paper and rebuilds and validates the index before atomically switching config. A v0.1 copy is never parsed as v2/v3 first: the existing read-only v0.1 preflight and manifest validation run on the safe copy, config switches atomically to that copy, and only then may the existing explicit migration gate run there. That migration creates a full backup outside the active Vault but still under Home, converts in isolated staging, validates every Paper, atomically swaps, retains the report and backup, and removes old active Outline only after success. Cancellation or migration failure leaves config on the unmodified safe v0.1 copy; the unsafe source remains untouched. Migration staging cleanup may remove its own isolated generated tree; active Trash and permanent-delete flows never use recursive deletion.

Restore never overwrites another asset or changes a historical code. An active code conflict blocks that item. Folder restore may merge into an existing same-name folder; non-conflicting items succeed and conflicts remain in Trash with per-item reports.

Permanent deletion accepts only explicit validated Paper paths. It unlinks each Paper, then uses `rmdir` only for a verified-empty directory. One to three Papers require confirmation; four or more require trim-exact lowercase `execute`.

## 9. Daily start and keyboard

Each device shows one built-in encouragement card on the first launch of each local calendar day. Immediately before display, it atomically records that date; after three seconds, Enter, or **开始写**, it opens a blank Paper. Missing or corrupt state means not yet shown today and never affects Vault content.

Core keyboard paths are `Cmd+S`, `Cmd+F`, Flashcard left/right arrows, `Esc`, and standard Tab/Shift+Tab/Enter/Space. Every drag action has a keyboard-reachable menu equivalent.

## 10. Platform allocation

- **macOS:** Road v0.3 acceptance platform for Paper, one-level Library, Flashcard, migration, recovery, Vault switching, and OS file services.
- **iPhone:** Phase 7.5 remains an independent lightweight quick-test build using an app-sandbox local Vault. It is not a Road v0.3 gate.
- **iPad:** future Paper/Library plus Flashcard beside an external editor using system multitasking.

All platforms use the same Paper model. keikeu never reads the external prose document.

## 11. Explicit non-goals

- AI summary, rewriting, continuation, ranking, evaluation, or external corpus
- built-in prose editor, chapter manager, mandatory Outline, or cross-Paper deck
- keikeu cloud, account, sync engine, collaboration, telemetry, or background watcher
- social feed, publishing, marketplace, or public author/work database
- graph/world-building database, canvas, timeline, scene board, or complex taxonomy
- nested folders, folder manual ordering, aliases, symlink assets, or external-volume Vaults
- plugin architecture, database/ORM, Repository/Service layer, event bus, or transaction framework

## 12. Acceptance

### Engineering evidence

Source inspection and direct tests must cover v2/v3 round trips, immutable codes, name boundaries, multiline Highlights, external-change refusal, Home/symlink guards, atomic config switch, copied unsafe-Vault relocation, one-level enumeration, global code conflicts, deterministic index rebuild with damaged-file isolation, partial batch results, explicit permanent-delete paths, Flashcard page-1 reset/jump/keyboard behavior, daily state, and v0.1 safe-copy-first migration.

Engineering completion, macOS workflow smoke, product acceptance, and Road tag/archive are separate conclusions.

### Product evidence

Road v0.3 acceptance requires de-identified real-author results for:

1. a new named Paper moving through folder retrieval, Flashcard selection/jump, and external-editor handoff; and
2. an existing v2 Paper across two sessions, including lazy v3 save, Refresh after an external Finder move, branch copy, Trash, and restore.

Unsafe relocation, destructive operations, and provider behavior are first exercised only on synthetic or copied Vaults. The record states whether retrieval is faster and clear, whether any P0/P1 occurred, and whether the external-editor handoff remains clear. No prose, inspirations, names, relationships, or Vault paths enter the record.

Only after P0/P1 is absent or fixed and reverified may the developer separately decide whether to tag or archive the Road. Supporting records live in [`acceptance/`](acceptance/README.md).
