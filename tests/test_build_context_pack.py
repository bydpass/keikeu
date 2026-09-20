from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_context_pack", ROOT / "scripts" / "build_context_pack.py"
)
assert SPEC is not None and SPEC.loader is not None
CONTEXT_PACK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT_PACK)


def test_tracked_files_excludes_worktree_deletions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "present.txt").write_text("present", encoding="utf-8")
    monkeypatch.setattr(CONTEXT_PACK, "ROOT", tmp_path)
    monkeypatch.setattr(
        CONTEXT_PACK,
        "_git_bytes",
        lambda *args: b"present.txt\0deleted.txt\0",
    )

    assert CONTEXT_PACK._tracked_files() == {
        CONTEXT_PACK.PurePosixPath("present.txt")
    }


def test_context_pack_includes_authority_and_only_selected_status() -> None:
    pack, paths, skipped = CONTEXT_PACK.build_context_pack(
        ["apps/desktop/python/keikeu_core/vault.py"]
    )
    text = pack.decode("utf-8")

    assert skipped == {}
    assert paths == sorted(
        [
            "AGENTS.md",
            "docs/PROJECT.md",
            "docs/RULES.md",
            "docs/SPEC.md",
            "apps/desktop/python/keikeu_core/vault.py",
        ]
    )
    assert "===== BEGIN FILE: apps/desktop/python/keikeu_core/vault.py =====" in text
    assert ".agents/skills/keikeu-routine/SKILL.md" not in text


def test_directory_expansion_skips_cold_context_but_exact_history_is_allowed() -> None:
    _, paths, skipped = CONTEXT_PACK.build_context_pack(["docs"], max_bytes=8_000_000)

    assert skipped["cold-context"] > 0
    assert not any(
        path.startswith(
            ("docs/acceptance/", "docs/archive/", "docs/manual/")
        )
        for path in paths
    )

    _, exact_paths, _ = CONTEXT_PACK.build_context_pack(
        ["docs/archive/snapshots/road-v0-7.html"]
    )
    assert "docs/archive/snapshots/road-v0-7.html" in exact_paths


def test_context_pack_rejects_binary_escape_and_oversize_requests() -> None:
    with pytest.raises(CONTEXT_PACK.ContextPackError, match="not UTF-8 text"):
        CONTEXT_PACK.build_context_pack(
            ["docs/acceptance/road-v0-5/cp2-departure-1220x780.png"]
        )
    with pytest.raises(CONTEXT_PACK.ContextPackError, match="escapes the repository"):
        CONTEXT_PACK.build_context_pack(["../outside.txt"])
    with pytest.raises(CONTEXT_PACK.ContextPackError, match="above the 100-byte limit"):
        CONTEXT_PACK.build_context_pack([], max_bytes=100)


def test_context_pack_writes_repository_root_context_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "CONTEXT.md"
    monkeypatch.setattr(CONTEXT_PACK, "ROOT", tmp_path)
    monkeypatch.setattr(CONTEXT_PACK, "OUTPUT", output)

    CONTEXT_PACK._write_atomic(b"route")

    assert output.read_bytes() == b"route"
    assert not (tmp_path / "build").exists()


def test_context_pack_rejects_output_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"unchanged")
    output_link = tmp_path / "CONTEXT.md"
    output_link.symlink_to(outside)
    monkeypatch.setattr(CONTEXT_PACK, "ROOT", tmp_path)
    monkeypatch.setattr(CONTEXT_PACK, "OUTPUT", output_link)

    with pytest.raises(CONTEXT_PACK.ContextPackError, match="not a symlink"):
        CONTEXT_PACK._write_atomic(b"safe")
    assert outside.read_bytes() == b"unchanged"
