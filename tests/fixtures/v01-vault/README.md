# v0.1 migration fixture vault

This is a fully synthetic, static v0.1 vault used by the Road v0.2 migration
tests. It contains no user writing or copied local vault content.

| Asset | Purpose |
|---|---|
| `cache/2026-07-01-090000-a101-rain-platform.md` | Valid Cache with every legacy field, including an Outline link. |
| `cache/2026-07-02-090000-a102-blank-optional.md` | Valid Cache with empty optional fields. |
| `cache/2026-07-03-090000-a103-empty-raw.md` | Valid v0.1 Cache that must fail the v0.2 preflight because raw inspiration is empty. |
| `cache/2026-07-04-090000-a104-corrupt-status.md` | Damaged Cache with an invalid status; the v0.1 reader must reject it. |
| `outlines/2026-07-01-091000-b101-rain-platform-outline.md` | Valid active v0.1 Outline; it is backup-only after a successful v0.2 migration. |
| `.trash/outlines/2026-06-30-080000-b100-old-outline.md` | Valid historical Outline bytes that verify whole-vault backup coverage. |

`keikeu_index.json` is version 1 and deliberately lists all active assets.
Phase 2 must treat Markdown as authoritative and must not let this auxiliary
index hide a damaged Cache.
