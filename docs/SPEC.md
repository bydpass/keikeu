# keikeu Road v0.5 Product Boundary

> Authority: accepted Road v0.5 product scope and author-asset constraints. Current runtime facts live in `src/` and `tests/`; current coordinates live in [PROJECT](PROJECT.md). The completed checkpoint history is summarized in the [Road v0.5 snapshot](archive/snapshots/road-v0-5.html).

## 1. Definition

keikeu is a private, local-first pre-writing and writing-focus tool for a single fanfiction author.

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

It organizes existing inspiration. It does not generate inspiration, ghostwrite prose, or host finished work.

## 2. Author control

- Markdown remains the durable, readable, repairable author asset.
- Rebuildable indexes and device state are auxiliary, never canonical creative content.
- keikeu must not silently rewrite, normalize, delete, overwrite, upload, merge, score, or train on author text.
- The author chooses the Vault and external prose editor.
- No account, cloud backend, telemetry, hidden remote service, or background sync is authorized.

## 3. Road objective and baseline

Road v0.4 completed the desktop presentation and local call-boundary replacement:

```text
retired baseline: Flet → Python Core → Markdown / Index / Vault
current runtime:  Vue → Tauri/Rust → JSONL sidecar
                  → Python application service
                  → Python Core → Markdown / Index / Vault
```

Road v0.5 keeps that architecture and makes the existing workflow calmer, clearer, and safer to operate. It does not change Paper schema, Vault layout, Home containment, migration semantics, or the product flow.

## 4. Accepted behavior

Road v0.5 preserves every accepted Road v0.4 capability:

- Paper create/open/save, frozen initial Summary, named Highlights, Tags, branching, soft delete, and external-modification rejection.
- Summary-first Flashcard navigation that always starts at page 1.
- Folder-aware Library search/sort, batch operations, Trash, restore, permanent-delete gate, and partial results.
- Vault preview/init/switch/relocate and v0.1 migration with Home containment, copy verification, backup, staging, and explicit confirmation.
- External-editor open/reveal through a validated platform boundary.

Road v0.5 adds these accepted interaction rules without expanding product scope:

- Paper Desk visibly separates editable name, Summary, Highlights, and Tags from the locked original draft.
- A successful save establishes the newest baseline. Save failure preserves the form and old baseline.
- Dirty navigation, Paper/Vault switching, and window close share one native two-choice departure guard: discard to the latest baseline or continue editing.
- Flashcard reads only the latest saved Paper, starts with Summary, then shows one Highlight per card.
- Library preserves scope, query, sort, active item, batch selection, and scroll only within the current process; Vault switch or runtime restart resets it.
- All pages share the Quiet Desk visual system. Paper, Flashcard, and Library context rails remain fixed in supported desktop layouts; long Flashcard lists scroll independently; overscroll bounce and scrollbar chrome are suppressed without disabling ordinary scrolling.

## 5. Architecture boundaries

- Vue owns visible state and interaction only. It never reads or writes author files.
- Rust owns the desktop lifecycle, one Python sidecar, the JSONL queue, native directory selection, and validated system actions.
- The transport-agnostic Python application service owns orchestration and opaque session state behind JSONL. During migration, Flet used the same service as the parity baseline.
- `keikeu_core` remains independent of Flet, Vue, Tauri, Rust, JSONL, and stdout.
- Markdown remains canonical. No localhost, HTTP, WebSocket, account, telemetry, upload, or hidden service is authorized.
- Road v0.5 changes no architecture boundary; its execution followed [RULES](RULES.md) and the completed [Planbook](../PLAN_revised.md).

## 6. Explicit exclusions

No AI generation, prose editor, sync, account, community, database, file watcher, Router, Pinia, TypeScript, UI kit, signing, notarization, DMG, public distribution, App Sandbox, mobile work, or cross-platform build enters Road v0.5.

## 7. Acceptance gates

1. **Checkpoint engineering:** CP0–CP7 each pass their declared focused checks and independent developer or advance-YOLO gate.
2. **Desktop UI evidence:** supported `1220×780` and `920×680` layouts remain reachable without horizontal overflow; desktop-dependent behavior receives isolated current-source Tauri evidence.
3. **Product acceptance:** two 30-minute dogfood rounds complete, the three most annoying issues are fixed and rechecked, and no unresolved P0/P1 remains.
4. **Final UI gate:** fixed rails, bounded Flashcard scrolling, hidden scrollbar chrome, and no-overscroll behavior pass the developer's final condition.
5. **Road closeout:** final checkpoint `d900953` is committed and the developer authorizes the separate read-only Road snapshot. Tag, push, signing, notarization, DMG, and distribution remain separate decisions.
