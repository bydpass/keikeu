from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_docs", ROOT / "scripts/check_docs.py")
assert SPEC is not None and SPEC.loader is not None
CHECK_DOCS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK_DOCS)


def test_missing_roots_are_reported_without_stopping_link_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    required = tmp_path / "README.md"
    active = tmp_path / "PLAN_road_v0_8.md"
    present = tmp_path / "guide.md"
    present.write_text("[self](guide.md) [missing](absent.md)\n", encoding="utf-8")
    monkeypatch.setattr(CHECK_DOCS, "ROOT", tmp_path)
    monkeypatch.setattr(CHECK_DOCS, "ARCHIVE", tmp_path / "archive")
    monkeypatch.setattr(CHECK_DOCS, "REQUIRED", {required})
    monkeypatch.setattr(CHECK_DOCS, "BUDGETS", {required: 140})
    monkeypatch.setattr(CHECK_DOCS, "active_documents", lambda: [required, active, present])

    assert CHECK_DOCS.main() == 1
    output = capsys.readouterr().out
    assert output.count("missing required file: README.md") == 1
    assert "missing active file: PLAN_road_v0_8.md" in output
    assert "guide.md: broken link absent.md" in output
