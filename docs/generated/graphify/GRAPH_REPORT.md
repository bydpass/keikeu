# Graph Report - src  (2026-07-18)

## Corpus Check
- Corpus is ~8,735 words - fits in a single context window. You may not need a graph.

## Summary
- 288 nodes · 696 edges · 13 communities (12 shown, 1 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 108 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Migration Transaction|Migration Transaction]]
- [[_COMMUNITY_Paper Markdown IO|Paper Markdown I/O]]
- [[_COMMUNITY_App Shell and Vault Gate|App Shell and Vault Gate]]
- [[_COMMUNITY_Paper Editor UI|Paper Editor UI]]
- [[_COMMUNITY_Paper and Flashcard|Paper and Flashcard]]
- [[_COMMUNITY_Vault Recovery|Vault Recovery]]
- [[_COMMUNITY_Index Projection|Index Projection]]
- [[_COMMUNITY_Device Local State|Device Local State]]
- [[_COMMUNITY_Library OS Handoff|Library OS Handoff]]
- [[_COMMUNITY_Legacy v0.1 Reader|Legacy v0.1 Reader]]
- [[_COMMUNITY_Page Package|Page Package]]

## God Nodes (most connected - your core abstractions)
1. `Paper` - 33 edges
2. `read_paper()` - 17 edges
3. `MigrationPreflight` - 17 edges
4. `str` - 16 edges
5. `Path` - 16 edges
6. `AppContext` - 15 edges
7. `LegacyCache` - 15 edges
8. `_convert_to_staged_vault()` - 15 edges
9. `migrate_v01_vault()` - 15 edges
10. `build_flashcard_page()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Control` --uses--> `AppContext`  [INFERRED]
  src/keikeu_app/pages/library_page.py → src/keikeu_app/main.py
- `Paper` --uses--> `Paper`  [INFERRED]
  src/keikeu_core/indexer.py → src/keikeu_core/models.py
- `bool` --uses--> `Paper`  [INFERRED]
  src/keikeu_core/indexer.py → src/keikeu_core/models.py
- `date` --uses--> `Paper`  [INFERRED]
  src/keikeu_core/markdown_io.py → src/keikeu_core/models.py
- `Share` --uses--> `AppContext`  [INFERRED]
  src/keikeu_app/pages/library_page.py → src/keikeu_app/main.py

## Import Cycles
- 1-file cycle: `src/keikeu_core/migration_v01.py -> src/keikeu_core/migration_v01.py`
- 1-file cycle: `src/keikeu_core/markdown_io.py -> src/keikeu_core/markdown_io.py`

## Communities (13 total, 1 thin omitted)

### Community 0 - "Migration Transaction"
Cohesion: 0.08
Nodes (51): LegacyCache, The small v0.1 Cache shape needed for one-way Paper conversion., _checkpoint(), _contains_legacy_cache_marker(), _convert_to_staged_vault(), _copy_full_vault(), _ensure_external_root(), _files_under() (+43 more)

### Community 1 - "Paper Markdown I/O"
Cohesion: 0.14
Nodes (35): date, _atomic_create_text(), _atomic_replace_text(), copy_paper_with_code(), _escape_scalar(), _format_frontmatter(), next_paper_code(), _paper_path() (+27 more)

### Community 2 - "App Shell and Vault Gate"
Cohesion: 0.09
Nodes (29): _build_migration_gate(), _build_shell(), _build_vault_picker(), _configure_window(), main(), keikeu Flet shell for the Paper v2 macOS flow.  The GUI only routes user actions, Show a no-write v0.1 preflight before allowing any v2 vault action., Open a desktop Vault chooser or create an iOS sandbox Vault. (+21 more)

### Community 3 - "Paper Editor UI"
Cohesion: 0.11
Nodes (33): Button, Container, OutlinedButton, build_paper_page(), Build a Paper create/edit page for ``open_path`` or a fresh Paper., Control, bool, Control (+25 more)

### Community 4 - "Paper and Flashcard"
Cohesion: 0.14
Nodes (21): AppContext, The active vault and page-navigation callbacks shared by GUI builders., Paper, A Road v0.2 writing unit without lifecycle state or Outline links., Validate durable fields and apply the spec's lossless list cleanup., build_flashcard_page(), _paper_path(), project_cards() (+13 more)

### Community 5 - "Vault Recovery"
Cohesion: 0.16
Nodes (22): _direct_asset_path(), _index_path(), init_vault(), is_vault(), list_trashed_papers(), Paper v2 vault layout, recovery bin, and local config resolution.  The user-sele, Restore a trashed Paper, requiring a new code only on active collision.      A n, Persist the selected vault path using the project's JSON style. (+14 more)

### Community 6 - "Index Projection"
Cohesion: 0.22
Nodes (20): _index_path(), _is_valid_index(), list_index_errors(), list_papers(), load_index(), _paper_entry(), Rebuildable v2 Paper metadata index.  The index is only a local projection of ac, Rebuild and return the v2 index from active Paper Markdown only. (+12 more)

### Community 7 - "Device Local State"
Cohesion: 0.27
Nodes (19): get_card_index(), load_card_positions(), move_card_position(), Disposable per-device UI state for the Flashcard page.  This module deliberately, Store a valid card position and return its clamped value., Move a remembered position after a successful explicit Paper rename., Read valid stored positions, treating every malformed shape as empty., Atomically replace the disposable state file without touching any vault. (+11 more)

### Community 8 - "Library OS Handoff"
Cohesion: 0.20
Nodes (18): build_library_page(), _open_command(), _open_with_system(), Paper Library: local search, asset health, recovery, and OS handoff., Return the platform command for opening a file with its default app., Return the platform command for showing a file in its file manager., Return the one native share sheet service for this app session., Open on desktop or hand one Paper to the iOS system share sheet. (+10 more)

### Community 9 - "Legacy v0.1 Reader"
Cohesion: 0.28
Nodes (12): Enum, LegacyCacheStatus, Frozen v0.1 Cache reader used only by the explicit migration module.  It intenti, Read one frozen v0.1 Cache without modifying it or parsing Outlines., The frozen status values present in v0.1 Cache frontmatter., _read_title(), read_v01_cache(), _split_document() (+4 more)

## Knowledge Gaps
- **12 isolated node(s):** `bool`, `Path`, `Theme`, `Page`, `bool` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Paper` connect `Paper and Flashcard` to `Migration Transaction`, `Paper Markdown I/O`, `Paper Editor UI`, `Index Projection`?**
  _High betweenness centrality (0.132) - this node is a cross-community bridge._
- **Why does `build_paper_page()` connect `Paper Editor UI` to `Paper Markdown I/O`, `App Shell and Vault Gate`, `Paper and Flashcard`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `build_flashcard_page()` connect `Paper and Flashcard` to `Paper Markdown I/O`, `Paper Editor UI`, `Device Local State`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `Paper` (e.g. with `date` and `_LegacyCache`) actually correct?**
  _`Paper` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ValueError` (e.g. with `_require_card_count()` and `_require_code()`) actually correct?**
  _`ValueError` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `MigrationPreflight` (e.g. with `LegacyCache` and `Paper`) actually correct?**
  _`MigrationPreflight` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Disposable per-device UI state for the Flashcard page.  This module deliberately`, `Read valid stored positions, treating every malformed shape as empty.`, `Atomically replace the disposable state file without touching any vault.` to the rest of the system?**
  _98 weakly-connected nodes found - possible documentation gaps or missing edges._