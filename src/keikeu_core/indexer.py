"""Rebuildable v2 Paper metadata index.

The index is only a local projection of active ``cache/*.md`` Papers.  Every
file is read independently so one malformed asset becomes an ``errors`` entry
instead of hiding valid Papers or changing any Markdown bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

from keikeu_core.markdown_io import read_paper
from keikeu_core.models import Paper

__all__ = [
    "rebuild_index",
    "load_index",
    "save_index",
    "list_papers",
    "list_index_errors",
]


def _index_path(vault: Path) -> Path:
    return vault / "keikeu_index.json"


def _write_json(target: Path, obj: object) -> None:
    with target.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _paper_entry(vault: Path, path: Path, paper: Paper) -> dict[str, object]:
    if path.stem != paper.code:
        raise ValueError("Paper filename must match frontmatter code")
    return {
        "code": paper.code,
        "path": str(path.relative_to(vault)),
        "summary": paper.summary,
        "tags": paper.tags,
        "created": paper.created.isoformat(),
        "updated": paper.updated.isoformat(),
    }


def rebuild_index(vault: Path) -> dict[str, object]:
    """Rebuild and return the v2 index from active Paper Markdown only."""
    papers: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    cache_dir = vault / "cache"
    paths = sorted(cache_dir.glob("*.md")) if cache_dir.is_dir() else []
    for path in paths:
        try:
            papers.append(_paper_entry(vault, path, read_paper(path)))
        except (OSError, ValueError) as exc:
            errors.append({"path": str(path.relative_to(vault)), "reason": str(exc)})
    index: dict[str, object] = {"version": 2, "papers": papers, "errors": errors}
    save_index(vault, index)
    return index


def _is_valid_index(data: object) -> bool:
    return (
        isinstance(data, dict)
        and data.get("version") == 2
        and isinstance(data.get("papers"), list)
        and isinstance(data.get("errors"), list)
    )


def load_index(vault: Path) -> dict[str, object]:
    """Load v2 metadata, rebuilding only when its JSON is missing or invalid."""
    try:
        with _index_path(vault).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        data = None
    if not _is_valid_index(data):
        return rebuild_index(vault)
    return data


def save_index(vault: Path, index: dict[str, object]) -> None:
    """Write the disposable index without touching Markdown assets."""
    _write_json(_index_path(vault), index)


def list_papers(vault: Path) -> list[dict[str, object]]:
    """Return indexed active Papers; callers may explicitly rebuild to refresh."""
    return load_index(vault)["papers"]  # type: ignore[return-value]


def list_index_errors(vault: Path) -> list[dict[str, str]]:
    """Return isolated parse errors from the last usable index rebuild."""
    return load_index(vault)["errors"]  # type: ignore[return-value]
