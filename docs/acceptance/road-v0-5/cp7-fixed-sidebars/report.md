# Road v0.5 CP7 fixed-sidebars acceptance

**Date:** 2026-07-30  
**Branch:** `ui/cp7-fixed-sidebars-no-bounce`  
**Gate:** Passed by developer; committed as `d900953`

## Scope

- Disable top/bottom overscroll bounce for every scroll container.
- Hide native scrollbar chrome without disabling mouse, trackpad, or keyboard scrolling.
- Keep the Paper, Flashcard, and Library context rails fixed beside the global rail.
- Give a long Flashcard list its own bounded vertical scroll.
- Preserve Library's existing window-scroll save/restore behavior and the existing narrow responsive flow.

## Implementation

- The shared stylesheet applies `overscroll-behavior: none` and `scrollbar-width: none` to every element, hides WebKit scrollbar chrome with `*::-webkit-scrollbar`, and owns one `.fixed-context-rail` rule at the existing `72px` global-rail offset and `260px` context width.
- Paper and Library reuse that fixed rail without changing their main document scroll container.
- Flashcard keeps its heading and Paper selector fixed while only `.flashcard-list` scrolls.
- Existing responsive breakpoints return the context rail to normal document flow below the supported desktop layout.

## Current-source Tauri smoke

`npm --prefix frontend run tauri:dev` ran with an isolated fake `HOME`, fake `TMPDIR`, and a synthetic Paper v3 Vault under `/private/tmp`. The Paper contained one Summary and 36 synthetic Highlights; no real Vault, workstation config, or author content was opened or changed.

| Probe | Result |
| --- | --- |
| `1220×780` Paper | The global and Paper context rails stayed in the same viewport position while a native wheel event moved the synthetic draft from its header to the lower editor actions and read-only original-draft section. |
| `1220×780` Flashcard | The context list moved from Summary/Highlight 1 to Highlights 27–36 without moving its heading, Paper selector, global rail, or main card. Card `37 / 37` opened and showed synthetic Highlight 36 content. |
| `920×680` Flashcard | Card `37 / 37` remained selectable after resizing; the last list item was independently scrolled back into view. |
| `920×680` Library | Main scroll position moved from `0` to `1`; the Library context rail stayed fixed and no horizontal overflow appeared. |
| Scroll boundaries | Out-of-range root scroll-position probes clamped `2 → 1` and `-1 → 0`; the shared CSS blocks overscroll and scroll chaining on the root and nested containers. |
| Shutdown | Tauri, Vite, and the Python sidecar exited after `Ctrl-C`; no test process remained. |

The final hidden-scrollbar pass reused the current Vite server and started a separate Tauri host with the same isolated synthetic `HOME`. A native wheel event moved the Paper document while both rails remained fixed; scrollbar chrome stayed absent at `1220×780` and `920×680`. The isolated host and sidecar then exited; the developer's pre-existing dev process was left running and untouched.

Evidence:

- [Paper top at 1220×780](screenshots/paper-1220-top.png)
- [Paper scrolled at 1220×780](screenshots/paper-1220-bottom.png)
- [Paper scrolled at 920×680](screenshots/paper-920-scrolled.png)
- [Flashcard 37 at 1220×780](screenshots/flashcard-1220-card37.png)
- [Library bottom at 920×680](screenshots/library-920-bottom.png)

## Checks

| Check | Result |
| --- | --- |
| Focused Paper / Flashcard / Library Vitest | 39 passed |
| Full Vitest | 64 passed |
| Python pytest | 235 passed |
| Rust tests | 10 passed |
| Vite production build | Passed |
| Python compileall | Passed |
| Sidecar build | Passed |
| Documentation check | Passed: 42 active files, 15 required files, local links valid |
| `git diff --check` | Passed |

## Boundary

CP7 changes only layout and scroll behavior. It adds no dependency, persistence, schema, Core, Vault, Markdown, Library-query, or product capability change. Physical trackpad feel remains available for the developer's independent follow-up; the current-source WebView, native wheel probe, accessibility bounds, and CSS contract form this checkpoint's automated and platform evidence.
