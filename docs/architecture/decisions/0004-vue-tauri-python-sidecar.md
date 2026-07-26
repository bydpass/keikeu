# ADR-0004: Vue/Tauri desktop shell with one Python sidecar

**Date**: 2026-07-25

**Status**: accepted
**Decider**: developer

## Context

Road v0.3 proved the product behavior and Python Core, but its Flet presentation layer is being replaced. The replacement must preserve local Markdown ownership, Home/path protections, failure semantics, and a runnable Flet rollback baseline while adding a browser-style frontend without exposing author files to JavaScript.

## Decision

Road v0.4 uses Vue 3/Vite JavaScript for visible UI, a narrow Tauri/Rust host for desktop lifecycle and validated platform actions, and one Rust-owned JSONL Python sidecar. A transport-agnostic Python application service is shared by Flet and the JSONL dispatcher; the existing Python Core remains the only owner of product and filesystem rules.

## Alternatives considered

### Keep Flet as the long-term desktop UI

- **Benefit:** no new language or process boundary.
- **Why not:** it does not deliver the approved frontend replacement and keeps current UI constraints.

### Let Vue call the filesystem or shell directly

- **Benefit:** fewer bridge methods.
- **Why not:** it duplicates Python safety rules and gives JavaScript authority over author assets.

### Expose Python through localhost HTTP or WebSocket

- **Benefit:** familiar web tooling.
- **Why not:** it adds ports, network permissions, discovery, shutdown, and security behavior that a local parent/child JSONL channel does not need.

## Consequences

### Positive

- Python Core, Markdown, indexes, and Vault layout remain reusable and manually repairable.
- Flet and Tauri can be compared through one application boundary.
- Vue receives narrow DTOs and cannot directly read or write author files.

### Negative

- Packaging spans Node, Rust, Python, Tauri, and PyInstaller.
- Sidecar lifecycle, protocol mismatch, lost responses, and session expiry require explicit handling.

### Risks

- Business rules may drift into Rust or Vue; Road v0.4 rules stop the checkpoint if this occurs.
- A mutation response may be lost after disk commit; mutations are never automatically retried and surface `commit_unknown`.
- Old-system support may be overstated; macOS 15.0+ is claimed only after the macOS 15.0 build and launch gate passes.
