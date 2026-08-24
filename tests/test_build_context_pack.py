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


def test_context_pack_includes_authority_and_only_selected_status() -> None:
    pack, paths, skipped = CONTEXT_PACK.build_context_pack(
        ["src/keikeu_core/vault.py"]
    )
    text = pack.decode("utf-8")

    assert skipped == {}
    assert paths == sorted(
        [
            "AGENTS.md",
            "docs/PROJECT.md",
            "docs/RULES.md",
            "docs/SPEC.md",
            "src/keikeu_core/vault.py",
        ]
    )
    assert "===== BEGIN FILE: src/keikeu_core/vault.py =====" in text
    assert ".agents/skills/keikeu-routine/SKILL.md" not in text


def test_directory_expansion_skips_cold_context_but_exact_history_is_allowed() -> None:
    _, paths, skipped = CONTEXT_PACK.build_context_pack(["docs"], max_bytes=8_000_000)

    assert skipped["cold-context"] > 0
    assert not any(
        path.startswith(
            ("docs/acceptance/", "docs/archive/", "docs/generated/", "docs/manual/")
        )
        for path in paths
    )

    _, exact_paths, _ = CONTEXT_PACK.build_context_pack(
        ["docs/archive/road-v0-3/cold_start_report.md"]
    )
    assert "docs/archive/road-v0-3/cold_start_report.md" in exact_paths


def test_context_pack_rejects_binary_escape_and_oversize_requests() -> None:
    with pytest.raises(CONTEXT_PACK.ContextPackError, match="not UTF-8 text"):
        CONTEXT_PACK.build_context_pack(
            ["docs/acceptance/road-v0-5/cp2-departure-1220x780.png"]
        )
    with pytest.raises(CONTEXT_PACK.ContextPackError, match="escapes the repository"):
        CONTEXT_PACK.build_context_pack(["../outside.txt"])
    with pytest.raises(CONTEXT_PACK.ContextPackError, match="above the 100-byte limit"):
        CONTEXT_PACK.build_context_pack([], max_bytes=100)


def test_context_pack_rejects_output_symlink_before_creating_outside_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    build_link = tmp_path / "build"
    build_link.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(CONTEXT_PACK, "ROOT", tmp_path)
    monkeypatch.setattr(
        CONTEXT_PACK, "OUTPUT", build_link / "context" / "keikeu-context.txt"
    )

    with pytest.raises(CONTEXT_PACK.ContextPackError, match="must not traverse a symlink"):
        CONTEXT_PACK._write_atomic(b"safe")
    assert not (outside / "context").exists()
