"""Candidate startup selects its own state without changing the accepted desktop default."""
from pathlib import Path

import pytest

from keikeu_bridge import sidecar
from keikeu_core import vault


def test_explicit_candidate_state_and_unchanged_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vault, "_current_home", lambda: tmp_path)
    captured = []
    monkeypatch.setattr(sidecar, "KeikeuService", lambda **kwargs: captured.append(kwargs))
    monkeypatch.setattr(sidecar, "run_jsonl", lambda *args: 0)
    assert sidecar.main([]) == 0
    assert captured.pop() == {"config_path": sidecar.CONFIG_PATH, "state_path": sidecar.STATE_PATH}
    candidate = tmp_path / "candidate"
    assert sidecar.main(["--state-directory", str(candidate)]) == 0
    assert captured.pop() == {
        "config_path": candidate / "desktop-config.json",
        "state_path": candidate / "desktop-state.json",
    }
    with pytest.raises(ValueError, match="outside current user Home"):
        sidecar.main(["--state-directory", str(tmp_path.parent / "outside")])
    assert not captured
