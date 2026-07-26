"""Frozen synthetic inputs for Road v0.3 boundary tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v03-vault"

EXPECTED_MANIFEST = {
    "fixture_schema": 1,
    "frozen_for": "Road v0.3",
    "synthetic_only": True,
    "vaults": {
        "mixed-vault": {
            "index_contract": "deliberately-stale-v2",
            "papers": [
                {
                    "path": "cache/K-20260720-001.md",
                    "schema_version": 2,
                    "expected": "active-root",
                },
                {
                    "path": "cache/K-20260720-002.md",
                    "schema_version": 3,
                    "expected": "active-root",
                },
                {
                    "path": "cache/夜行列车/K-20260720-003.md",
                    "schema_version": 3,
                    "expected": "active-folder",
                },
                {
                    "path": "cache/夜行列车/深层/K-20260720-004.md",
                    "schema_version": 3,
                    "expected": "path-error",
                },
                {
                    "path": ".trash/cache/K-20260719-005.md",
                    "schema_version": 2,
                    "expected": "trash-root",
                },
                {
                    "path": ".trash/cache/旧车站/K-20260719-006.md",
                    "schema_version": 3,
                    "expected": "trash-folder",
                },
            ],
            "runtime_symlinks": [
                {
                    "path": "cache/链接目录",
                    "target": "cache/夜行列车",
                    "kind": "internal-directory",
                    "expected": "path-error",
                },
                {
                    "path": "cache/K-20260720-099.md",
                    "target": "outside-vault-target.md",
                    "kind": "vault-escape-file",
                    "expected": "path-error",
                },
            ],
        },
        "unsafe-vault": {
            "placement_contract": "outside-simulated-home-only",
            "source_retained": True,
            "papers": [
                {
                    "path": "cache/K-20260718-001.md",
                    "schema_version": 2,
                    "expected": "relocation-source",
                }
            ],
        },
    },
}

EXPECTED_FILES = {
    "README.md",
    "manifest.json",
    "mixed-vault/.trash/cache/K-20260719-005.md",
    "mixed-vault/.trash/cache/旧车站/K-20260719-006.md",
    "mixed-vault/cache/K-20260720-001.md",
    "mixed-vault/cache/K-20260720-002.md",
    "mixed-vault/cache/夜行列车/K-20260720-003.md",
    "mixed-vault/cache/夜行列车/深层/K-20260720-004.md",
    "mixed-vault/keikeu_index.json",
    "unsafe-vault/cache/K-20260718-001.md",
    "unsafe-vault/keikeu_index.json",
}

EXPECTED_DIRECTORIES = {
    "mixed-vault",
    "mixed-vault/.trash",
    "mixed-vault/.trash/cache",
    "mixed-vault/.trash/cache/旧车站",
    "mixed-vault/cache",
    "mixed-vault/cache/夜行列车",
    "mixed-vault/cache/夜行列车/深层",
    "unsafe-vault",
    "unsafe-vault/cache",
}


def test_fixture_tree_manifest_and_paper_headers_are_frozen():
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == EXPECTED_MANIFEST

    entries = list(FIXTURE_ROOT.rglob("*"))
    assert {str(path.relative_to(FIXTURE_ROOT)) for path in entries if path.is_file()} == (
        EXPECTED_FILES
    )
    assert {str(path.relative_to(FIXTURE_ROOT)) for path in entries if path.is_dir()} == (
        EXPECTED_DIRECTORIES
    )
    assert not any(path.is_symlink() for path in entries)

    for vault_name, contract in manifest["vaults"].items():
        vault = FIXTURE_ROOT / vault_name
        assert (vault / "cache").is_dir()
        assert json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8")) == {
            "version": 2,
            "papers": [],
            "errors": [],
        }
        for paper in contract["papers"]:
            path = vault / paper["path"]
            text = path.read_text(encoding="utf-8")
            assert path.name == f"{text.split('code: ', 1)[1].splitlines()[0]}.md"
            assert "type: paper\n" in text
            assert f"schema_version: {paper['schema_version']}\n" in text
            assert "fixture: synthetic-road-v03\n" in text
            assert all(
                heading in text
                for heading in ("## 初稿副本", "## Summary", "## Highlights", "## Tags")
            )


def test_symlink_recipes_are_created_only_in_an_ignored_runtime_copy(tmp_path):
    manifest = EXPECTED_MANIFEST["vaults"]["mixed-vault"]
    vault = tmp_path / "mixed-vault"
    shutil.copytree(FIXTURE_ROOT / "mixed-vault", vault)
    outside_target = tmp_path / "outside-vault-target.md"
    outside_target.write_text("synthetic symlink target\n", encoding="utf-8")

    for recipe in manifest["runtime_symlinks"]:
        link = vault / recipe["path"]
        if recipe["kind"] == "internal-directory":
            target = vault / recipe["target"]
            link.symlink_to(target, target_is_directory=True)
        else:
            target = outside_target
            link.symlink_to(target)
        assert link.is_symlink()

    internal_link, escape_link = (
        vault / recipe["path"] for recipe in manifest["runtime_symlinks"]
    )
    assert internal_link.resolve().is_relative_to(vault.resolve())
    assert not escape_link.resolve().is_relative_to(vault.resolve())


def test_unsafe_fixture_uses_a_simulated_home_and_retains_its_source(tmp_path):
    simulated_home = tmp_path / "simulated-home"
    simulated_home.mkdir()
    source = FIXTURE_ROOT / "unsafe-vault"
    source_bytes = (source / "cache" / "K-20260718-001.md").read_bytes()
    candidate = tmp_path / "outside-simulated-home" / "unsafe-vault"
    shutil.copytree(source, candidate)

    assert not candidate.resolve().is_relative_to(simulated_home.resolve())
    assert (candidate / "cache" / "K-20260718-001.md").read_bytes() == source_bytes
    assert (source / "cache" / "K-20260718-001.md").read_bytes() == source_bytes
