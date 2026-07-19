# ADR 0001: Split Normative Maps from Observed Runtime Facts

- Status: accepted
- Date: 2026-07-18
- Scope: repository documentation

## Context

keikeu had several long Markdown files that repeated product behavior, Git rules, current status, architecture, and design detail. Root README links pointed to old paths, archived Road material remained discoverable as if active, and agent cold starts required historical search.

The repository also needs visual explanations for layout, interaction states, modules, and data lifecycles. Plain Markdown is good for durable contracts but poor at demonstrating those systems.

## Decision

Use one authority per question:

- `docs/SPEC.md` — product contract and acceptance;
- `docs/RULES.md` — reviewable engineering, interaction, data, Git, and evidence rules;
- `docs/PROJECT.md` — current coordinates and navigation;
- `AGENTS.md` — agent work method only;
- `docs/design/*.html` — executable visual and interaction specimens;
- `docs/architecture/architecture.html` — intended module and lifecycle map;
- `src/` and `tests/` — observed runtime facts; and
- `docs/generated/` — rebuildable observations that never define intent.

Human-facing explanations live under `docs/manual/`. They may provide fuller narrative or teaching material, but must point back to the active authority and never redefine it.

Commit-bound records and frozen status pages move to `docs/archive/` and are excluded from cold-start navigation.

## Consequences

- README becomes a short map instead of a product encyclopedia.
- A status update changes `PROJECT.md`, not every document.
- Visual states can be inspected offline without adding a build system.
- Architecture claims link to actual source and tests.
- Generated tools may expose drift but cannot modify active authorities.
- Human manuals remain readable without becoming a second product, Git, or agent truth.
- Historical internal links may remain stale inside the read-only archive; active links must stay valid.

## Revisit when

Revisit only if the no-build HTML set becomes measurably harder to maintain than the duplication it removed, or if another format can preserve offline use, source anchoring, accessibility, and cold-start speed with less machinery.
