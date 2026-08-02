# keikeu Road v0.6 Product Boundary

> Authority: approved Road v0.6 product scope and author-asset constraints. The detailed Paper v4 grammar, DTOs, migration, recovery, and protocol contract live in the approved [Paper v4 design](design/road-v0-6-paper-v4-design.md). Current runtime coordinates live in [PROJECT](PROJECT.md).

## 1. Definition

keikeu is a private, local-first pre-writing and writing-focus tool for a single fanfiction author.

```text
existing inspiration → editable card-page Paper → saved Paper → external prose editor
```

The author now leaves keikeu with the Paper itself. There is no separate Flashcard product step in the Road v0.6 target.

## 2. Author control

- Markdown remains the durable, readable, repairable author asset.
- Rebuildable indexes and device state are auxiliary, never canonical creative content.
- keikeu must not silently rewrite, normalize, delete, overwrite, upload, merge, score, or train on author text.
- The author chooses the Vault and external prose editor.
- No account, cloud backend, telemetry, hidden remote service, or background sync is authorized.
- Damaged Paper Markdown is reported, not silently repaired or partially opened as an editable Paper.

## 3. Current runtime boundary

CP4 has activated the Road v0.6 product/data contract without changing the process architecture:

```text
Vue → Tauri/Rust → JSONL protocol v2 → Python service/core
    → Paper v4 Markdown / Index / Vault → Paper pages
```

CP0–CP3 added the contracts, Core, migration/Index, and development-only UI. CP4
performed the single vertical protocol-v2 switch. CP5 removed the unreachable legacy
normal-runtime code without changing this product behavior. `PROJECT.md`, source, and tests
remain the authority for the current checkpoint.

## 4. Paper v4 target behavior

- A Paper has a stable optional display name, ordered Tags, and at least one ordered card page.
- Every page has an always-editable optional title, author Markdown content, and optional type: `summary`, `snapshot`, `whisper`, or `null`.
- Display labels are fixed: 总结、高光、碎碎念; `null` displays no label.
- A Paper has at most one Summary page. Snapshot and Whisper pages are unlimited.
- Basic mode and further mode are presentation only. Switching modes never clears a page title, content, or hidden type.
- A saved page must have a non-empty title or content containing at least one non-whitespace character. The whitespace check never rewrites content.
- Paper and page names trim outer whitespace only, become `null` when empty, allow at most 200 Unicode code points, and reject control, surrogate, and line-separator characters.
- Tags are single-line values; comma is ordinary content. Normal v4 editing trims, drops empty values, and keeps the first trimmed duplicate without normalizing author text.

The exact Markdown v4 shape, frontmatter scalar codec, page markers, reversible marker escaping, Tags grammar, and strict failure rules are defined only in [the approved design §8](design/road-v0-6-paper-v4-design.md#8-markdown-schema-v4).

## 5. Accepted interaction target

- The default Paper editor is one large card page, not a Summary form followed by a render step.
- The Paper display name and current page title remain editable in both basic and further modes.
- The card bottom exposes exactly three primary actions: 保存, 删除, 加一页.
- 加一页 splits the current page content at the actual caret or selection, preserves the prefix on the current page, moves the suffix to a new untitled/untyped page, and focuses the new page title. If the body was never focused, the split point is the end.
- 删除 removes the current page after confirmation. Deleting the only page replaces it with one blank page; a Paper never has zero pages.
- Page-number buttons switch pages. Road v0.6 does not add page reordering or page deep-links.
- Save is one whole-Paper compare-and-swap operation. A successful Markdown replacement advances the baseline even when disposable Index update fails.
- Dirty departure protection covers Paper/Vault switching, navigation, and normal close. Known failure preserves the draft; stale or unknown results never trigger an automatic retry.
- Library projects the whole Paper, searches all pages locally, previews the first page, and always opens the whole Paper at page 1.

## 6. Recovery and migration

- `repair_required` is a tagged successful domain result with separate ordinary-open and unknown-save ownership; it never exposes damaged prose in diagnostics.
- `commit_unknown` freezes the affected durable intent. `paper.save` recovers only through read-only `paper.reconcile_save`; all other mutations use their declared read-only refresh/inspect path and are never automatically replayed.
- `index_degraded` means the author-file mutation is known successful while the disposable Index is not current. It must not roll back or re-send the author mutation.
- v2/v3 → v4 migration may discard only `initial_summary`, and only under the approved migration contract with a complete external backup.
- Legacy Tags containing multiline/control characters, empty items, outer whitespace, or trim-collisions block preflight rather than being silently normalized.
- Raw loss-audit, full preflight, Home-contained backup outside the active Vault, regular-file manifest and byte verification, isolated staging, per-file safe replacement, and mixed-schema resume are required.
- Migration, delete, recovery, and failure experiments use fixtures, synthetic Vaults, or complete copies before any separately authorized real-Vault operation.

## 7. Architecture boundaries

- Vue owns visible state, draft/baseline, active page, and App-root pending intent; it never reads or writes author files.
- Rust owns desktop lifecycle, one Python sidecar, the JSONL queue, native directory selection, and validated system actions; it never parses Markdown or implements product rules.
- The transport-agnostic Python service owns orchestration and strict DTOs. `keikeu_core` owns domain validation and file rules without GUI or transport imports.
- `markdown_io.py` exclusively owns Paper Markdown. `vault.py` owns containment and destructive filesystem rules. Index data is local and rebuildable.
- No localhost, HTTP, WebSocket, account, telemetry, upload, hidden service, or automatic mutation replay is authorized.

## 8. Explicit exclusions and platforms

No AI generation, prose editor, sync, account, community, database, file watcher, Router, Pinia, TypeScript, UI kit, auto-save, page reorder, signing, notarization, staple, DMG, public distribution, mobile implementation, or cross-platform build enters Road v0.6.

- macOS Apple Silicon is the only Road v0.6 engineering and first-author platform. Intel Mac is unsupported.
- iOS/iPadOS remain a separate 2026-08 direction; Android/HarmonyOS a separate 2026-Q4 direction; Windows a 2027 direction.
- Linux and watchOS have no planned support. The iOS-only second user does not enter v0.x acceptance and returns no earlier than a separately designed iOS+Android v1.0.
- Developer ID distribution work is deferred to Road v0.8.

## 9. Acceptance gates

1. **Checkpoint engineering:** CP0–CP6 each produce their declared implementation, checks, smoke, and evidence with no unresolved P0/P1. Their developer exit judgments are covered by advance YOLO; evidence may not be invented or copied forward.
2. **Current/target integrity:** CP0–CP3 kept production v0.5/protocol v1; CP4 alone activated the complete v4/v2 vertical path; CP5 removed only code proven unreachable.
3. **Safety integration:** CP6 exercises unknown-result ownership, strict repair states, Index verification, migration and path-mutation recovery, and the Chinese repair manual using synthetic data or complete copies.
4. **Product acceptance:** CP7 separately requires the first author's real workflow. It is not part of CP6 engineering completion and needs separate real-Vault authorization.
5. **Road closeout:** CP7 acceptance, snapshot, tag, push, signing, packaging, and release are separate decisions.
