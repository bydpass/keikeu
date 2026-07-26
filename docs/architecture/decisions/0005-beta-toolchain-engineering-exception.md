# ADR-0005: Beta macOS/Xcode engineering exception

**Date**: 2026-07-25

**Status**: accepted
**Decider**: developer

## Context

The available arm64 workstation runs macOS 27.0 beta and Xcode 27.0 beta.
Road v0.4 originally prohibited beta platform tools entirely, which blocked
Tauri engineering even though release compatibility has its own later gate.

## Decision

The developer explicitly approved this workstation for CP4–CP12 engineering,
tests, and provisional local builds. On 2026-07-26, after CP13 compatibility
was accepted, the developer granted a separate one-time extension for CP14's
final engineering build and launch smoke after Flet retirement. Node, npm,
Rust, Cargo, Python, frontend, Rust, and PyInstaller versions remain exactly
locked. Rust/Cargo `1.88.0` is the approved CP4 lock: it is the minimum version
accepted by the resolved dependency graph and replaces the observed but
insufficient `1.83.0` workstation toolchain.

Neither the original exception nor the CP14 extension proves release
compatibility or authorizes signing, notarization, App Sandbox, distribution,
or push. The macOS 15.7+ claim remains supported only by the accepted CP13
GitHub arm64 `macos-15` runner build/launch and same-artifact workstation
retest; CP14 beta evidence cannot replace or broaden it.

## Consequences

- CP4–CP12 may proceed on the current beta workstation.
- CP14 may use the current beta workstation only for the final post-Flet
  engineering build and isolated launch/relaunch smoke.
- Beta-only failures are engineering observations, not release evidence.
- During CP4, Rust 1.88 release proc-macros failed to load when Tauri injected
  the then-tracked macOS 13.3 target. CP4 therefore used a one-run 11.0
  override only to prove provisional bundle assembly. CP12 raises the tracked
  minimum to 15.0; the CP4 provisional bundle remains neither production nor
  compatibility evidence.
- A production candidate cannot depend on an unrecorded or floating toolchain.
- The original exception expired when CP13 began. The one-time CP14 extension
  expires when the final CP14 build/smoke evidence is recorded or a stable
  workstation replaces the current environment, whichever happens first.
- The CP14 extension was consumed and expired on 2026-07-26 after the
  post-Flet build and isolated launch/relaunch smoke passed.
