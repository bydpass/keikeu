"""The checked-in corpus is shared with Rust; changes require reviewing both implementations."""

import json
from pathlib import Path

from keikeu_core.markdown_io import parse_paper_v4_bytes, render_paper_v4_bytes


def test_shared_paper_golden():
    corpus = json.loads((Path(__file__).parent / "fixtures/paper-v4-golden.json").read_text())
    for case in corpus["cases"]:
        try:
            paper = parse_paper_v4_bytes(bytes.fromhex(case["hex"]))
        except (ValueError, UnicodeError):
            assert case.get("error") == "repair_required", case["name"]
        else:
            assert "error" not in case, case["name"]
            assert render_paper_v4_bytes(paper).decode() == case["canonical"], case["name"]
