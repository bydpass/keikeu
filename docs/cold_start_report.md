# Phase 8.5 Cold-Start Audit

- Date: 2026-07-18
- Branch: `codex/phase-8-5-doc-reform`
- Result: structural navigation pass; independent fresh-agent run not performed

## Evidence boundary

This report does not pretend the implementing agent is new to the repository. It records deterministic navigation and browser checks using only active entry points. A formal independent-agent pass remains optional follow-up requiring explicit subagent authorization.

Archive files, supplementary human manuals, and conversation memory were excluded from the authority route below.

## Task 1: explain the project

Starting point: [`README.md`](../README.md).

Result:

- one-line product definition appears before implementation detail;
- current status separates Road v0.2 engineering, Phase 8 product acceptance, and iOS 7.5 engineering;
- the core flow and non-goals are visible without opening archive history; and
- one click reaches [`SPEC.md`](SPEC.md) for the complete contract.

Verdict: structural pass.

## Task 2: locate the Paper save chain

Route:

```text
README
  → PROJECT runtime map
  → architecture.html / Paper 保存
  → src/keikeu_app/pages/paper_page.py
  → src/keikeu_core/models.py
  → src/keikeu_core/markdown_io.py
  → src/keikeu_core/indexer.py
```

The architecture page links each source directly. No global repository search or archive file is required.

Observed responsibilities:

- UI builds the in-memory Paper and checks source bytes;
- `Paper.normalize()` enforces durable invariants;
- `markdown_io.py` renders and safely writes the asset; and
- `indexer.py` rebuilds disposable metadata from disk truth.

Verdict: structural pass; source reached within two link transitions from the architecture node.

## Task 3: propose a small change plan

Probe: “Improve the external-modification error wording without changing save behavior.”

Minimum location plan from active maps:

1. confirm the interaction requirement in [`interaction.html`](design/interaction.html) § Error and recovery;
2. change only [`paper_page.py`](../src/keikeu_app/pages/paper_page.py) if wording is the sole behavior;
3. update the focused builder assertion in [`test_app_pages.py`](../tests/test_app_pages.py); and
4. run `.venv/bin/python -m pytest tests/test_app_pages.py`.

Scope exclusions are evident from [`RULES.md`](RULES.md): do not change Markdown I/O, overwrite policy, Vault state, dependencies, or Phase 8 product scope.

Verdict: structural pass.

## Task 4: name the verification command

The commands are discoverable in README, PROJECT, and AGENTS at their appropriate level:

```bash
.venv/bin/python -m pytest tests/test_app_pages.py
.venv/bin/python scripts/check_docs.py
```

The first checks the hypothetical UI change; the second checks documentation structure. They are not interchangeable.

Verdict: structural pass.

## Automated navigation evidence

`scripts/check_docs.py` verifies:

- all required active authorities exist;
- line budgets are respected;
- active Markdown and HTML local links resolve;
- active documents have inbound navigation;
- HTML has no duplicate IDs or external runtime assets; and
- every archived Markdown/HTML file carries a read-only marker.

Manual documents are link-checked but remain non-normative and unnecessary for the four cold-start tasks.

The final run reported 24 active files and 16 required files and remained green.

## Browser evidence

The three active HTML maps were exercised at 375, 768, and 1440 CSS pixels. Search, theme, device tabs, Paper stepper, Flashcard controls, architecture filtering, keyboard activation, semantic landmarks, and overflow checks passed. No screenshot baseline or axe run existed, so visual regression and full WCAG conformance remain unproven.

## Remaining formal gate

An independently spawned agent with no conversation history has not executed the four tasks. Do not relabel this report as an independent cold-start pass. If that stronger evidence is required, run the same tasks from README only and append the result without exposing private author content.
