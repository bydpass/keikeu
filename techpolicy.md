# keikeu TECHPOLICY.md

## Fixed Stack

- Python 3
- Flet
- Markdown files
- JSON index
- GitHub repo

## Development Policy

Human-led development with agentic coding assistance.

The developer must understand:

- every dependency
- every file structure decision
- every data model
- every build command
- every release artifact

Agentic coding may generate code, but cannot own architecture decisions.

## Release Route

1. macOS Paper–Flashcard Core
2. iPhone / iPadOS file-service parity
3. Android
4. Windows

Optional Outline work follows the separate Pre-Advance Road and does not block the macOS core.

## Forbidden Before MVP

- keikeu-operated cloud backend, account, or background sync
- account system
- external fandom database
- AI-required workflow
- complex graph system
- social features
- plugin architecture
- premature Windows/Linux compatibility work

## User-Selected File Services

- A vault may live in a normal local directory or an OS-exposed third-party file-service directory such as iCloud Drive, Dropbox, or OneDrive.
- keikeu treats these as ordinary filesystem paths.
- keikeu does not call provider APIs, manage provider accounts, promise sync timing, or merge creative-text conflicts.
- Core behavior must remain usable offline whenever the selected files are available locally.
