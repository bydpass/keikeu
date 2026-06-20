"""Rebuildable metadata index for keikeu (appdesign.md Step 5).

Pure Python. No Flet, no GUI, no third-party dependencies.

The index is ``<vault>/keikeu_index.json``, shaped::

    {"version": 1, "caches": [...], "outlines": [...]}

It exists only to make the GUI's list views fast; it is NOT the source of
truth. Product invariant 2: the Markdown files are the user asset and the
index is auxiliary, derivable from Markdown alone. So a missing or corrupt
index is disposable — it is silently rebuilt by re-reading every cache and
outline — but a user's Markdown file is never deleted or modified to "fix"
the index.

Parsing stays in :mod:`keikeu_core.markdown_io` (``read_cache`` /
``read_outline``); this module only walks the vault, projects each parsed
model down to a flat entry dict, and reads/writes the one JSON file.
"""

from __future__ import annotations

import json
from pathlib import Path

from keikeu_core.markdown_io import read_cache, read_outline
from keikeu_core.models import Cache, Outline

__all__ = [
    "rebuild_index",
    "load_index",
    "save_index",
    "list_caches",
    "list_outlines",
]


def _index_path(vault: Path) -> Path:
    """Return the index file path inside vault directory ``vault``."""
    return vault / "keikeu_index.json"


def _write_json(target: Path, obj: object) -> None:
    """Write ``obj`` as JSON to ``target`` with the project's fixed style.

    Matches ``vault._write_json``: ``indent=2``, ``ensure_ascii=False`` (fandom
    and titles are often CJK), and a trailing newline so diffs stay clean.
    """
    with target.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _cache_entry(vault: Path, path: Path, cache: Cache) -> dict:
    """Project a parsed ``Cache`` down to its flat index entry.

    ``path`` is stored relative to ``vault`` (e.g. ``cache/...slug.md``) so the
    index does not bake in an absolute machine path; datetimes become ISO
    strings and the status enum becomes its backing value.
    """
    return {
        "type": "cache",
        "title": cache.title,
        "path": str(path.relative_to(vault)),
        "status": cache.status.value,
        "created": cache.created.isoformat(),
        "updated": cache.updated.isoformat(),
        "linked_outline": cache.linked_outline,
    }


def _outline_entry(vault: Path, path: Path, outline: Outline) -> dict:
    """Project a parsed ``Outline`` down to its flat index entry.

    ``path`` is relative to ``vault``; datetimes become ISO strings and the
    ending-type enum becomes its backing value.
    """
    return {
        "type": "outline",
        "title": outline.title,
        "path": str(path.relative_to(vault)),
        "created": outline.created.isoformat(),
        "updated": outline.updated.isoformat(),
        "ending_type": outline.ending_type.value,
    }


def rebuild_index(vault: Path) -> None:
    """Rebuild ``<vault>/keikeu_index.json`` from the Markdown files alone.

    Scans ``vault/cache/*.md`` via :func:`markdown_io.read_cache` and
    ``vault/outlines/*.md`` via :func:`markdown_io.read_outline`, projects each
    to a flat entry, and overwrites the index. Files are visited in sorted
    filename order so the written index is deterministic and diff-stable.

    This only ever READS Markdown; it never deletes or modifies a user asset.
    """
    caches = [
        _cache_entry(vault, path, read_cache(path))
        for path in sorted((vault / "cache").glob("*.md"))
    ]
    outlines = [
        _outline_entry(vault, path, read_outline(path))
        for path in sorted((vault / "outlines").glob("*.md"))
    ]
    index = {"version": 1, "caches": caches, "outlines": outlines}
    save_index(vault, index)


def _is_valid_index(data: object) -> bool:
    """True iff ``data`` has the shape the list helpers rely on.

    Requires a dict carrying ``caches`` and ``outlines`` lists. Anything else —
    a JSON ``null``/array/number/string, or a dict missing a key — is treated as
    corrupt so :func:`load_index` rebuilds rather than handing back a value that
    would make :func:`list_caches`/:func:`list_outlines` raise.
    """
    return (
        isinstance(data, dict)
        and isinstance(data.get("caches"), list)
        and isinstance(data.get("outlines"), list)
    )


def load_index(vault: Path) -> dict:
    """Return the parsed index dict, rebuilding first if it is unusable.

    If the index file is missing, not valid JSON, OR valid JSON of the wrong
    shape (e.g. a truncated-but-still-parseable or hand-edited file that is not a
    dict carrying ``caches``/``outlines`` lists), it is rebuilt from the Markdown
    and then loaded. A corrupt index is disposable; the rebuild reads — never
    deletes or rewrites — the user's Markdown files (product invariant 2). This
    keeps :func:`list_caches`/:func:`list_outlines` total: they never crash on a
    damaged index.
    """
    path = _index_path(vault)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        # OSError: missing/unreadable. ValueError: invalid JSON
        # (json.JSONDecodeError is a ValueError subclass).
        data = None
    if not _is_valid_index(data):
        # Disposable index — rebuild from the source-of-truth Markdown.
        rebuild_index(vault)
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    return data


def save_index(vault: Path, index: dict) -> None:
    """Write ``index`` to ``<vault>/keikeu_index.json`` in the fixed style."""
    _write_json(_index_path(vault), index)


def list_caches(vault: Path) -> list[dict]:
    """Return the index's ``caches`` entries (rebuilding the index if needed)."""
    return load_index(vault)["caches"]


def list_outlines(vault: Path) -> list[dict]:
    """Return the index's ``outlines`` entries (rebuilding the index if needed)."""
    return load_index(vault)["outlines"]
