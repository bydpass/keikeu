# Road v0.6 Invited Alpha Design

> Status: design approved by the developer on 2026-07-31.
>
> This document defines the Road v0.6 target. It does not claim that CP0,
> signing, notarization, installation, product acceptance, a commit, or a push
> has passed.

## 1. Core judgment

Road v0.6 is a **macOS Apple Silicon invited Alpha plus a second-user MVP
Gate**. It is not a public launch and it is not a cross-platform
implementation Road.

Road v0.2 and v0.3 contain real-author evidence from the developer. Road v0.5
adds Agent dogfood and a developer gate, but it does not provide evidence from
a second human user. Road v0.6 must answer three different questions:

1. Can keikeu produce a trustworthy Developer ID-signed, notarized, stapled
   arm64 DMG?
2. Can the developer understand and independently repeat that release process
   from a usable manual?
3. Can a second user install the same artifact and complete the core workflow
   without an unresolved P0/P1?

All three must pass. Automated tests, release engineering, operator learning,
and product validation remain separate conclusions.

## 2. Chosen approach

Use one local, manual release path:

- `Developer ID Application` identity in the local macOS Keychain;
- existing sidecar and Tauri build chain;
- Tauri/Apple-native signing and default DMG tooling;
- Apple `notarytool` with one Keychain credential profile;
- Apple `stapler`, Gatekeeper, code-signing, disk-image, and architecture
  verification;
- one linear human runbook;
- one independent developer rehearsal before tester delivery.

This is preferred over:

- an unsigned or ad-hoc build, because it cannot establish the invited
  tester's Gatekeeper path;
- CI signing and release automation, because one invited user does not justify
  remote secrets or a release service;
- App Store distribution, because review, store metadata, sandboxing, and
  public support are outside this Road.

No release orchestrator, Makefile, CI job, updater, or custom DMG artwork is
added. Reconsider automation only after the manual process has been repeated
successfully and remains a measured source of errors.

## 3. Product and architecture invariants

The runtime remains:

```text
Vue/Vite
  → Tauri/Rust
  → JSONL Python sidecar
  → Python application service
  → Python Core
  → Markdown / rebuildable JSON / local Vault
```

Road v0.6 does not change this architecture, Paper schema, Vault layout,
author-control rules, or the core product flow:

```text
existing inspiration → Paper Markdown → Flashcard → external prose editor
```

Markdown remains canonical. No account, telemetry, upload, remote service,
cloud sync, hidden background service, or AI ghostwriting enters the Road.
All build and local smoke work uses synthetic or copied Vaults, never the only
real Vault.

## 4. Road outcome and scope

### Required outcomes

- Produce one arm64 DMG for macOS 15.7 or later.
- Sign distributable code with `Developer ID Application`.
- Receive an Apple notarization result of `Accepted` and inspect its log.
- Staple and validate the distributed DMG.
- Verify Gatekeeper, signatures, disk-image integrity, architecture, install,
  first launch, core flow, quit, and relaunch.
- Record the final DMG SHA-256 after stapling.
- Provide a usable local release manual.
- Complete an independent developer release rehearsal from that manual.
- Complete the second-user MVP Gate with no unresolved P0/P1.
- Fix only observed P0/P1 issues, then rebuild and repeat the affected release
  gates.

### Explicit exclusions

- App Store, public download, PKG, ZIP distribution, updater, or release feed.
- App Sandbox or Mac App Store capability work.
- CI signing, remote credentials, remote release jobs, or automated push.
- Intel or universal macOS builds and Rosetta compatibility QA.
- iOS, iPadOS, Android, HarmonyOS, Windows, Linux, or watchOS implementation.
- New product capabilities, complex onboarding, in-app feedback, analytics,
  or P2/P3 opportunistic polish.
- Custom DMG presentation or byte-for-byte reproducible-build claims.

The developer performs any remote push manually. Tagging and public release
remain separate decisions after Road acceptance.

## 5. Locked platform matrix

| Platform | Status | Entry or acceptance Gate |
| --- | --- | --- |
| macOS Apple Silicon, macOS 15.7+ | Primary development platform and Road v0.6 sole delivery commitment | Developer ID signing, notarization, staple, arm64 DMG, install, launch/relaunch, exact-artifact macOS 15.7 compatibility, and second-user flow without unresolved P0/P1 |
| Intel Mac | Explicitly unsupported | No x86_64 or universal build, Rosetta QA, or Intel compatibility claim |
| iOS and iPadOS | August 2026 engineering target, not an unconditional release date | Design and prove a mobile-specific runtime while leaving the desktop sidecar unchanged; then prove sandbox-local create/save/quit/reopen on iPhone and iPad |
| Android | Conditional Q4 2026 engineering target | Reuse the accepted mobile-runtime decision; prove app-private storage and the core flow on a real device |
| HarmonyOS | Q4 2026 exploration target, not a release commitment | First choose HarmonyOS NEXT-native or Android-compatible targeting, then run an independent feasibility Gate; Android support does not imply HarmonyOS support |
| Windows | Directional 2027 target | Native Windows sidecar build, safe file semantics, signed installer, and clean-machine core flow |
| Linux and watchOS | No plan; unsupported | No build, QA, package, or compatibility claim |

The current Python sidecar is a desktop child process. Tauri mobile support
does not make that process model portable to iOS, iPadOS, or Android. Mobile
runtime work therefore belongs to a later design and Road. The accepted
desktop sidecar remains unchanged by that future decision.

### Release identity

Road v0.6 locks the invited Alpha identity before implementation:

- app version: `0.6.0`;
- bundle identifier: keep the existing `app.keikeu.desktop`;
- distributed filename:
  `keikeu-0.6.0-alpha.<N>-macos-arm64.dmg`, beginning with `alpha.1`;
- increment `<N>` whenever a previously hash-bound or distributed candidate is
  replaced.

The candidate suffix distinguishes invited artifacts without putting a
prerelease string into the macOS app version.

## 6. Release architecture and data flow

The release path is linear:

```text
exact source commit
  → current automated checks
  → arm64 PyInstaller sidecar
  → Tauri release build with Developer ID signing
  → default DMG
  → verify app, nested sidecar, DMG signatures, arm64, and image integrity
  → record pre-staple SHA-256
  → submit the distributed DMG with notarytool
  → bind the submission ID to that hash
  → require Accepted and inspect the matching notarization log
  → confirm the submitted DMG is still byte-identical
  → staple and validate the DMG
  → reverify signatures, image integrity, Gatekeeper, and architecture
  → calculate final post-staple SHA-256
  → local mounted-DMG install and smoke
  → independent developer rehearsal
  → second-user MVP Gate
```

Responsibilities stay narrow:

| Component | Responsibility |
| --- | --- |
| Existing Python build script | Build the target-specific arm64 sidecar |
| Existing Tauri CLI and configuration | Build the app, apply configured Developer ID signing through the bundle, and create the default DMG |
| macOS Keychain | Hold the Developer ID identity, its private key, and the chosen notary credential profile |
| Apple `notarytool` | Submit the distributed DMG, return its submission ID and status, and expose its log |
| Apple `stapler` | Attach and validate the notarization ticket on the distributed DMG |
| Apple/macOS verification tools | Establish signature, architecture, disk-image, Gatekeeper, and ticket evidence |
| Release manual | Explain the one approved human procedure and its stop conditions |
| Acceptance records | Preserve only de-identified conclusions and reproducible evidence |

Tauri's automatic notarization credential paths are not used in this Road.
The manual path keeps notarization credentials in one `notarytool` Keychain
profile and performs submission and log review explicitly. This makes the
process teachable without placing credentials in repository files, `.env`
files, command history, screenshots, or CI.

Notarization deliberately uploads the signed release artifact to Apple's
notary service. This is a developer-initiated release operation, not network
behavior in keikeu. No Vault, synthetic fixture, author content, credential,
or local release log may be bundled into that artifact.

The pre-staple DMG hash identifies exactly what was submitted. Stapling after
`Accepted` is the only authorized post-submission mutation. Any other source,
config, signature, bundle, or DMG byte change creates a new candidate that
must be verified and notarized again. The final distributable identity is the
post-staple hash.

## 7. Manual contract

Create one runbook at:

`docs/manual/macos-developer-id-release.md`

The manual is non-authoritative teaching material. Acceptance and stop rules
remain in the active Road specification, plan, and `docs/RULES.md`. If the
manual conflicts with authority or observed tools, fix the manual.

The manual must contain:

1. Scope, supported machine, output artifact, and stop conditions.
2. A short explanation of Developer ID signing, notarization, stapling, and
   Gatekeeper, including what each does not prove.
3. One-time Apple Developer, certificate, private-key, and Keychain notary
   profile setup.
4. Per-candidate preflight: clean source identity, commit, version, bundle ID,
   target, minimum macOS, tool versions, signing identity, checks, and output
   location.
5. One exact build-to-DMG procedure using the repository's actual commands.
6. One exact submission, submission-ID/pre-staple-hash binding, log-review,
   staple, final verification, and post-staple-hash procedure.
7. Expected outcomes and stop conditions for every step.
8. Recipient-style installation, first launch, core-flow, quit, and relaunch
   checks.
9. A compact troubleshooting path for identity, signing, notarization,
   stapling, Gatekeeper, and runtime failures.
10. Evidence redaction, artifact naming, hash recording, tester transfer, and
    safe cleanup.

Do not add parallel API-key, Apple-ID environment-variable, CI, App Store,
PKG, or custom-DMG tutorials. Do not copy an Apple error-code encyclopedia.

CP3 proves the manual is usable: the developer opens a new Terminal and
performs the complete release without the Agent issuing commands, editing the
instructions during the run, or supplying missing steps.

## 8. Checkpoint sequence

No form of YOLO may replace current evidence review in Road v0.6. The
developer must inspect the evidence and explicitly pass each checkpoint. An
unpassed checkpoint never seeds the next checkpoint branch.

### CP0 — Release contract and identity readiness

Entry:

- Road v0.5 is complete.
- The written Road v0.6 design and implementation plan are approved.
- The checkpoint starts from the last approved commit.

Work:

- Apply the locked `0.6.0`, `app.keikeu.desktop`, arm64 target, macOS 15.7
  floor, candidate filename rule, and invited Alpha wording.
- Record the platform matrix and unsupported boundaries in active authority.
- Confirm a valid paid Apple Developer membership, an available `Developer ID
  Application` identity and private key, and one local Keychain notary profile.
- Establish the manual skeleton and credential boundary.
- Teach the distinction between signing, notarization, stapling, and
  Gatekeeper.

Exit:

- The release contract has no unresolved identity, account, toolchain, target,
  or credential prerequisite.
- The developer can explain the four trust-chain concepts.
- Only redacted identity evidence is recorded.

### CP1 — Repeatable arm64 candidate

Entry:

- CP0 was explicitly passed and committed.

Work:

- Build from the exact clean source state using the documented toolchain.
- Run the current Python, Vue, Rust, build, and documentation checks.
- Build the arm64 sidecar and release candidate.
- Exercise an installed candidate with a synthetic Vault.
- Refine the manual using the commands that actually ran.

Exit:

- The app and sidecar are arm64 only.
- Version, bundle ID, and minimum macOS are correct.
- Installed launch, core synthetic flow, quit, and relaunch succeed.
- Commands, actual results, tool versions, omissions, exact source commit,
  and sidecar SHA-256 are recorded without copying old pass counts.

CP1 does not claim Developer ID trust-chain completion.

### CP2 — Developer ID trust chain

Entry:

- CP1 was explicitly passed and committed.
- The accepted identity and Keychain notary profile are available.

Work:

- Produce the signed app and default DMG.
- If the pinned Tauri build leaves only the outer DMG unsigned, sign that DMG
  exactly once before the pre-staple hash. This is part of candidate creation,
  not permission to re-sign internal app content or repair a failed candidate.
- Before submission, verify the app main executable, nested sidecar, outer
  DMG signatures, app/sidecar identity agreement, hardened runtime and secure
  timestamps on executable code, target architecture, and disk-image
  integrity.
- Record the pre-staple SHA-256.
- Submit the distributed DMG with `notarytool`.
- Bind the submission ID to that hash, require the same submission's status to
  be `Accepted`, and inspect its log. The log must contain no error; every
  warning must be resolved or explicitly shown to be non-blocking.
- Confirm the DMG still matches the submitted pre-staple hash.
- Staple and validate the DMG, then repeat signature, disk-image, architecture,
  and Gatekeeper assessment. Gatekeeper must identify a notarized Developer ID
  result, not merely return exit code zero.
- Calculate the final SHA-256 after stapling.
- Mount the DMG locally, copy the app to Applications, and rerun the synthetic
  launch/core-flow/quit/relaunch smoke.

Exit:

- The signature, identity agreement, notarization, log, staple, disk-image,
  architecture, Gatekeeper, local install, launch, and relaunch evidence all
  pass.
- No ad-hoc signature, Gatekeeper bypass, or in-place artifact patch was used.
- The manual describes the actual successful path and observed recovery steps.

CP2 proves the trust-chain procedure on the current workstation. It does not
reuse old CP13 evidence or yet claim that its candidate is the final
macOS 15.7-tested artifact.

### CP3 — Independent developer release rehearsal

Entry:

- CP2 was explicitly passed and committed.
- The manual is frozen for the attempt.
- The rehearsal starts from the exact clean source state named by the manual.

Work:

- The developer, not the Agent, opens a new Terminal and follows only the
  manual from identity check through final hash and installed-app smoke.
- The developer maps every verification command to the conclusion it proves.
- The independently produced final-hash DMG is installed on a real macOS 15.7
  host and completes the synthetic core flow, quit, and relaunch. If no such
  host is available, CP3 pauses unless the developer explicitly revises the
  supported minimum; older evidence cannot substitute for the exact artifact.

Exit:

- Agent intervention during execution is zero.
- No command or prerequisite is supplied outside the manual.
- The full release and smoke succeed.
- The same final-hash artifact has current macOS 15.7 compatibility evidence.
- The developer explicitly confirms independent reproduction and conceptual
  understanding.

If the run needs an Agent repair, CP3 fails. Fix the manual, discard the
candidate when required, and repeat the complete rehearsal.

### CP4 — Invited Alpha and second-user MVP Gate

Entry:

- CP3 was explicitly passed and committed.
- The tester's Mac is confirmed as Apple Silicon with macOS 15.7 or later.
- Managed-device status is known, and any device-management policy permits a
  Developer ID DMG and the external-editor handoff.
- The sent DMG hash matches the accepted CP3 artifact.

Work:

- Give the tester a one-page privacy, installation, task, and stop guide.
- Do not give a feature tour.
- Transfer the DMG through a path that gives it quarantine metadata. Confirm
  that metadata exists; do not remove it or bypass Gatekeeper.
- Ask the tester to create a dedicated test Vault and use one real inspiration
  they are willing to copy into that Vault.
- Observe normal drag-to-Applications installation, first Gatekeeper launch,
  Vault creation, Paper organization, save, Flashcard, external-editor
  handoff, about ten minutes of prose writing, quit/relaunch, and Paper
  retrieval.
- Record completion, hesitation, intervention count, and de-identified
  verbatim feedback only.
- Ask one non-leading value question after the task: whether keikeu made
  starting the writing easier and whether they would choose to use it again
  for another inspiration.

The moderator may explain privacy, the task, and the stop condition. Any
keikeu click-path instruction counts as intervention. If the tester needs
rescue to complete a common core step, treat that as a P1 until fixed and
retested.

Exit:

- The tester completes the safety-critical core flow.
- No author content, Vault path, account, or device identifier is recorded.
- No unresolved P0/P1 remains.
- The tester supplies a concrete positive value signal: the workflow made
  starting easier or they would independently choose it again.
- Engineering release evidence and product evidence are reported separately.

If the tester is not within the supported machine boundary, CP4 does not
start. If device policy blocks Developer ID installation or the external
editor, CP4 also does not start.

If CP4 exposes a P0/P1, fix only that issue, create a new candidate and hash,
and rerun the CP1, CP2, and CP3 operational gates against the new candidate
before retesting. P2/P3 observations go to the next-Road candidate pool.

If the flow succeeds but the tester gives no positive value signal, the MVP
Gate fails without becoming a P1 and without authorizing new features. Record
the result and pause for a separate developer product decision.

A CP4 pass means only that the invited-user MVP Gate passed at `n = 1`. It
does not establish broad market validation or product-market fit.

## 9. Failure and recovery rules

| Failure | Required response |
| --- | --- |
| Worktree, commit, version, identity, architecture, or toolchain mismatch | Stop before producing a release candidate |
| Upload fails before a submission ID exists | Correct the transport problem and retry the same immutable artifact |
| A submission ID exists | Query that submission before considering another upload |
| Notarization returns `Invalid` | Read the log, correct source or configuration, discard the candidate, and rebuild from the exact source |
| Notarization is `Accepted` but staple fails | Confirm the DMG still matches its pre-staple hash, then retry staple; if a failed attempt changed it, discard the candidate |
| Signature, Gatekeeper, architecture, image, install, or runtime check fails | Do not distribute and do not bypass the check |
| A signed or submitted artifact needs a change other than the planned staple operation | Create a new candidate and repeat the trust chain |
| A tester already received a bad candidate | Retire its name/hash, issue a new candidate, and state which hash is current |
| Private key or credential exposure is suspected | Stop release work and handle credential response separately; ordinary build failures do not justify certificate revocation |

Forbidden recovery includes `xattr` removal, right-click-open acceptance,
disabling Gatekeeper, ad-hoc signing, `codesign --deep --force` as a repair
strategy, overwriting an already-issued candidate, or treating `Accepted` as
proof of runtime correctness.

## 10. Test and evidence model

| Conclusion | Minimum evidence |
| --- | --- |
| Source checks passed | Current commands and actual results for Python, Vue, Rust, compile, build, and docs checks |
| Candidate is arm64 and internally coherent | Exact source commit, sidecar SHA-256, app and nested-sidecar architecture, version, identifier, configured minimum macOS, signature structure, and synthetic installed-app smoke |
| Trust chain passed | App/main/sidecar/DMG signature checks, app/sidecar identity agreement, hardened runtime and timestamp summary, pre-staple hash bound to submission ID, `Accepted` status and issue-free reviewed log, staple validation, final Gatekeeper assessment, disk-image verification, and post-staple SHA-256 |
| Manual and final artifact are accepted | CP3 checklist executed by the developer with zero Agent intervention, an explicit understanding statement, and exact-final-hash macOS 15.7 install/core-flow/relaunch evidence |
| Second-user MVP Gate passed | Exact artifact hash, supported machine and policy boundary, quarantine-preserving transfer, normal Gatekeeper install/launch/relaunch, core-task completion, intervention count, hesitation points, and concrete de-identified value feedback |
| Road accepted | CP0–CP4 explicitly passed, no unresolved P0/P1, final checkpoint committed, and engineering/product conclusions recorded separately |

Acceptance records live under `docs/acceptance/road-v0-6/`. They contain no
raw notarization log, author prose, inspiration, relationships, Vault path,
email, Apple ID, credential, private-key material, or stable device
identifier. Raw logs and release artifacts stay local and outside Git.

## 11. Git and documentation boundaries

The pre-Road design document is a docs-only change and does not pass CP0.
Implementation checkpoint branches follow `docs/RULES.md`:

```text
docs/cp0-release-contract
build/cp1-arm64-candidate
build/cp2-developer-id-trust
docs/cp3-release-rehearsal
test/cp4-invited-alpha-gate
```

If CP4 requires a P0/P1 code fix, keep CP4 open and use a focused CP4 branch
name matching the actual content. Rerun the CP1–CP3 operational gates on that
candidate; do not invent duplicate passing checkpoints.

Every checkpoint:

- starts from the previous explicitly passed checkpoint commit;
- stages exact files only;
- requires explicit commit authorization;
- records checks, developer QA, omissions, and risks;
- excludes secrets, logs, environments, app bundles, DMGs, and author data;
- is not pushed automatically.

CP0 or its implementation plan assigns authority updates by responsibility:

- `docs/SPEC.md` — Road v0.6 product boundary and platform support promise;
- `docs/RULES.md` — durable credential, artifact, and evidence safeguards;
- `docs/PROJECT.md` — current checkpoint and next Gate;
- README files — reader-facing current platform support;
- `docs/manual/macos-developer-id-release.md` — non-authoritative release
  teaching;
- `docs/manual/invited-alpha-test-guide.md` — one-page tester privacy,
  installation, task, and stop guide;
- `docs/acceptance/road-v0-6/` — de-identified checkpoint evidence.

Road v0.6's no-YOLO condition stays in its active product boundary and plan;
it does not silently change the policy for unrelated future Roads.

After the final accepted CP4 commit, create
`docs/archive/snapshots/road-v0-6.html` as a separate closeout change. A
snapshot, tag, commit, push, and public release are separate decisions.

## 12. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Existing beta macOS/Xcode exception is mistaken for release approval | CP0 inventories the actual release workstation and stops unless its toolchain is explicitly accepted for Developer ID release |
| Bundled Python sidecar fails hardened-runtime or notarization checks | Verify and diagnose the nested sidecar before submission; never patch it after the outer app is signed |
| Secrets leak through environment files, screenshots, logs, or Git | Use Keychain identities and one notary profile; preserve only redacted summaries |
| A local build is mistaken for tester-ready | CP2 trust-chain and install gates are independent of CP1 build success |
| The Agent masks an unusable manual | CP3 requires a developer-only execution with zero Agent intervention |
| The tester receives a different artifact from the accepted one | Bind local evidence, handoff, and tester confirmation to the post-staple SHA-256 |
| One user's feedback expands scope | Fix only observed P0/P1; defer P2/P3 |
| A newer tester Mac is mistaken for macOS 15.7 compatibility | Require the same final-hash DMG to run on a real macOS 15.7 host |
| Future platform dates become false promises | Keep non-macOS entries behind explicit engineering or feasibility Gates |

## 13. Completion definition

Road v0.6 is complete only when:

1. CP0–CP4 have each been explicitly passed without any YOLO substitute for
   current evidence review.
2. The final DMG is arm64-only, signed with Developer ID, notarized, stapled,
   Gatekeeper-accepted, hash-bound, and install/core-flow/relaunch tested on a
   real macOS 15.7 host.
3. The developer independently reproduced and explained the release process
   using the manual.
4. The second user completed the core workflow on a supported Mac with no
   unresolved P0/P1 and supplied a concrete positive value signal.
5. The final checkpoint is committed and the separate closeout records the
   Road without implying a tag, push, public release, or other-platform
   support.

## 14. Primary references

- [Tauri macOS code signing and notarization](https://v2.tauri.app/distribute/sign/macos/)
- [Tauri DMG distribution](https://v2.tauri.app/distribute/dmg/)
- [Apple: Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Apple: Customizing the notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow)
- [Apple: Resolving common notarization issues](https://developer.apple.com/documentation/security/resolving-common-notarization-issues)
- [Tauri sidecars](https://v2.tauri.app/develop/sidecar/)
- [Tauri Shell supported platforms](https://v2.tauri.app/plugin/shell/)
