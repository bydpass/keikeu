# keikeu Road v0.4 Product Boundary

> Authority: Road v0.4 product scope and author-asset constraints. Current runtime facts live in `src/` and `tests/`; current coordinates live in [PROJECT](PROJECT.md); execution order lives in the [Road v0.4 Planbook](../PLAN_revised.md).

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

Road v0.3 product acceptance and archival are complete. Its detailed product, visual, interaction, architecture, decision, and acceptance records are read-only history in the [Road v0.3 archive](archive/road-v0-3/README.md).

Road v0.4 replaces only the desktop presentation and local call boundary:

```text
current: Flet → Python Core → Markdown / Index / Vault
target:  Vue → Tauri/Rust → JSONL sidecar → Python application service
         → Python Core → Markdown / Index / Vault
```

The accepted Python/Flet implementation remains the runtime and rollback baseline until Gate A proves Tauri parity. Road v0.4 does not change Paper schema, Vault layout, Home containment, migration semantics, or the product flow.

## 4. Frozen behavior

Road v0.4 preserves every accepted Road v0.3 capability:

- Paper create/open/save, frozen initial Summary, named Highlights, Tags, branching, soft delete, and external-modification rejection.
- Summary-first Flashcard navigation that always starts at page 1.
- Folder-aware Library search/sort, batch operations, Trash, restore, permanent-delete gate, and partial results.
- Vault preview/init/switch/relocate and v0.1 migration with Home containment, copy verification, backup, staging, and explicit confirmation.
- External-editor open/reveal through a validated platform boundary.

The archived [Road v0.3 SPEC](archive/road-v0-3/SPEC.md) remains the detailed parity checklist. It is historical evidence, not an editable v0.4 source.

## 5. Architecture boundaries

- Vue owns visible state and interaction only. It never reads or writes author files.
- Rust owns the desktop lifecycle, one Python sidecar, the JSONL queue, native directory selection, and validated system actions.
- The transport-agnostic Python application service is shared by Flet and JSONL; it owns orchestration and opaque session state.
- `keikeu_core` remains independent of Flet, Vue, Tauri, Rust, JSONL, and stdout.
- Markdown remains canonical. No localhost, HTTP, WebSocket, account, telemetry, upload, or hidden service is authorized.
- Road work follows the [understanding gate](../RULE_FOR_UNDERSTANDING.md).

## 6. Explicit exclusions

No AI generation, prose editor, sync, database, file watcher, Router, Pinia, TypeScript, UI kit, signing, notarization, DMG, App Sandbox, mobile work, or cross-platform build enters Road v0.4.

## 7. Acceptance gates

1. **Gate A — Platform parity:** Tauri produces the same durable results, failure protections, and keyboard paths as Flet on synthetic/copied Vaults.
2. **Gate B — Visual reconstruction:** the approved editorial workbench direction is applied after parity, with independent visual evidence.
3. **Product acceptance:** de-identified real-author scenarios A/B and production bundle smoke pass with no unresolved P0/P1.
4. **Compatibility:** the same arm64 artifact is built and launched on macOS 15.0, then retested on the current workstation, before claiming macOS 15.0+.
5. **Flet retirement:** only after all prior gates may Flet code, tests, dependency, and GUI entry be removed. Tag, archive, commit, and push remain separate developer decisions.
