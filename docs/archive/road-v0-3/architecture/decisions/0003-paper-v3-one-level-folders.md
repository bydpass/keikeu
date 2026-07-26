> **ARCHIVE — READ ONLY.** Road v0.3 architecture decision; archived on 2026-07-25.

# ADR 0003: Use Paper v3 with One-Level Real Folders

- Status: accepted
- Date: 2026-07-22
- Scope: Road v0.3 Paper identity, Markdown, paths, index, Library, Flashcard, and Trash

## Context

Road v0.2 uses the Paper code as both durable identity and fixed `cache/<code>.md` location, stores Highlights as strings, and keeps Library flat. Real folders and named retrieval would make those assumptions conflict across Markdown, index, pages, Trash, and Flashcard.

Markdown must remain the author-owned fact source. The project has one filesystem implementation and no measured need for a database, storage interface, watcher, or general file manager.

## Decision

Paper schema v3 adds optional `Paper.display_name` and ordered `Highlight(display_name, content)` values. Code remains an immutable `K-YYYYMMDD-NNN` identity and filename. The reader accepts v2/v3, the writer emits v3 after an explicit save, and mixed Vaults are supported without bulk rewrite.

Names are single-line trimmed author text, at most 200 Unicode code points, with control characters rejected. Blank display names become `None`; folder names must be nonblank and also reject path separators, dot paths, leading dots, and documented internal/UI reserved names. NFC+casefold is used only for comparison and sorting.

Active and Trash Papers may live at the root or in one real directory below `cache/`. `vault.py` validates and enumerates supported paths and global codes; the app passes Vault-relative paths instead of deriving them from code. Index v3 stores path/folder and searchable Paper/Highlight names. Deeper directories and symlinks are visible errors and are never write targets.

Externally created duplicate codes are preserved and reported; keikeu blocks mutations involving them rather than silently renaming history. Drag is optional convenience: every move has a keyboard-reachable menu equivalent, including Highlight **上移/下移**.

## Alternatives considered

- **Keep code as mutable path identity:** rejected because folder moves and restores would keep reproducing fixed-path assumptions and state-key migration.
- **Use virtual folders in tags or index JSON:** rejected because the author could not inspect or repair organization in Finder and Markdown would cease to explain disk state.
- **Allow arbitrary nesting:** rejected because navigation, recovery, and destructive-operation rules would expand beyond the observed one-level need.
- **Add SQLite or a Repository/Service layer:** rejected because it creates a second fact source or a one-implementation abstraction without solving a measured problem.

## Consequences

- Markdown parsing, the v0.1 migrator, every index producer, and Flashcard projection must adopt the new Highlight shape together.
- Folder/path rules and code allocation move to one core seam; Markdown I/O still exclusively serializes Paper text.
- Branch copy can duplicate creative fields under a new code without copying system history.
- Trash, merge, restore, and permanent delete operate per explicit Paper path and report partial results.
- Linear scans remain acceptable; a 1,000-Paper probe informs later optimization without prebuilding a cache system.

## Revisit when

Revisit nesting only after repeated real workflows require hierarchy rather than preference. Revisit storage architecture only if measured local Markdown/index performance blocks the primary flow or a second approved storage backend actually exists.
