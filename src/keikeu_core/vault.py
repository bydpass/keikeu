"""Paper v2 vault layout, recovery bin, and local config resolution.

The user-selected vault holds only durable Paper Markdown and a disposable
index.  Recovery moves a file under ``.trash/cache``; it never copies or
rewrites an asset unless a code collision requires an explicitly requested
new Paper code.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from keikeu_core.markdown_io import copy_paper_with_code, read_paper
from keikeu_core.models import validate_paper_code

__all__ = [
    "init_vault",
    "is_vault",
    "soft_delete",
    "list_trashed_papers",
    "restore_paper",
    "get_vault",
    "set_vault",
]

_EMPTY_INDEX: dict[str, object] = {"version": 2, "papers": [], "errors": []}


def _index_path(vault: Path) -> Path:
    return vault / "keikeu_index.json"


def _write_json(target: Path, obj: object) -> None:
    with target.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def init_vault(path: Path) -> None:
    """Create the v2 Paper layout without changing existing user data.

    New vaults contain ``cache/``, ``.trash/cache/``, and a v2 empty index.
    Existing Outline directories and an existing index are left untouched so
    this helper cannot damage a vault that still needs migration.
    """
    path.mkdir(parents=True, exist_ok=True)
    (path / "cache").mkdir(parents=True, exist_ok=True)
    (path / ".trash" / "cache").mkdir(parents=True, exist_ok=True)
    index_path = _index_path(path)
    if not index_path.exists():
        _write_json(index_path, _EMPTY_INDEX)


def is_vault(path: Path) -> bool:
    """Return whether ``path`` has the minimum usable v2 vault structure."""
    return path.is_dir() and (path / "cache").is_dir() and _index_path(path).is_file()


def _direct_asset_path(vault: Path, rel_path: str, parent: tuple[str, ...]) -> Path:
    """Resolve a direct Markdown asset path below one allowed vault directory."""
    rel = Path(rel_path)
    if rel.is_absolute() or rel.parts[: len(parent)] != parent or len(rel.parts) != len(parent) + 1:
        expected = "/".join(parent) + "/*.md"
        raise ValueError(f"expected {expected}")
    if rel.suffix != ".md" or not rel.stem:
        expected = "/".join(parent) + "/*.md"
        raise ValueError(f"expected {expected}")
    return vault / rel


def _soft_delete_target(vault: Path, source: Path) -> Path:
    trash_dir = vault / ".trash" / "cache"
    trash_dir.mkdir(parents=True, exist_ok=True)
    target = trash_dir / source.name
    while target.exists():
        target = trash_dir / f"{source.stem}-{secrets.token_hex(4)}{source.suffix}"
    return target


def soft_delete(vault: Path, rel_path: str) -> Path:
    """Move an active ``cache/*.md`` Paper to recovery without overwriting.

    The file move preserves bytes exactly.  A duplicate recovery filename gains
    a random suffix; its Paper frontmatter remains the durable code authority.
    """
    source = _direct_asset_path(vault, rel_path, ("cache",))
    target = _soft_delete_target(vault, source)
    source.replace(target)
    return target


def list_trashed_papers(vault: Path) -> list[Path]:
    """Return sorted vault-relative paths for all direct recovery files."""
    trash_dir = vault / ".trash" / "cache"
    if not trash_dir.is_dir():
        return []
    return [path.relative_to(vault) for path in sorted(trash_dir.glob("*.md"))]


def restore_paper(vault: Path, rel_path: str, new_code: str | None = None) -> Path:
    """Restore a trashed Paper, requiring a new code only on active collision.

    A normal restore moves the original file bytes to its code-derived active
    path.  If that code is already active, the caller must either cancel or
    supply an unused ``new_code``.  The latter rewrites only the Paper code via
    ``markdown_io`` while preserving the frozen draft and current Summary.
    """
    source = _direct_asset_path(vault, rel_path, (".trash", "cache"))
    paper = read_paper(source)
    target = vault / "cache" / f"{paper.code}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    if not target.exists():
        if new_code is not None and validate_paper_code(new_code) != paper.code:
            new_target = vault / "cache" / f"{new_code}.md"
            if new_target.exists():
                raise FileExistsError(f"Paper already exists: {new_target}")
            copy_paper_with_code(source, new_target, new_code)
            try:
                source.unlink()
            except OSError:
                new_target.unlink(missing_ok=True)
                raise
            return new_target
        source.replace(target)
        return target

    if new_code is None:
        raise FileExistsError("Paper code is already active; choose a new Paper code or cancel")
    new_code = validate_paper_code(new_code)
    target = vault / "cache" / f"{new_code}.md"
    if target.exists():
        raise FileExistsError(f"Paper already exists: {target}")
    copy_paper_with_code(source, target, new_code)
    try:
        source.unlink()
    except OSError:
        target.unlink(missing_ok=True)
        raise
    return target


def get_vault(config_path: Path) -> Path | None:
    """Return the configured vault path, or ``None`` for absent/bad config."""
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            obj = json.load(handle)
    except (OSError, ValueError):
        return None
    value = obj.get("vault") if isinstance(obj, dict) else None
    return Path(value) if isinstance(value, str) else None


def set_vault(path: Path, config_path: Path) -> None:
    """Persist the selected vault path using the project's JSON style."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(config_path, {"vault": str(path)})
