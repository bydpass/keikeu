# ADR 0002: Keep Durable Writes Inside the Current User Home

- Status: accepted
- Date: 2026-07-22
- Scope: Road v0.3 Vault, config, device state, migration, and smoke artifacts

## Context

Road v0.2 accepts a configured Vault path without a single durable-write boundary, and some test commands can default to operating-system temporary directories. Road v0.3 adds Vault switching and copied-legacy relocation, so a mistaken path or symlink escape could direct writes into another user, `/Volumes`, an application bundle, or a temporary location.

Apple App Sandbox is not yet enabled for the macOS build. Claiming sandbox protection now would be false, while enabling entitlements and durable provider access would widen this Road into a packaging and distribution project.

## Decision

All durable Vault, config, device-state, and interactive-smoke writes must resolve to the current user's `Path.home()` or a descendant. Core path checks resolve symlinks before containment checks; `/tmp`, `/private/tmp`, `/var/folders`, `/Volumes`, other users, and app bundles are not valid durable targets.

A configured Vault outside Home becomes read-only to keikeu and is classified without writing. Relocation does not follow or dereference symlinks: only ordinary directories and regular files are copied into a new Home-contained destination. Any symlink or unsupported/special entry aborts with an error and leaves the source and config untouched. The copy's regular-file manifest and bytes must match the source before format-specific validation.

For v2/v3, every supported Paper is parsed and the index is rebuilt and validated on the safe copy before config switches atomically. For v0.1, the safe copy instead receives the existing read-only v0.1 preflight and manifest validation; it is never parsed as v2/v3 first. Config then switches atomically to that safe copy, and only the existing explicit migration gate may migrate it. Cancellation or migration failure leaves the unmodified safe copy selected. The unsafe source is never written or deleted.

Automated tests use frozen synthetic inputs or copies under the ignored repository `tests/test-vault/` basetemp. Road v0.3 does not claim Apple App Sandbox protection.

## Alternatives considered

- **Continue accepting arbitrary paths:** rejected because convenience does not justify unbounded writes or symlink escape.
- **Enable Apple App Sandbox in this Road:** rejected because entitlements, signing, provider bookmarks, and distribution evidence are a separate platform capability.
- **Silently move an unsafe Vault:** rejected because location and source retention belong to the author.

## Consequences

- Path validation and selected-Vault config replacement become centralized core responsibilities.
- External-volume Vaults are intentionally unavailable in Road v0.3.
- Provider folders work only when the OS exposes them under Home; keikeu still does not manage sync.
- Relocation uses extra disk space and time, but entry-type, copy, or pre-switch validation failure leaves source bytes and config unchanged.
- Product copy must state the application-level boundary without implying OS sandbox protection.

## Revisit when

Revisit when formal macOS distribution requires App Sandbox, when a verified security review changes the boundary, or when a real external-volume workflow justifies a separately designed permission model.
