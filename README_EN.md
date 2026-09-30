# keikeu

> A local-first pre-writing tool for fanfiction authors: shape existing ideas into editable, repairable Markdown card-page Papers, then hand them to the prose editor you already use.

[简体中文](README.md) | English

![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20(Apple%20Silicon)-lightgrey)
![Status](https://img.shields.io/badge/status-personal%20dev%20build-orange)

## What keikeu is

keikeu is built for a single fanfiction author and covers only the stage before prose:

```text
existing inspiration → edit and save a card-page Paper → external prose editor
```

What you keep is plain Markdown that any text editor can open, read, and repair. keikeu has no accounts, cloud backend, telemetry, AI ghostwriting, fandom database, community features, or built-in prose editor.

## What it does today

- **Card-page Papers:** a Paper has an optional display name, Tags, and at least one ordered card page. Each page has an optional title, Markdown content, and a type of Summary, Snapshot, Whisper, or none; a Paper has at most one Summary.
- **Split at the cursor:** "Add page" splits the current page at the cursor and moves the rest into a new page.
- **Whole-Paper save:** one save commits the entire Paper and checks whether the file changed while you were editing. Unsaved work is guarded when you switch Paper or Vault, navigate, or close the window.
- **Library:** search every page, filter and sort by all, unfiled, or one-level folders, and move, branch, trash, or restore Papers.
- **Vault:** a local folder you choose inside your Home directory. An iCloud Documents route exists as an opt-in candidate and is not yet formally accepted.
- **Recovery:** a damaged Paper keeps its original bytes, explains the error, and can be exported. When a write result is unknown, keikeu checks read-only before the next write. Older formats migrate only after a full backup.

## Status

| Item | State |
| --- | --- |
| Accepted product baseline | Road v0.7 CP8 (`2f03aee`): Paper v4, Index v4, JSONL protocol v2 |
| Latest engineering cleanup | Road v09 CP0–CP4 (`c615ce5`): source layout, pure Rust rules crate, developer tools and docs |
| Next | Replace the iOS UI with native SwiftUI while reusing the Rust core; see the [handoff](docs/road-v09-01-handoff.md) |
| Distribution | Personal development build; no signed, notarized, or public installer |

[PROJECT](docs/PROJECT.md) holds live progress and evidence boundaries.

## Platforms

| Platform | Implementation | State |
| --- | --- | --- |
| macOS, local Vault | Vue/Vite → Tauri/Rust host → Python sidecar | Accepted desktop baseline |
| macOS, iCloud Vault | In-process Rust Paper Core + native Apple file coordination | Candidate, not formally accepted |
| iPhone | Earlier Vue/Tauri candidate, to be replaced by native SwiftUI | Planned |
| Windows / Android | Vue/Tauri/Python route kept / native work scheduled separately | Unscheduled, no runnable package |

## Run from source (macOS)

Requires an Apple Silicon Mac, Python `>=3.11,<3.14`, Node `22.23.2` / npm `10.9.8`, and Rust `1.88.0` (pinned by `rust-toolchain.toml`).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip install -r requirements-build.lock
npm --prefix apps/desktop ci
./dev
```

`./dev` is a developer terminal panel: press `a` to launch with the existing sidecar or `b` to rebuild the sidecar first. It also shows logs for the processes it manages and lets you browse local docs. For direct troubleshooting, use the underlying commands:

```bash
.venv/bin/python scripts/build_sidecar.py
npm --prefix apps/desktop run tauri:dev
```

## Tests

```bash
.venv/bin/python -m pytest
npm --prefix apps/desktop run test
cargo test --workspace --locked
.venv/bin/python scripts/check_docs.py
```

Synthetic Vaults and temporary output from automated tests go to the ignored `tests/test-vault/`, never to your real Vault.

## Repository layout

```text
apps/desktop/src/                  Vue UI
apps/desktop/src-tauri/            Tauri/Rust host, storage routing, and recovery
apps/desktop/python/keikeu_core/   pure-Python domain and file logic
apps/desktop/python/keikeu_bridge/ application service, JSONL protocol, and sidecar
crates/keikeu-core/                Rust Paper rules with no file access
platforms/apple/                   native Apple host and file coordination
scripts/                           build, context packing, and doc checks
tests/                             Python tests and versioned fixtures
docs/                              product, rules, design, architecture, acceptance, manuals
dev                                developer terminal panel
```

Hard rules: `keikeu_core` never depends on a GUI or transport; only backends read and write Markdown; the pure Rust rules crate never touches files.

## Documentation

| Question | Entry point |
| --- | --- |
| Product purpose and author-control boundary | [SPEC](docs/SPEC.md) |
| Current progress and next step | [PROJECT](docs/PROJECT.md) |
| Rules every change must follow | [RULES](docs/RULES.md) |
| Architecture | [Architecture map](docs/architecture/architecture.html) |
| Desktop visual and interaction specs | [Design map](docs/design/design.html), [Interaction map](docs/design/interaction.html) |
| How agents work here | [AGENTS](AGENTS.md) |
| Human guides to tech, design, Git, and ethics | [Manuals](docs/manual/README.md) |
| Construction snapshots of past Roads | [Archive](docs/archive/snapshots/) |

Core project docs are written in Simplified Chinese.

## Roadmap

| Stage | Scope | Result |
| --- | --- | --- |
| v0.1–v0.2 | macOS prototype, Paper / Flashcard Core | v0.1 archived, v0.2 accepted |
| Road v0.3 | Paper Library | Accepted and archived |
| Road v0.4 | Vue/Tauri frontend, Flet retired | [Accepted](docs/acceptance/road_v0_4_cp14.md) |
| Road v0.5 | Quiet Desk UI and interaction closeout | [Accepted](docs/archive/snapshots/road-v0-5.html) |
| Road v0.6 | Paper v4 card-page rebuild | [Accepted](docs/archive/snapshots/road-v0-6.html) |
| Road v0.7 | Continuous editing, responsive layout, native IME | [Accepted](docs/archive/snapshots/road-v0-7.html) |
| Road v0.8 | Unified Rust core and iCloud candidate | Interrupted and handed off; not accepted |
| Road v09 | Source layout and workflow cleanup | [Complete](docs/archive/snapshots/road-v09.html) |
| Next | Native SwiftUI iOS | Planned |
| Later | Desktop parity, Python retirement, external Alpha, Android | Scheduled separately |

## License

Code and accompanying documentation are licensed under [GPL-3.0-or-later](LICENSE). Papers, Vaults, and exports you create are not keikeu assets; their rights stay with you.
