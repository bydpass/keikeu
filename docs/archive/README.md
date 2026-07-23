# keikeu Documentation Archive

> **READ-ONLY HISTORY.** Nothing below this directory defines current product behavior, project status, engineering rules, or agent instructions. Start from [`README.md`](../../README.md) and [`docs/PROJECT.md`](../PROJECT.md).

## Why this exists

As part of the Road v0.3 preparation and next-Mac precursor, Phase 8.5 replaced overlapping root documents, Road notebooks, prototypes, and status pages with explicit active authorities and non-normative [human manuals](../manual/README.md):

- product contract → [`docs/SPEC.md`](../SPEC.md)
- current coordinates → [`docs/PROJECT.md`](../PROJECT.md)
- engineering and interaction constraints → [`docs/RULES.md`](../RULES.md)
- agent operation → [`AGENTS.md`](../../AGENTS.md)
- visual and interaction facts → [`docs/design/`](../design/)
- runtime structure → [`docs/architecture/`](../architecture/)

Archive files retain historical reasoning and evidence. Their internal links may point to superseded locations and are intentionally excluded from active-link validation.

## Collections

| Collection | Target commit and subject | Contents | Use |
| --- | --- | --- | --- |
| [`docs-clarify-export-cancellation-semantics/`](docs-clarify-export-cancellation-semantics/) | `9d033db` · `docs: clarify export cancellation semantics` | Road v0.1 records | historical comparison only |
| [`docs-agents-md-update/`](docs-agents-md-update/) | `146cb74` · `docs: AGENTS.md update` | Road v0.2 records | historical comparison only |
| [`docs-archive-documentation-reform-report/`](docs-archive-documentation-reform-report/) | `9114d63` · `docs: archive documentation reform report` | Phase 8 record and SOP before final author confirmation | historical acceptance evidence only |
| [`snapshots/`](snapshots/) | commit-bound status pages listed below | status and handoff HTML | frozen evidence only |
| [`planning/`](planning/) | supplied on 2026-07-18 | Phase 8.5 reform proposal | understand the migration decision, not current status |

## Snapshot files

| File | Target commit | Commit subject |
| --- | --- | --- |
| [`fix-support-ios-simulator-deployment.html`](snapshots/fix-support-ios-simulator-deployment.html) | `323b2a3` | `fix: support iOS simulator deployment` |
| [`fix-ios-create-sandbox-vault-on-device.html`](snapshots/fix-ios-create-sandbox-vault-on-device.html) | `73d3f90` | `fix(ios): create sandbox vault on device` |
| [`docs-finalize-documentation-reform.html`](snapshots/docs-finalize-documentation-reform.html) | `96567d2` | `docs: finalize documentation reform` |
| [`docs-stop-at-phase-8.html`](snapshots/docs-stop-at-phase-8.html) | `b31bbc4` | `docs: stop_@_phase_8` |
| [`feat-complete-road-v0-3-candidate.html`](snapshots/feat-complete-road-v0-3-candidate.html) | `2cc40ba` | `feat: complete Road v0.3 candidate` |

## Archive rule

Do not update a historical document to match current behavior. If history needs correction, add a dated note beside it. If a current authority is incomplete, fix the active authority rather than reviving an archive file.

Commit-bound archive directories and snapshot files use the target commit subject in kebab-case. Conventional type and scope words remain in the name; punctuation becomes a hyphen or a word such as `at`. Each archived directory or page retains the full target hash in its header or body.
