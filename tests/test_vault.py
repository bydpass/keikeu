"""Tests for keikeu_core.vault — local vault layout + config resolution.

These tests pin the Step 3 contract: idempotent, non-destructive vault
init; the exact empty-index shape; vault detection; and config round-trip
with safe failure modes. All filesystem work happens under pytest's
``tmp_path`` fixture; no real home directory is ever touched.

The headless-import test reuses the fresh-subprocess probe pattern from
tests/test_models.py so the running process's polluted sys.modules cannot
mask a forbidden import.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from keikeu_core.vault import get_vault, init_vault, is_vault, set_vault, soft_delete


# --------------------------------------------------------------------------- #
# init_vault: directory layout
# --------------------------------------------------------------------------- #


def test_init_vault_creates_cache_and_outlines_dirs(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    assert (vault / "cache").is_dir()
    assert (vault / "outlines").is_dir()
    assert (vault / ".trash" / "cache").is_dir()
    assert (vault / ".trash" / "outlines").is_dir()


# --------------------------------------------------------------------------- #
# init_vault: exact empty-index shape
# --------------------------------------------------------------------------- #


def test_init_vault_writes_exact_empty_index(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    index = vault / "keikeu_index.json"
    assert index.is_file()
    with index.open(encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded == {"version": 1, "caches": [], "outlines": []}


# --------------------------------------------------------------------------- #
# init_vault: idempotent and non-destructive (the critical invariant)
# --------------------------------------------------------------------------- #


def test_init_vault_is_idempotent(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    init_vault(vault)  # must not raise
    assert is_vault(vault)


def test_init_vault_does_not_clobber_seeded_index(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    index = vault / "keikeu_index.json"
    # Pre-seed the index with user data, as if caches had been written.
    seeded = {
        "version": 1,
        "caches": [{"title": "spark", "path": "cache/spark.md"}],
        "outlines": [],
    }
    with index.open("w", encoding="utf-8") as fh:
        json.dump(seeded, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    # Re-init must preserve the seeded data: index is rebuildable, but
    # init must never clobber it (product invariant 2).
    init_vault(vault)
    with index.open(encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded == seeded


# --------------------------------------------------------------------------- #
# is_vault
# --------------------------------------------------------------------------- #


def test_is_vault_true_for_initialized_vault(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    assert is_vault(vault) is True


def test_is_vault_does_not_require_trash_dirs_for_older_vaults(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    (vault / ".trash" / "cache").rmdir()
    (vault / ".trash" / "outlines").rmdir()
    (vault / ".trash").rmdir()
    assert is_vault(vault) is True


def test_is_vault_false_for_empty_dir(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert is_vault(empty) is False


def test_is_vault_false_for_nonexistent_path(tmp_path):
    missing = tmp_path / "does_not_exist"
    assert is_vault(missing) is False  # must not raise


# --------------------------------------------------------------------------- #
# set_vault / get_vault round-trip
# --------------------------------------------------------------------------- #


def test_set_then_get_vault_round_trips(tmp_path):
    vault = tmp_path / "vault"
    config = tmp_path / "config" / "keikeu_config.json"
    set_vault(vault, config)
    assert config.is_file()  # parent dirs created
    assert get_vault(config) == vault


# --------------------------------------------------------------------------- #
# get_vault: safe failure modes (never raises)
# --------------------------------------------------------------------------- #


def test_get_vault_returns_none_for_missing_config(tmp_path):
    missing = tmp_path / "no_such_config.json"
    assert get_vault(missing) is None


def test_get_vault_returns_none_for_corrupt_config(tmp_path):
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("this is not json {{{", encoding="utf-8")
    assert get_vault(corrupt) is None


def test_get_vault_returns_none_for_nonstring_vault_value(tmp_path):
    # Valid JSON object, but "vault" is not a string (hand-edited / corrupt).
    # Must return None, not raise TypeError from Path(123).
    for payload in ('{"vault": 123}', '{"vault": null}', '{"vault": [1, 2]}'):
        config = tmp_path / "weird.json"
        config.write_text(payload, encoding="utf-8")
        assert get_vault(config) is None


# --------------------------------------------------------------------------- #
# soft_delete
# --------------------------------------------------------------------------- #


def test_soft_delete_moves_cache_into_matching_trash_dir_preserving_bytes(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    source = vault / "cache" / "spark.md"
    source_bytes = b"# Spark\n\nraw bytes stay exact\n"
    source.write_bytes(source_bytes)

    moved = soft_delete(vault, "cache/spark.md")

    assert not source.exists()
    assert moved == vault / ".trash" / "cache" / "spark.md"
    assert moved.read_bytes() == source_bytes


def test_soft_delete_suffixes_duplicate_trash_names_without_overwriting(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    source = vault / "outlines" / "same.md"
    source.write_text("new outline", encoding="utf-8")
    existing = vault / ".trash" / "outlines" / "same.md"
    existing.write_text("old outline", encoding="utf-8")

    moved = soft_delete(vault, "outlines/same.md")

    assert moved.parent == vault / ".trash" / "outlines"
    assert moved.name.startswith("same-")
    assert moved.suffix == ".md"
    assert moved.read_text(encoding="utf-8") == "new outline"
    assert existing.read_text(encoding="utf-8") == "old outline"


def test_soft_delete_rejects_paths_outside_cache_and_outlines(tmp_path):
    vault = tmp_path / "vault"
    init_vault(vault)
    for rel_path in ("cache/nested/spark.md", "notes/spark.md", "../cache/spark.md"):
        try:
            soft_delete(vault, rel_path)
        except ValueError as ex:
            assert "cache/*.md or outlines/*.md" in str(ex)
        else:
            raise AssertionError(f"soft_delete accepted invalid path: {rel_path}")


# --------------------------------------------------------------------------- #
# Headless import: only stdlib pulled in (no flet / pydantic / yaml)
# --------------------------------------------------------------------------- #


def test_module_imports_only_stdlib():
    # Import vault in a FRESH interpreter so we inspect *its* import closure,
    # not the global sys.modules of the running test process (which a sibling
    # test or conftest could already have polluted with flet). PYTHONPATH
    # points at src/ so this works with or without an editable install.
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        "import keikeu_core.vault, sys\n"
        "forbidden = {'flet', 'pydantic', 'attr', 'attrs', 'yaml'}\n"
        "leaked = sorted(forbidden & set(sys.modules))\n"
        "assert not leaked, 'vault must not import: ' + repr(leaked)\n"
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
