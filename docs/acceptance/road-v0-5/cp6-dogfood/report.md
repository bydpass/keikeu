# Road v0.5 CP6 independent dogfood report

**Target:** `keikeu CP6 Round 2 1e87ad4.app` on macOS
**Date:** 2026-07-29–2026-07-30
**Scope:** Paper → Flashcard → Library, Vault selection/reset, Trash recovery, Core recovery, and migration gates
**Tester:** Codex, acting as an independent first user
**Gate state:** Passed by developer on 2026-07-30

## Executive summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 1 |
| **Total** | **4** |

No P0/P1 or normal-interaction data loss was found. Round 1 exposed three concrete annoyances; all three were fixed and rechecked in Round 2. The later P2 follow-up also fixed Vault switching from an unsaved daily draft and was checked in a current-source Tauri process. The developer accepted CP6 on 2026-07-30.

## Candidate and isolation

| Item | Evidence |
| --- | --- |
| Base HEAD | `1e87ad44875fe1eb62b1b6f506d975344ae2e9dc` |
| Bundle identity | `app.keikeu.cp6dogfood.r2`; title `keikeu · CP6 Round 2 · 1e87ad4` |
| Desktop executable SHA-256 | `284e528f72e4777861b16c2e61557d4261cd5145e766c664fd99780a52d53942` |
| Sidecar SHA-256 | `84a3ba1adde566c2085230408143bf4fea128fc2f85ba074907e61a57fc11f5b` |
| Data source | Repository-local copied and synthetic Vaults under `tests/test-vault/cp6-dogfood-*` |
| Persistent state | Process-local fake `HOME` and `TMPDIR`; no real Vault or workstation keikeu config used |

## Sessions

| Run | Time | Result |
| --- | --- | --- |
| Round 1 | 2026-07-29 23:47:32–2026-07-30 01:06:30 EDT | More than 30 minutes. Found no P0/P1 and identified the three highest-friction items below. |
| Round 2 rehearsal | 2026-07-30 01:10:45–01:40:19 EDT | Paused by developer at 29m34s; preserved as the [pause checkpoint](checkpoint.md), not counted as the completed rerun. |
| Round 2 completed run | 2026-07-30 10:45:13–11:15:13 EDT | Uninterrupted candidate process and active workflow/recovery probing for 30 minutes. Rechecked all three fixes, restored the paused Trash item, and covered Core and migration states. |

The final two minutes of the completed run included diagnosing a macOS Accessibility/window-activation anomaly on the same isolated process. A controlled red-close test later exited host and Core cleanly, and the abnormal state did not reproduce through the normal close path. It is recorded as test-tool noise, not a product issue.

## Issues and outcomes

### 1. Flashcard boundary controls looked actionable but did nothing

| Field | Value |
| --- | --- |
| Severity | Medium |
| Category | UX / interaction feedback |
| Project class | Top-three annoyance; fixed |

**Reproduction:** Open Flashcard on Summary, press `上一张`; or go to the last card and press `下一张`.

**Before:** The boundary button remained visually enabled and accepted a no-op click.

**After:** `上一张` is disabled on page 1 and `下一张` is disabled on the final page; arrow-key navigation still works. See [last-card boundary evidence](screenshots/round2-05-flash-last-boundary-1220x780.png) and [920×680 evidence](screenshots/round2-15-flashcard-boundary-920x680.png).

### 2. Blank Summary produced the browser's English required-field bubble

| Field | Value |
| --- | --- |
| Severity | Medium |
| Category | UX / validation consistency |
| Project class | Top-three annoyance; fixed |

**Reproduction:** Leave Summary blank and save a draft in the Chinese interface.

**Before:** Native HTML validation intercepted submit and showed an English browser bubble instead of keikeu's existing inline error.

**After:** Submit reaches the existing validation path and displays `Summary 不能为空。`; no save request is sent. See [Round 2 validation evidence](screenshots/round2-01-summary-validation-1220x780.png).

### 3. Paper and Library exposed raw ISO timestamps

| Field | Value |
| --- | --- |
| Severity | Low |
| Category | Visual noise / readability |
| Project class | Top-three annoyance; fixed |

**Reproduction:** Inspect Paper identity or Library details for a saved Paper.

**Before:** Values included `T`, seconds, and fractional seconds.

**After:** Both pages show calm minute-level `YYYY-MM-DD HH:MM` values while retaining the Core-owned source value. See [Paper evidence](screenshots/round2-02-paper-saved-1220x780.png) and [Library evidence](screenshots/round2-06-library-saved-1220x780.png).

### 4. Paper gives no reason why Vault switching is unavailable

| Field | Value |
| --- | --- |
| Severity | Medium |
| Category | UX / action discoverability |
| Project class | P2; fixed |

**Reproduction:** Start on the clean in-memory daily draft and inspect `切换 Vault`.

**Before:** The button was disabled without explanation. Opening Library exposed a working `切换 Vault` action, so the workflow was recoverable and content was not at risk.

**After:** A clean in-memory draft can enter the Vault picker directly. A dirty in-memory draft still uses the existing native departure guard: `继续编辑` preserves the draft and `未保存` state, while `放弃更改` enters the Vault picker without writing a Markdown file. See [native confirmation](screenshots/p2-vault-dirty-confirm-1220x780.png) and [preserved draft](screenshots/p2-vault-continue-preserves-draft-1220x780.png).

**Decision:** Remove only the stale `paper.path` disable condition and reuse `requestDeparture()`; no Core, persistence, or Vault semantics changed.

### Additional visual adjustment

The shared divider token changed from `#d9d5ca` to `#b8b2a6`, so the context/workspace split, field rules, cards, tables, Vault/migration panels, and Core states remain quiet but read more clearly. The active design page and final prototype use the same token. See [Paper at 920×680](screenshots/p2-divider-paper-920x680.png) and [Vault at 920×680](screenshots/p2-divider-vault-920x680.png).

## Testing coverage

### Pages and workflows exercised

- Vault picker, native folder choice/cancel, successful Vault switch, and post-switch context reset.
- Paper daily draft, obvious editable regions, read-only original copy, inline validation, save baseline, dirty navigation `继续编辑`/`放弃更改`, and clean close.
- Flashcard Summary-first projection, one Highlight per card, mouse/card-list and arrow-key navigation, page reset on Paper switch, and both boundaries.
- Library search with `⌘F`, sorting, selection, folder scope, folder move, Trash/restore, and Paper/Flashcard return-context retention at `1220×780` and `920×680`.
- Real sidecar termination, explicit Core-blocked page, `重启本地 Core`, and recovery without losing the restored copied Paper. See [blocked](screenshots/round2-10-core-blocked-1220x780.png) and [recovered](screenshots/round2-11-core-recovered-1220x780.png).
- Exact copied v0.1 migration-blocked fixture and a copied migration-ready fixture. Confirmation enabling was exercised, then migration was cancelled; no backup or migration mutation was performed. Screenshots were intentionally omitted because those states display the local test path.

### Automated checks

| Check | Result |
| --- | --- |
| Vitest | 63 passed |
| Python pytest | 235 passed |
| Rust tests | 10 passed |
| Vite production build | Passed |
| Python compileall | Passed |
| Sidecar build | Passed |
| Documentation check | Passed: 41 active files, 15 required files, local links valid |
| `git diff --check` | Passed |

### Not tested / out of scope

- Real author Vaults, real workstation config, cloud/provider behavior, telemetry, or network upload.
- Performing an actual v0.1 migration; only preflight, confirmation gating, and cancel paths were tested on copies.
- External-editor/Finder application behavior beyond the validated UI actions.
- Signing, notarization, DMG, distribution, other macOS versions, iOS, Android, or Windows.
- The advance-YOLO follow-up checkpoint; it is separate from this accepted CP6 record.

## Final gate judgment

- Agent dogfood: complete.
- Unresolved P0/P1: none found.
- Round 1 top-three annoyances: fixed and rechecked.
- Recorded P2 Vault-switch issue: fixed and rechecked.
- Developer acceptance: passed on 2026-07-30.
- Road v0.5 closeout: deferred until the authorized follow-up checkpoint completes.
- Git state at handoff: checkpoint commit authorized; no push, tag, or archive.
