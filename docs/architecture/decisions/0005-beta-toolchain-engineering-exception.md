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
tests, and provisional local builds. Node, npm, Rust, Cargo, Python, frontend,
Rust, and PyInstaller versions remain exactly locked. Rust/Cargo `1.88.0` is
the approved CP4 lock: it is the minimum version accepted by the resolved
dependency graph and replaces the observed but insufficient `1.83.0`
workstation toolchain.

This exception does not prove release compatibility, does not waive CP13, and
does not authorize signing, notarization, App Sandbox, distribution, or push.
The current macOS 15.0+ claim still requires building and launching on an
arm64 macOS 15.0 environment and retesting the same artifact on the current
machine.

## Consequences

- CP4–CP12 may proceed on the current beta workstation.
- Beta-only failures are engineering observations, not release evidence.
- During CP4, Rust 1.88 release proc-macros failed to load when Tauri injected
  the then-tracked macOS 13.3 target. CP4 therefore used a one-run 11.0
  override only to prove provisional bundle assembly. CP12 raises the tracked
  minimum to 15.0; the CP4 provisional bundle remains neither production nor
  compatibility evidence.
- A production candidate cannot depend on an unrecorded or floating toolchain.
- The exception expires when CP13 begins or a stable workstation replaces the
  current environment, whichever happens first.
