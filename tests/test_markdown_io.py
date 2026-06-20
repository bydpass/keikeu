"""Tests for keikeu_core.markdown_io — Markdown round-trip serialization.

These tests pin the Step 4 contract: cache/outline files round-trip every field
exactly, the verbatim invariant (product invariant 1) survives content that
looks structural (``## ...`` and ``---`` lines, CJK, emoji), blank optional
fields stay blank, filenames are collision-free and filesystem-safe, CJK slugs
are preserved, and the module pulls in no third-party dependency.

A vault is set up with ``vault.init_vault(tmp_path)`` so writes land in a real
``cache/`` / ``outlines/`` layout.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from keikeu_core import vault
from keikeu_core.markdown_io import (
    read_cache,
    read_outline,
    update_cache,
    update_outline,
    write_cache,
    write_outline,
)
from keikeu_core.markdown_io import _slugify  # internal: filename rule under test
from keikeu_core.models import (
    Cache,
    CacheStatus,
    EndingType,
    Outline,
    Relation,
    RelationType,
)


# --------------------------------------------------------------------------- #
# Cache round-trip: verbatim raw with structural-looking content
# --------------------------------------------------------------------------- #


def test_cache_round_trip_preserves_all_fields(tmp_path):
    vault.init_vault(tmp_path)
    raw = (
        "first line 火\n"
        "## not a header\n"
        "---\n"
        "\n"
        "深夜的电车，两个陌生人 🚃\n"
        "  trailing spaces kept  "
    )
    created = datetime(2026, 6, 20, 14, 30, 45)
    updated = datetime(2026, 6, 21, 9, 0, 0)
    cache = Cache(
        title="灵感 one",
        raw=raw,
        notes="just a note\nsecond line",
        status=CacheStatus.DRAFTING,
        created=created,
        updated=updated,
        linked_outline="outlines/some-outline.md",
    )
    path = write_cache(tmp_path, cache)
    assert path.parent == tmp_path / "cache"

    back = read_cache(path)
    assert back.raw == raw  # SACRED: verbatim, untouched
    assert back.title == "灵感 one"
    assert back.notes == "just a note\nsecond line"
    assert back.status is CacheStatus.DRAFTING
    assert back.linked_outline == "outlines/some-outline.md"
    assert back.created == created
    assert back.updated == updated


# --------------------------------------------------------------------------- #
# Outline round-trip: prose, lists, enums via frontmatter
# --------------------------------------------------------------------------- #


def test_outline_round_trip_preserves_all_fields(tmp_path):
    vault.init_vault(tmp_path)
    raw_inspiration = (
        "a spark\n"
        "## looks like a header but is not\n"
        "---\n"
        "末尾 🌙"
    )
    created = datetime(2026, 1, 2, 3, 4, 5)
    updated = datetime(2026, 1, 3, 4, 5, 6)
    outline = Outline(
        title="My/Outline",
        raw_inspiration=raw_inspiration,
        summary="a tidy summary\nspanning lines",
        fandom="Some Fandom",
        characters=["Alice", "Bob", "查理"],
        cp="Alice/Bob",
        content_warnings="dark themes",
        plot="they meet, they part, they write",
        ending_type=EndingType.CUSTOM,
        custom_ending="they part ways but write letters",
        relations=[
            Relation(
                relation_type=RelationType.SEQUEL,
                target_path="outlines/next.md",
                note="continues here",
            ),
            Relation(
                relation_type=RelationType.IF,
                target_path="outlines/what-if.md",
                note="",
            ),
        ],
        created=created,
        updated=updated,
    )
    path = write_outline(tmp_path, outline)
    assert path.parent == tmp_path / "outlines"

    back = read_outline(path)
    assert back.raw_inspiration == raw_inspiration  # SACRED: verbatim
    assert back.title == "My/Outline"
    assert back.summary == "a tidy summary\nspanning lines"
    assert back.fandom == "Some Fandom"
    assert back.characters == ["Alice", "Bob", "查理"]
    assert back.cp == "Alice/Bob"
    assert back.content_warnings == "dark themes"
    assert back.plot == "they meet, they part, they write"
    assert back.ending_type is EndingType.CUSTOM
    assert back.custom_ending == "they part ways but write letters"
    assert back.created == created
    assert back.updated == updated
    assert len(back.relations) == 2
    assert back.relations[0].relation_type is RelationType.SEQUEL
    assert back.relations[0].target_path == "outlines/next.md"
    assert back.relations[0].note == "continues here"
    assert back.relations[1].relation_type is RelationType.IF
    assert back.relations[1].target_path == "outlines/what-if.md"
    assert back.relations[1].note == ""


# --------------------------------------------------------------------------- #
# Blank optional fields survive
# --------------------------------------------------------------------------- #


def test_blank_cache_fields_round_trip(tmp_path):
    vault.init_vault(tmp_path)
    cache = Cache(title="t", raw="")
    back = read_cache(write_cache(tmp_path, cache))
    assert back.title == "t"
    assert back.raw == ""
    assert back.notes == ""
    assert back.status is CacheStatus.RAW
    assert back.linked_outline is None


def test_blank_outline_fields_round_trip(tmp_path):
    vault.init_vault(tmp_path)
    outline = Outline(title="t")
    back = read_outline(write_outline(tmp_path, outline))
    assert back.title == "t"
    assert back.raw_inspiration == ""
    assert back.summary == ""
    assert back.fandom == ""
    assert back.characters == []
    assert back.cp == ""
    assert back.content_warnings == ""
    assert back.plot == ""
    assert back.ending_type is EndingType.OE
    assert back.custom_ending == ""
    assert back.relations == []


# --------------------------------------------------------------------------- #
# Filename collision avoided for same second + same title
# --------------------------------------------------------------------------- #


def test_filename_collision_avoided(tmp_path):
    vault.init_vault(tmp_path)
    created = datetime(2026, 6, 20, 14, 30, 45)
    a = write_cache(tmp_path, Cache(title="same", raw="a", created=created))
    b = write_cache(tmp_path, Cache(title="same", raw="b", created=created))
    assert a != b
    assert a.exists() and b.exists()


# --------------------------------------------------------------------------- #
# Dangerous filename chars removed; CJK preserved
# --------------------------------------------------------------------------- #


def test_dangerous_filename_chars_removed(tmp_path):
    vault.init_vault(tmp_path)
    path = write_cache(tmp_path, Cache(title='a/b:c*?"<>|d', raw="r"))
    name = path.name
    for bad in '/\\:*?"<>|':
        assert bad not in name


def test_only_dangerous_chars_falls_back_to_untitled():
    assert _slugify('/\\:*?"<>|') == "untitled"
    assert _slugify("   ") == "untitled"
    assert _slugify("...") == "untitled"


def test_cjk_slug_preserved(tmp_path):
    vault.init_vault(tmp_path)
    path = write_cache(tmp_path, Cache(title="深夜的电车", raw="r"))
    assert "深夜的电车" in path.name


def test_slug_collapses_whitespace():
    assert _slugify("a   b\tc") == "a-b-c"


# --------------------------------------------------------------------------- #
# Frontmatter newline injection: must never crash or truncate (regression)
# --------------------------------------------------------------------------- #


def test_outline_custom_ending_multiline_round_trips(tmp_path):
    # custom_ending is free text and now lives in body section 6, so a newline
    # or a bare '---' line must round-trip verbatim and never be mistaken for a
    # frontmatter fence. Previously this crashed read_outline with KeyError.
    vault.init_vault(tmp_path)
    custom = "they part\n---\nbut write letters\n## still part of the ending"
    outline = Outline(
        title="t",
        ending_type=EndingType.CUSTOM,
        custom_ending=custom,
    )
    back = read_outline(write_outline(tmp_path, outline))
    assert back.ending_type is EndingType.CUSTOM
    assert back.custom_ending == custom


def test_cache_linked_outline_with_newline_round_trips(tmp_path):
    # linked_outline is a frontmatter scalar; an embedded newline must be
    # escaped, not silently truncated nor allowed to split the fenced block.
    vault.init_vault(tmp_path)
    cache = Cache(title="t", raw="r", linked_outline="a\nb")
    back = read_cache(write_cache(tmp_path, cache))
    assert back.linked_outline == "a\nb"


# --------------------------------------------------------------------------- #
# In-place update: edit/save against the SAME path, no new filename
# --------------------------------------------------------------------------- #


def test_update_cache_overwrites_same_path(tmp_path):
    vault.init_vault(tmp_path)
    raw = "深夜的电车 🚃\n## not a header\n---\nverbatim spark"
    created = datetime(2026, 6, 20, 14, 30, 45)
    cache = Cache(
        title="t",
        raw=raw,
        notes="first note",
        status=CacheStatus.RAW,
        created=created,
    )
    path = write_cache(tmp_path, cache)

    # Edit a couple of fields, then update in place.
    cache.status = CacheStatus.ARCHIVED
    cache.notes = "edited note\nsecond line"
    update_cache(path, cache)

    # No new file: still exactly one file in cache/, and it is the same path.
    cache_dir = tmp_path / "cache"
    files = list(cache_dir.glob("*.md"))
    assert files == [path]

    back = read_cache(path)
    assert back.status is CacheStatus.ARCHIVED  # changed field reflected
    assert back.notes == "edited note\nsecond line"
    assert back.raw == raw  # SACRED: verbatim, untouched


def test_update_outline_overwrites_same_path(tmp_path):
    vault.init_vault(tmp_path)
    raw_inspiration = "a spark\n## looks like a header\n---\n末尾 🌙"
    created = datetime(2026, 1, 2, 3, 4, 5)
    outline = Outline(
        title="t",
        raw_inspiration=raw_inspiration,
        summary="first summary",
        ending_type=EndingType.OE,
        created=created,
    )
    path = write_outline(tmp_path, outline)

    # Edit summary + ending_type, then update in place.
    outline.summary = "edited summary\nspanning lines"
    outline.ending_type = EndingType.BE
    update_outline(path, outline)

    outlines_dir = tmp_path / "outlines"
    files = list(outlines_dir.glob("*.md"))
    assert files == [path]

    back = read_outline(path)
    assert back.summary == "edited summary\nspanning lines"
    assert back.ending_type is EndingType.BE
    assert back.raw_inspiration == raw_inspiration  # SACRED: verbatim


# --------------------------------------------------------------------------- #
# Render is stable: write_* then update_* (no edit) yields byte-identical bytes
# --------------------------------------------------------------------------- #


def test_render_is_stable_for_write_then_update(tmp_path):
    vault.init_vault(tmp_path)

    cache = Cache(title="t", raw="r\n---\nx", notes="n")
    cache_path = write_cache(tmp_path, cache)
    before = cache_path.read_bytes()
    update_cache(cache_path, cache)
    assert cache_path.read_bytes() == before

    outline = Outline(
        title="t",
        raw_inspiration="spark\n## x",
        ending_type=EndingType.CUSTOM,
        custom_ending="they part\n---\nthen write",
    )
    outline_path = write_outline(tmp_path, outline)
    before = outline_path.read_bytes()
    update_outline(outline_path, outline)
    assert outline_path.read_bytes() == before


# --------------------------------------------------------------------------- #
# No third-party deps pulled in (fresh interpreter, like test_models.py)
# --------------------------------------------------------------------------- #


def test_module_imports_only_stdlib():
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.markdown_io, sys\n"
        "forbidden = {'yaml', 'flet', 'pydantic'}\n"
        "leaked = sorted(forbidden & set(sys.modules))\n"
        "assert not leaked, 'markdown_io must not import: ' + repr(leaked)\n"
    )
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [str(src), os.environ.get("PYTHONPATH", "")]
        ),
    }
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
