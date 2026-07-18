# Graphify Trial

> Status: bounded AST-only trial complete on 2026-07-18. Decision: retain this disposable snapshot; do not automate or treat it as authority.

## Authority boundary

This directory may contain only rebuildable observations such as `graph.html`, `graph.json`, and `GRAPH_REPORT.md`. Those files can describe imports, source links, isolated documents, and possible drift. They cannot define product scope, rename concepts, update `AGENTS.md`, or override [`architecture.html`](../../architecture/architecture.html).

## Trial scope

- scanned `src/` only: 19 Python files, about 8,735 detected words;
- excluded tests and docs because no Gemini semantic backend was configured and this task did not authorize extraction subagents;
- excluded author Vaults, build output, environments, Git internals, and `docs/archive/`;
- run manually; no watch process or Git hook;
- used deterministic AST extraction only: zero model input/output tokens.

This narrower trial is deliberate. Pretending an AST-only run understands product and documentation semantics would create false confidence.

## Outputs

```text
graph.html       interactive observed graph
graph.json       machine-readable nodes and edges
GRAPH_REPORT.md  compact audit report
```

- [`graph.html`](graph.html) — 288 nodes, 696 edges, 13 manually named communities.
- [`graph.json`](graph.json) — raw generated graph.
- [`GRAPH_REPORT.md`](GRAPH_REPORT.md) — generated report and suggested queries.
- [`vis-network.min.js`](vis-network.min.js) — pinned 9.1.6 browser runtime vendored because Graphify's export hardcodes a CDN.
- [`LICENSE-vis-network-MIT.txt`](LICENSE-vis-network-MIT.txt) — license for the vendored runtime.

The built-in benchmark estimated about 6.2× fewer tokens per structural query than reading the code corpus naively. This is a tool benchmark, not a keikeu performance or quality claim.

## Signal

- `Paper` is the most connected node with 33 edges, matching its role across Markdown, migration, index, Paper UI, and Flashcard.
- Migration, Markdown I/O, app shell, Vault recovery, index projection, device state, and Library formed recognizable communities.
- The observed import structure did not reveal Flet imports inside `keikeu_core`.

## Noise and drift audit

- Primitive/type nodes such as `str` and `Path` rank as highly connected.
- Inferred edges include `Paper → Paper` and `bool → Paper`, which are not useful architectural facts.
- The report labels self-references inside `migration_v01.py` and `markdown_io.py` as one-file import cycles.
- It reports 98 weakly connected nodes, many caused by docstrings and generic type symbols rather than actual missing architecture.

No architecture change is justified by this output. The manually maintained architecture map remains consistent with the useful structural signal.

## Adoption decision

Keep Graphify manual and on demand. Do not install a hook, run a watcher, scan private Vaults, or inject instructions into `AGENTS.md`. Revisit a broader scan only when a semantic backend can be used within project privacy constraints or AST filtering removes the current generic-type noise.

All generated files remain deletable and reproducible. Their absence is not a runtime failure. A future rebuild must replace Graphify's CDN script URL with the local pinned asset again before the offline gate can pass.
