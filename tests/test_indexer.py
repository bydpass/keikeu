"""Tests for keikeu_core.indexer — the rebuildable metadata index (Step 5).

The index is auxiliary, not the source of truth (product invariant 2): it is
derived from the Markdown files and may be rebuilt at will, but the rebuild
must never touch a user asset. These tests pin the entry shape (relative path,
ISO datetimes, enum values), deterministic ordering, missing/corrupt-index
recovery, and the headless stdlib-only import closure.

Setup goes through the real public surface — ``vault.init_vault`` plus
``markdown_io.write_cache`` / ``write_outline`` — so the index is exercised
against genuine on-disk Markdown, not hand-built fixtures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from keikeu_core import vault as vault_mod
from keikeu_core.indexer import (
    list_caches,
    list_outlines,
    load_index,
    rebuild_index,
)
from keikeu_core.markdown_io import write_cache, write_outline
from keikeu_core.models import Cache, EndingType, Outline


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _fresh_vault(tmp_path: Path) -> Path:
    """Init a vault under ``tmp_path`` and return its directory."""
    vault = tmp_path / "vault"
    vault_mod.init_vault(vault)
    return vault


# --------------------------------------------------------------------------- #
# Rebuild from cache files
# --------------------------------------------------------------------------- #


def test_rebuild_from_cache_files(tmp_path):
    vault = _fresh_vault(tmp_path)
    c1 = Cache(
        title="first spark",
        raw="what if they met on a train",
        status="raw",
        created=datetime(2026, 6, 20, 9, 0, 0),
        updated=datetime(2026, 6, 20, 9, 5, 0),
    )
    c2 = Cache(
        title="second spark",
        raw="a letter never sent",
        status="drafting",
        created=datetime(2026, 6, 20, 10, 0, 0),
        updated=datetime(2026, 6, 20, 10, 0, 0),
        linked_outline="outlines/some-outline.md",
    )
    p1 = write_cache(vault, c1)
    write_cache(vault, c2)

    rebuild_index(vault)
    caches = list_caches(vault)

    assert len(caches) == 2
    assert list_outlines(vault) == []

    by_title = {e["title"]: e for e in caches}
    e1 = by_title["first spark"]
    assert e1["type"] == "cache"
    assert e1["path"] == str(p1.relative_to(vault))
    assert e1["path"].startswith("cache/")
    assert e1["status"] == "raw"
    assert e1["created"] == "2026-06-20T09:00:00"
    assert e1["updated"] == "2026-06-20T09:05:00"
    assert e1["linked_outline"] is None

    e2 = by_title["second spark"]
    assert e2["status"] == "drafting"
    assert e2["linked_outline"] == "outlines/some-outline.md"


# --------------------------------------------------------------------------- #
# Rebuild from outline files
# --------------------------------------------------------------------------- #


def test_rebuild_from_outline_files(tmp_path):
    vault = _fresh_vault(tmp_path)
    o1 = Outline(
        title="open ending one",
        ending_type="OE",
        created=datetime(2026, 6, 20, 11, 0, 0),
        updated=datetime(2026, 6, 20, 11, 30, 0),
    )
    o2 = Outline(
        title="custom ending two",
        ending_type="custom",
        custom_ending="they part ways but keep writing",
        created=datetime(2026, 6, 20, 12, 0, 0),
        updated=datetime(2026, 6, 20, 12, 0, 0),
    )
    write_outline(vault, o1)
    p2 = write_outline(vault, o2)

    rebuild_index(vault)
    outlines = list_outlines(vault)

    assert len(outlines) == 2
    assert list_caches(vault) == []

    by_title = {e["title"]: e for e in outlines}
    e1 = by_title["open ending one"]
    assert e1["type"] == "outline"
    assert e1["path"].startswith("outlines/")
    assert e1["created"] == "2026-06-20T11:00:00"
    assert e1["updated"] == "2026-06-20T11:30:00"
    assert e1["ending_type"] == "OE"

    e2 = by_title["custom ending two"]
    assert e2["path"] == str(p2.relative_to(vault))
    assert e2["ending_type"] == EndingType.CUSTOM.value
    assert e2["ending_type"] == "custom"


# --------------------------------------------------------------------------- #
# Deterministic ordering for stable diffs
# --------------------------------------------------------------------------- #


def test_rebuild_is_deterministic_sorted_by_filename(tmp_path):
    vault = _fresh_vault(tmp_path)
    write_cache(vault, Cache(title="a", raw="a"))
    write_cache(vault, Cache(title="b", raw="b"))
    write_cache(vault, Cache(title="c", raw="c"))

    rebuild_index(vault)
    paths = [e["path"] for e in list_caches(vault)]
    assert paths == sorted(paths)


# --------------------------------------------------------------------------- #
# Missing index is recreated on load
# --------------------------------------------------------------------------- #


def test_missing_index_is_recreated_on_load(tmp_path):
    vault = _fresh_vault(tmp_path)
    write_cache(vault, Cache(title="only one", raw="spark"))

    index_file = vault / "keikeu_index.json"
    index_file.unlink()
    assert not index_file.exists()

    index = load_index(vault)

    assert index_file.exists()
    assert index["version"] == 1
    assert len(index["caches"]) == 1
    assert index["caches"][0]["title"] == "only one"


# --------------------------------------------------------------------------- #
# Corrupt index is rebuilt without ever touching the Markdown
# --------------------------------------------------------------------------- #


def test_corrupt_index_rebuilds_and_never_deletes_markdown(tmp_path):
    vault = _fresh_vault(tmp_path)
    cache_path = write_cache(vault, Cache(title="precious", raw="do not lose me"))
    original_bytes = cache_path.read_bytes()

    index_file = vault / "keikeu_index.json"
    index_file.write_text("{ broken json", encoding="utf-8")

    index = load_index(vault)

    # The user asset survives untouched: same file, same bytes.
    assert cache_path.exists()
    assert cache_path.read_bytes() == original_bytes

    # The disposable index is now valid again and reflects the Markdown.
    assert index["version"] == 1
    assert json.loads(index_file.read_text(encoding="utf-8")) == index
    assert [e["title"] for e in index["caches"]] == ["precious"]


# --------------------------------------------------------------------------- #
# Wrong-shape (but valid JSON) index is rebuilt; list helpers never crash
# --------------------------------------------------------------------------- #


def test_wrong_shape_index_rebuilds_and_never_crashes_lists(tmp_path):
    # A truncated-but-still-parseable or hand-edited index can be valid JSON of
    # the wrong shape. load_index must treat it as corrupt and rebuild, so
    # list_caches/list_outlines stay total instead of raising TypeError/KeyError.
    vault = _fresh_vault(tmp_path)
    cache_path = write_cache(vault, Cache(title="keep me", raw="spark"))
    original_bytes = cache_path.read_bytes()
    index_file = vault / "keikeu_index.json"

    for payload in ("null", "[1, 2, 3]", "12345", '"a string"',
                    '{"version": 1, "outlines": []}',
                    '{"version": 1, "caches": []}'):
        index_file.write_text(payload, encoding="utf-8")
        # Must not raise, and the user asset must survive untouched.
        assert isinstance(list_caches(vault), list)
        assert isinstance(list_outlines(vault), list)
        assert cache_path.read_bytes() == original_bytes

    # After recovery the index reflects the Markdown again.
    assert [e["title"] for e in list_caches(vault)] == ["keep me"]


# --------------------------------------------------------------------------- #
# list_caches / list_outlines return the right slice
# --------------------------------------------------------------------------- #


def test_list_caches_and_list_outlines_return_their_entries(tmp_path):
    vault = _fresh_vault(tmp_path)
    write_cache(vault, Cache(title="c-one", raw="x"))
    write_outline(vault, Outline(title="o-one"))
    # init_vault already wrote a valid (empty) index, and load_index only
    # rebuilds when the index is missing/corrupt — not when it is merely
    # stale. So sync the index to the freshly-written Markdown explicitly,
    # exactly as a caller would after writing assets.
    rebuild_index(vault)

    caches = list_caches(vault)
    outlines = list_outlines(vault)

    assert [e["type"] for e in caches] == ["cache"]
    assert [e["title"] for e in caches] == ["c-one"]
    assert [e["type"] for e in outlines] == ["outline"]
    assert [e["title"] for e in outlines] == ["o-one"]


# --------------------------------------------------------------------------- #
# Headless import: only stdlib pulled in (no flet / pydantic / yaml)
# --------------------------------------------------------------------------- #


def test_module_imports_only_stdlib():
    # Import indexer in a FRESH interpreter so we inspect *its* import closure,
    # not the global sys.modules of the running test process. PYTHONPATH points
    # at src/ so this works with or without an editable install.
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.indexer, sys\n"
        "forbidden = {'flet', 'pydantic', 'attr', 'attrs', 'yaml'}\n"
        "leaked = sorted(forbidden & set(sys.modules))\n"
        "assert not leaked, 'indexer must not import: ' + repr(leaked)\n"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(src), os.environ.get("PYTHONPATH", "")]
    )}
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
