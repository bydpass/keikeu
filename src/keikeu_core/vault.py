"""Local vault layout and config resolution for keikeu (appdesign.md Step 3).

Pure Python. No Flet, no GUI, no third-party dependencies.

A vault is a user-chosen directory holding two asset folders and a
rebuildable metadata index::

    <vault>/
        cache/                 # inspiration caches (灵感缓存)
        outlines/              # outline Markdown (大纲)
        keikeu_index.json      # auxiliary, rebuildable from Markdown alone

Markdown files are the user asset; ``keikeu_index.json`` is auxiliary and
must be rebuildable from Markdown alone (product invariant 2). Init must
therefore never clobber an existing index.

The config file records which directory is the active vault. Its location
differs between desktop and mobile, so this layer takes an injected
``config_path`` and never hardcodes ``~/.keikeu_config.json``; the Flet
layer decides where config lives.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "init_vault",
    "is_vault",
    "get_vault",
    "set_vault",
]

# Empty index written only when one does not already exist.
_EMPTY_INDEX: dict[str, object] = {"version": 1, "caches": [], "outlines": []}


def _index_path(path: Path) -> Path:
    """Return the index file path inside vault directory ``path``."""
    return path / "keikeu_index.json"


def _write_json(target: Path, obj: object) -> None:
    """Write ``obj`` as JSON to ``target`` with the project's fixed style.

    Uses ``indent=2``, ``ensure_ascii=False`` (fandom text is often CJK),
    and a trailing newline so the file is diff-friendly.
    """
    with target.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def init_vault(path: Path) -> None:
    """Create the vault layout at ``path``, idempotently and non-destructively.

    Creates ``path/``, ``path/cache/`` and ``path/outlines/`` (parents and
    existing directories are tolerated). Writes ``keikeu_index.json`` ONLY
    if it does not already exist, so calling this twice — or pointing it at
    an existing vault — never overwrites user data in the index.
    """
    path.mkdir(parents=True, exist_ok=True)
    (path / "cache").mkdir(parents=True, exist_ok=True)
    (path / "outlines").mkdir(parents=True, exist_ok=True)
    index = _index_path(path)
    if not index.exists():
        _write_json(index, _EMPTY_INDEX)


def is_vault(path: Path) -> bool:
    """Return True iff ``path`` is a fully-formed keikeu vault.

    Requires ``path`` to be a directory containing both ``cache/`` and
    ``outlines/`` directories and a ``keikeu_index.json`` file. Returns
    False (never raises) for a missing or partial layout.
    """
    return (
        path.is_dir()
        and _index_path(path).is_file()
        and (path / "cache").is_dir()
        and (path / "outlines").is_dir()
    )


def get_vault(config_path: Path) -> Path | None:
    """Return the configured vault path, or None if it cannot be resolved.

    Reads the JSON object at ``config_path`` and returns ``Path(obj["vault"])``
    when present. Returns None — never raises — when the file is missing,
    unreadable, not valid JSON, not a JSON object, or lacks a ``"vault"`` key.
    """
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, ValueError):
        # OSError: missing/unreadable. ValueError: invalid JSON
        # (json.JSONDecodeError is a ValueError subclass).
        return None
    if not isinstance(obj, dict) or "vault" not in obj:
        return None
    value = obj["vault"]
    # A syntactically valid but hand-edited/corrupt config may carry a
    # non-string "vault" (number, null, list). Path(...) would raise TypeError,
    # breaking the "never raises" contract, so treat it as unresolved.
    if not isinstance(value, str):
        return None
    return Path(value)


def set_vault(path: Path, config_path: Path) -> None:
    """Record ``path`` as the active vault in the config at ``config_path``.

    Creates ``config_path``'s parent directories if needed, then writes
    ``{"vault": str(path)}`` in the project's fixed JSON style.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(config_path, {"vault": str(path)})
