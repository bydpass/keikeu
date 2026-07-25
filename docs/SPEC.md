# keikeu Product Boundary

> Authority: stable product purpose and author-asset constraints during the transition after Road v0.3. Current runtime facts live in `src/` and `tests/`; current coordinates live in [PROJECT](PROJECT.md).

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

## 3. Current baseline

Road v0.3 product acceptance and archival are complete. Its detailed product, visual, interaction, architecture, decision, and acceptance records are read-only history in the [Road v0.3 archive](archive/road-v0-3/README.md).

The existing Python/Flet implementation remains the runtime baseline until a separately approved Road replaces it. Archival alone does not authorize implementation changes, dependency changes, data migration, or removal of the accepted runtime.

## 4. Transition gate

Before implementation of the next Road:

1. approve one active product specification and Planbook;
2. approve the frontend/core call boundary and packaging model;
3. publish active visual, interaction, and architecture maps;
4. define compatibility, privacy, failure, build, and real-author acceptance evidence; and
5. update [RULES](RULES.md) where the accepted architecture changes existing constraints.

Until then, [PROJECT](PROJECT.md) and runtime inspection answer what exists; this file only preserves product purpose and author-control boundaries.
