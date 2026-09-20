# keikeu Product Boundary (Road v0.7 accepted; v0.8 replanning from 5ff26fe)

> 2026-09-20 当前决定：v08 已中断并转交，未获最终接受；v09 整顿工作目录与执行体系，v09.01 直接替换为 iOS SwiftUI。移动端采用原生组件并尽可能复用 Rust 内核；Mac 日后重构，Windows 保留现有技术结构。本轮 v09 CP0–CP4 已获全计划 YOLO，先重排目录并独立纯规则核心。当前方向与转交清单见 [Road v09 规划](road-v09.md)；下文 v08 目标和候选门槛保留作历史对照，不再驱动旧 iOS 路线开工或收尾。外部 Alpha 移出 v09，后续版本编号待定。

> Authority: §§1–7 define the accepted product, author-asset, and data-safety boundary inherited from Road v0.6; §8 defines shared exclusions and platform scope; §9 records the Road v0.7 App Shell composition accepted at CP6; §10 defines the CP7 continuous-flow override accepted by developer Gate D on 2026-08-25; §11 defines the CP8 responsive-navigation override accepted by developer Gate D on 2026-08-26 and records the developer's Road v0.7 completion judgment; §13 records the documented but unimplemented cross-platform target and does not authorize CP0. Detailed Paper v4 grammar, DTOs, migration, recovery, and protocol remain in the approved [Paper v4 design](design/road-v0-6-paper-v4-design.md); the current interface and acceptance matrix live in the [App Shell design](design/road-v0-7-app-shell-design.md). Current checkpoint and runtime facts live in [PROJECT](PROJECT.md), source, and tests.

## 1. Definition

keikeu is a private, local-first pre-writing and writing-focus tool for a single fanfiction author.

```text
existing inspiration → editable card-page Paper → saved Paper → external prose editor
```

The author leaves keikeu with the Paper itself. There is no separate Flashcard product step.

## 2. Author control

- Markdown remains the durable, readable, repairable author asset.
- Rebuildable indexes and device state are auxiliary, never canonical creative content.
- keikeu must not silently rewrite, normalize, delete, overwrite, upload, merge, score, or train on author text.
- 完整文件夹树只有在界面明确说明“全部内容”并获得确认后才能移入废纸篓；不可恢复的整树销毁还需要废纸篓中的第二次明确确认。
- The author chooses the Vault and external prose editor.
- The current accepted runtime has no account, cloud backend, telemetry, hidden remote service, or keikeu-managed background sync. The future opt-in iCloud Documents target is bounded by §13 and is not a current capability.
- Damaged Paper Markdown is reported, not silently repaired or partially opened as an editable Paper.

## 3. Current runtime and accepted composition

CP4 has activated the Road v0.6 product/data contract without changing the process architecture:

```text
Vue → Tauri/Rust → JSONL protocol v2 → Python service/core
    → Paper v4 Markdown / Index / Vault → Paper pages
```

Road v0.7 keeps that runtime and every durable data contract unchanged. Its CP6-accepted change is
limited to the Vue composition layer:

```text
previous accepted: page-level Paper / Library / Vault surfaces
current accepted:  compact App Shell → Paper / Library → Vault context / blocking recovery
```

The production composition passed CP5 engineering integration and CP6 first-author acceptance.
Paper v4, Index v4, protocol v2, Python, Rust, and every author-control contract remain unchanged.
The accepted runtime now includes the CP7 presentation and narrow folder-lifecycle override plus the
CP8 responsive-navigation presentation override. CP7
completed Gate C engineering verification, two Gate D remediation rounds, isolated Tauri smoke and
same-page Figma synchronization before the developer explicitly passed Gate D on 2026-08-25. The
folder-lifecycle exception is defined in §10 and
[ADR-0008](architecture/decisions/0008-whole-folder-trash-lifecycle.md). Automated composition
evidence did not prove that the native macOS candidate window appeared; CP8 separately passed that
physical-input Gate on 2026-08-26. `PROJECT.md`, source, and tests remain the authority for current
implementation and checkpoint state.

## 4. Current Paper v4 behavior (unchanged by Road v0.7)

- A Paper has a stable optional display name, ordered Tags, and at least one ordered card page.
- Every page has an always-editable optional title, author Markdown content, and optional type: `summary`, `snapshot`, `whisper`, or `null`.
- Display labels are fixed: 总结、高光、碎碎念; `null` displays no label.
- A Paper has at most one Summary page. Snapshot and Whisper pages are unlimited.
- Basic mode and further mode are presentation only. Switching modes never clears a page title, content, or hidden type.
- A saved page must have a non-empty title or content containing at least one non-whitespace character. The whitespace check never rewrites content.
- Paper and page names trim outer whitespace only, become `null` when empty, allow at most 200 Unicode code points, and reject control, surrogate, and line-separator characters.
- Tags are single-line values; comma is ordinary content. Normal v4 editing trims, drops empty values, and keeps the first trimmed duplicate without normalizing author text.

The exact Markdown v4 shape, frontmatter scalar codec, page markers, reversible marker escaping, Tags grammar, and strict failure rules are defined only in [the approved design §8](design/road-v0-6-paper-v4-design.md#8-markdown-schema-v4).

## 5. Accepted interaction baseline (unchanged by Road v0.7)

- The default Paper editor is one large card page, not a Summary form followed by a render step.
- The Paper display name and current page title remain editable in both basic and further modes.
- The card bottom exposes exactly three primary actions: 保存, 删除, 加一页.
- 加一页 splits the current page content at the actual caret or selection, preserves the prefix on the current page, moves the suffix to a new untitled/untyped page, and focuses the new page title. If the body was never focused, the split point is the end.
- 删除 removes the current page after confirmation. Deleting the only page replaces it with one blank page; a Paper never has zero pages.
- Page-number buttons switch pages. Road v0.6 does not add page reordering or page deep-links.
- Save is one whole-Paper compare-and-swap operation. A successful Markdown replacement advances the baseline even when disposable Index update fails.
- Dirty departure protection covers Paper/Vault switching, navigation, and normal close. Known failure preserves the draft; stale or unknown results never trigger an automatic retry.
- Library projects the whole Paper, searches all pages locally, previews the first page, and always opens the whole Paper at page 1.

## 6. Recovery and migration

- `repair_required` is a tagged successful domain result with separate ordinary-open and unknown-save ownership; it never exposes damaged prose in diagnostics.
- `commit_unknown` freezes the affected durable intent. `paper.save` recovers only through read-only `paper.reconcile_save`; all other mutations use their declared read-only refresh/inspect path and are never automatically replayed.
- `index_degraded` means the author-file mutation is known successful while the disposable Index is not current. It must not roll back or re-send the author mutation.
- v2/v3 → v4 migration may discard only `initial_summary`, and only under the approved migration contract with a complete external backup.
- Legacy Tags containing multiline/control characters, empty items, outer whitespace, or trim-collisions block preflight rather than being silently normalized.
- Raw loss-audit, full preflight, Home-contained backup outside the active Vault, regular-file manifest and byte verification, isolated staging, per-file safe replacement, and mixed-schema resume are required.
- Migration, delete, recovery, and failure experiments use fixtures, synthetic Vaults, or complete copies before any separately authorized real-Vault operation.

## 7. Architecture boundaries

- Vue owns visible state, draft/baseline, active page, and App-root pending intent; it never reads or writes author files.
- In the current desktop runtime, Rust owns lifecycle, one Python sidecar, the JSONL queue, native directory selection/confirmation, and validated system actions; it never parses Markdown or implements product rules.
- The transport-agnostic Python service owns orchestration and strict DTOs. `keikeu_core` owns domain validation and file rules without GUI or transport imports.
- In the current desktop runtime, `markdown_io.py` exclusively owns Paper Markdown. In that same runtime, `vault.py` owns Home containment, supported Paper paths, active/Trash enumeration, code allocation, and destructive moves on those paths; migration modules separately own gated backup/staging/replacement. The v0.8 Rust path may receive bounded mobile/shared-iCloud ownership after its contract and golden Gates pass; desktop ownership changes only in the separate post-candidate convergence under §13. Index data is local and rebuildable.
- The current accepted runtime has no localhost, HTTP, WebSocket, account, telemetry, upload, hidden service, or automatic mutation replay.

## 8. Explicit exclusions and platforms

No AI generation, prose editor, sync, account, community, database, file watcher, Router, Pinia, TypeScript, UI kit, auto-save, page reorder, signing, notarization, staple, DMG, public distribution, mobile implementation, or cross-platform build enters Road v0.7.

- macOS Apple Silicon is the only Road v0.7 engineering and first-author platform. Intel Mac is unsupported. The historical Phase 7.5 iOS quick-test branch is not part of the accepted runtime or evidence for the new mobile target.
- The documented sequence is Road v0.8 iPhone core creation plus Mac iCloud synchronization; independent desktop parity and Python product-runtime retirement; Road v0.9 iOS/macOS first external Alpha plus the promotion Gate; Road v0.10 Android plus second Alpha; then a Windows decision from both rounds. Linux and watchOS have no scheduled work.
- Road v0.8 is being replanned after the 2026-09-07 rollback to `5ff26fe`; the new iteration has not started. Prior attempt evidence does not establish this iteration's acceptance. The independently implemented [App-root close-guard candidate](acceptance/close-guard-2026-09-04.md) has focused and native-window evidence; on 2026-09-05 the developer manually confirmed protection for all normal exit paths except force quit and passed this independent prerequisite. This is not a v0.8 checkpoint or CP0 seed approval.
- Signing, notarization, TestFlight, DMG delivery, recruitment, promotion, Android implementation, and Windows implementation remain unperformed.
- The repository `./dev` TUI, human manuals, and ignored root `CONTEXT.md` are developer workflow tools.
  They are not product surfaces, runtime protocol components, author assets, or acceptance evidence.

## 9. Accepted Road v0.7 App Shell baseline (CP6 passed; CP7 override in §10)

Road v0.7 changes only Vue work-surface structure, information hierarchy, and responsive
presentation. It does not change §§1–8, Paper v4, Index v4, Vault persistence, protocol v2,
Python, Rust, or author-control contracts.

- Paper and Library are the only peer daily locations.
- Vault is a local-environment entry. Its normal state stays quiet; selection, migration,
  `repair_required`, `commit_unknown`, and sidecar failure retain complete environment or
  blocking surfaces.
- A compact App Shell expresses product identity, current location, New Paper, and current
  Vault without adding a permanent side rail, Router, or store.
- Paper prioritizes author content. The CP6 baseline used scope–list–detail/actions at `1220×780`
  and placed detail below the list at `920×680`; the accepted CP7/CP8 presentation in §§10–11
  instead keeps scope/sidebar plus the main result/action stream and moves Paper preview into a
  top-layer Popover.
- Leaving a dirty Paper for Library, New Paper, or Vault reuses the one departure guard owned by
  PaperView; App coordinates the navigation intent without duplicating confirmation rules.
- Both target window sizes keep content, save, dangerous actions, and recovery paths visible or
  reachable by clear vertical scrolling, with no horizontal overflow.
- Navigation and actions have semantic names, visible focus, keyboard paths, non-color-only state,
  and reduced-motion behavior.

The accepted criteria and evidence boundary are frozen in the
[Road v0.7 acceptance matrix](design/road-v0-7-app-shell-design.md#141-road-v07-验收矩阵).
CP2–CP4 provide current source, tests, and window evidence for this production UI structure. CP5
provides the complete cross-stack baseline plus current-source synthetic Tauri evidence for the
normal, native dirty-confirmation, Index, repair, `commit_unknown`, restart and no-replay paths. The
separate [CP6 author Gate](acceptance/road-v0-7/cp6-author/report.md) passed by explicit developer
judgment under one bounded real-v4-Vault authorization, which is now consumed. CP7 subsequently
passed its own four Gates and now supplies the accepted presentation and folder-lifecycle override in
§10. Neither that consumed authorization nor later acceptance authorizes any further real-Vault
action, scope outside §10, Road closeout, or remote Git operations.

## 10. Accepted Road v0.7 CP7 continuous-flow override

CP7 removes visual and interaction friction from the accepted App Shell without changing Paper v4,
Index v4, protocol v2, DTOs, author Markdown, or product capabilities. Its original scope was the Vue
presentation layer and Tauri window geometry. Gate D follow-up remediation adds one explicitly
approved Core exception: the complete-folder Trash lifecycle below. No new command, dependency,
schema, index, service, or remote behavior is added.

- The Paper surface becomes one continuous vertical flow: context → page navigation → current page → actions.
- The default desktop window is `720×900` (`width / height = 0.8`), with `720×680` minimum desktop geometry, and remains resizable into the accepted landscape state. `375×812` is browser-responsive evidence, not a mobile implementation or Tauri minimum.
- Tags use one single-line comma-separated field. The Vue adapter uses reversible CSV-style quotes so literal commas and quotes survive; DTOs and Markdown continue to carry the existing ordered Tag array and Paper v4 bullet grammar. Library search suppresses service queries during IME composition and sends the committed Chinese text exactly once.
- Paper details and Library Paper preview open in compact native popovers outside document flow. A selected Library row never inserts a detail block below the result list or displaces Paper/folder operations.
- The Paper surface has no persistent dirty label; existing departure, new-Paper, Vault and close guards remain authoritative.
- Paper name and page title use the approved Opus serif role; controls and body text stay on the system sans stack. Text-field focus remains quiet while keyboard focus for buttons and navigation stays clearly visible. The Figma meta color `#627078` is corrected to `#5c6a71` in production for WCAG contrast.
- Confirmed active-folder deletion atomically moves the exact complete directory tree, including unknown and nested entries, to `.trash/cache/`; restore moves the same tree back without partial merge. A conflicting exact/NFC+casefold target blocks the whole move. Confirmed permanent folder deletion uses identity-pinned, symlink-safe recursion and refuses unsafe platforms or mounted subtrees. Once irreversible recursion begins, a later filesystem failure cannot restore entries already destroyed; the remaining tree is restored to its visible Trash name and the operation reports failure. Single-Paper operations and folder merge/rename keep their existing strict validation. The full contract is [ADR-0008](architecture/decisions/0008-whole-folder-trash-lifecycle.md).
- Paper v4, Index v4, protocol v2, DTOs, Rust commands, sidecar, recovery states, and the Library range/list/action capabilities remain unchanged. Python changes are confined to the three existing folder lifecycle methods; Library presentation changes are confined to IME-safe search and top-layer preview.

CP7 followed four Gates: contract, Figma delivery, production verification, and explicit developer UI
acceptance. Gates A–C and both remediation rounds completed on 2026-08-25; the developer then
explicitly passed Gate D with no unresolved P0/P1. The CP7 acceptance record separates this product
judgment from automated engineering evidence and from the native macOS candidate-window check moved
to CP8. CP7 is committed locally at `1e17cea`; its acceptance did not itself authorize closeout.
CP8 and the downstream snapshot later closed the Road, while push, tag, signing, packaging and release
remain unperformed.

## 11. Accepted Road v0.7 CP8 responsive-navigation override

CP8 is an accepted, presentation-only continuation of CP7. Gate A–C engineering/Figma evidence and
the physical-keyboard macOS native-candidate-window Gate completed on 2026-08-26; the developer then
explicitly passed Gate D with no reported anomaly. That acceptance did not itself imply a checkpoint
commit, Road closeout, remote Git action, or release.

Gate A–C engineering and Figma evidence completed on 2026-08-26. The source candidate, focused/full
tests, five-viewport synthetic browser QA, debug app bundle, and in-place Figma Page `71:2` overwrite
are recorded in the [CP8 engineering report](acceptance/road-v0-7/cp8-responsive-navigation/report.md).
The same report separately records the developer's Gate D observation and subsequent Git boundary.

- The one-row `56px` Shell presents `编辑 Paper → 新 Paper → Library … Vault`; it changes only label
  and placement and keeps the single existing dirty-departure guard.
- Every Paper page button stays in the DOM in a one-row, locally scrollable, scroll-snapping track with
  about three visible slots. The track has a thin visible horizontal scrollbar, no arrows, wrapping, or
  cycling; load, direct selection, add, and delete center the active tab while retaining `aria-current`,
  focus, direct selection, and saving locks. The document itself must not scroll horizontally.
- Portrait means `height >= width` through native `@media (orientation: portrait)`. The Markdown field
  uses `clamp(220px, 34dvh, 300px)`, disables vertical resize, and scrolls long content internally;
  landscape keeps vertical resize.
- Portrait Paper actions are an opaque, safe-area-aware bottom sticky Anchor that does not cover the
  final line, errors, or focus. Portrait Library exposes equal-height sticky Anchors for `范围 / 排序`
  and `新文件夹`; their native popovers support keyboard activation, Escape, light-dismiss, focus
  return, failure-preserved input, and success-close behavior. Landscape Library keeps its existing
  sidebar, sort row, and inline folder creation.
- Engineering layout evidence must cover `375×812`, `720×900`, `720×680`, `920×680`, and
  `1220×780`, including `1/3/4/6/7/12` pages, 80 body lines, maximum legal names, local track/body
  scrolling, Anchor clearance, and `document.scrollWidth <= clientWidth`.
- The existing Figma Page `71:2` is versioned as
  `CP7 Gate D accepted · before CP8 overwrite`, overwritten in place, and renamed
  `CP8 · 响应式锚点与横向滚轮`; a second active master is not created.
- The native IME Gate uses an absolute-path CP8 debug app, fake Home, synthetic data containing Tag
  “暴食”, macOS Simplified Pinyin, and a physical keyboard. A missing or disrupted candidate window,
  any intermediate-pinyin query, or duplicate final submission is P1 and blocks CP8 acceptance.
- Core, bridge, DTOs, Paper v4, Index v4, protocol v2, Rust commands, Tauri geometry, dependencies,
  durable author assets, and product capabilities remain unchanged.

CP8 implementation, Figma synchronization, automated evidence, native IME observation, and developer
acceptance are complete Gate A–D conclusions. Final checkpoint `2f03aee` and the independent
[Road v0.7 snapshot](archive/snapshots/road-v0-7.html) complete the Road's documentation closeout.
No real Vault or author content was used for CP8 verification. Push, tag, signing, packaging, and
release remain separate and unperformed.

## 12. Road v0.6 completed acceptance record

1. **Checkpoint engineering:** CP0–CP6 each produce their declared implementation, checks, smoke, and evidence with no unresolved P0/P1. Their developer exit judgments are covered by advance YOLO; evidence may not be invented or copied forward.
2. **Current/target integrity:** CP0–CP3 kept production v0.5/protocol v1; CP4 alone activated the complete v4/v2 vertical path; CP5 removed only code proven unreachable.
3. **Safety integration:** CP6 exercises unknown-result ownership, strict repair states, Index verification, migration and path-mutation recovery, and the Chinese repair manual using synthetic data or complete copies.
4. **Product acceptance:** CP7 separately requires the first author's real workflow. It is not part of CP6 engineering completion and needs separate real-Vault authorization.
5. **Road closeout:** CP7 acceptance, snapshot, tag, push, signing, packaging, and release are separate decisions.

## 13. Documented unified-core target (not implemented or software-CP0-authorized)

The 2026-09-04 plan refactor retains Vue/Tauri and chooses progressive Rust Core unification.
[ADR-0009](architecture/decisions/0009-unified-rust-core-transition.md) records the decision and its
conditional replacement of ADR-0004. The 2026-09-07 rollback to `5ff26fe` restarts planning; the revised
[plan and change map](../PLAN_road_v0_8.md#0-先看我们正在改什么) distinguish engineering checkpoints from device acceptance.
Documentation approval proves no mobile build, Apple capability,
software checkpoint, migration, or Alpha result; current runtime ownership above remains in force.

| Stage / environment | Target backend and boundary |
| --- | --- |
| v0.8 macOS local Vault | Existing JSONL Python sidecar and full desktop capabilities, unchanged |
| v0.8 macOS shared iCloud Vault | In-process Rust Paper Core plus Apple-native file coordination |
| v0.8 iPhone local / shared iCloud Vault | The same Rust Paper Core; cloud mode adds native coordination |
| Independent post-candidate convergence | Rust takes over remaining desktop capabilities after parity and switch validation; Python product runtime retires |
| First external Alpha and later Android | Unified Rust product Core; Python may remain a development comparison tool only |

- The v0.8 iPhone candidate includes multi-page Paper creation/editing, save/reopen, list/search,
  single-Paper Markdown export, local draft recovery, and mandatory Mac iCloud round trips. Mobile
  and cloud capabilities are narrow; desktop-local Trash, migration, folders and external-editor
  handoff remain available. Full mobile management, whole-Vault export and formal iPad acceptance
  are excluded. Mobile/cloud search may scan supported Papers linearly without Index v4.
- Keep the existing `bridgeRequest` boundary and Paper v4 file contract. Freeze host capabilities,
  shared business DTOs and host-only methods separately from unchanged Python JSONL protocol v2;
  never fabricate a current Index state for a backend without an Index.
- Each client uses one controlled backend for its selected Vault: no dual writes or automatic
  fallback to another writer after an error. Cross-device concurrency still requires coordination.
- Chinese and English follow the system initially, remain manually switchable, and store the choice
  only in local device state; author text, names and Tags are not translated or normalized.
- Local is the default. Explicit iCloud opt-in creates or reconnects one shared cloud Vault without
  moving an existing local Vault. Resolve dirty drafts and pending writes before switching; validate
  the new target before changing selection. Failed switches keep the old selection, and old results
  cannot be applied to a new storage identity. Discovery/download/read/write use Apple-native APIs.
- Recovery drafts are private, non-canonical and unsynced, keyed by storage, Paper/draft identity
  and revision. Clear only the matching successfully saved revision or an explicitly discarded draft;
  retain newer edits and all failed/unknown saves. Surface recovery-write failure. Relaunch offers
  recovery, export or discard without overwriting Paper; only the last persisted draft is guaranteed.
- Distinguish pre-replacement failure, committed-but-response-lost and external changes; retain the
  draft and reconcile read-only, never replay an unknown write. Preserve and verify every conflict's
  raw bytes before marking it handled, and preserve the displaced current version before promotion.
  Interrupted recovery must not overwrite copies; no automatic merge, deletion or clock-based winner.
  Same-code creation covers both native version conflicts and provider-renamed sibling files: discover,
  preserve, export and offer explicit recovery without silently renaming files or rewriting codes.
- Independent post-candidate convergence must preserve all desktop Index, folder, Trash, migration,
  recovery, device-state and system-action behavior on fixtures/copies. Only parity, safe switching
  and developer acceptance permit removing sidecar, product JSONL calls and Python packaging.
  The first external Alpha is blocked until that convergence passes; v0.8 acceptance alone is insufficient.
- Road v0.9 owns final external TestFlight iOS and Developer ID/notarized/stapled macOS validation;
  if the DMG shared-container gate fails, macOS Alpha uses TestFlight with its own actual-build checks.
  Debug sync does not prove distribution. The 18+ Chinese/English first Alpha uses self-attestation
  without birth dates or identity documents; promotion remains a separate gate.
- Road v0.10 adds Android and the second Alpha after promotion begins: local Markdown and explicit
  import/export, no new cloud service. Windows timing depends on both Alpha rounds.
