"""Additive Index v4, Trash projection, and v4 Branch contracts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from keikeu_core.indexer import (
    build_index_v4,
    query_index_v4,
    query_trash_v4,
    rebuild_index_v4,
    verify_index_v4,
)
from keikeu_core.markdown_io import (
    branch_paper_v4,
    parse_paper_v4_bytes,
    render_paper_v4_bytes,
)
from keikeu_core.models import CardPageV4, PaperV4
from keikeu_core.vault import init_vault


NOW = datetime(2026, 8, 2, 11, 0)


def make_paper(code: str, **overrides) -> PaperV4:
    values = {
        "code": code,
        "display_name": None,
        "pages": [CardPageV4(content="第一页")],
        "created": NOW,
        "updated": NOW,
    }
    values.update(overrides)
    return PaperV4(**values)


def fresh_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    init_vault(vault)
    return vault


def store(vault: Path, relative: str, paper: PaperV4) -> Path:
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_paper_v4_bytes(paper))
    return path


def test_index_v4_has_full_page_projection_and_active_only_persistence(tmp_path):
    vault = fresh_vault(tmp_path)
    path = store(
        vault,
        "cache/夜车/K-20260802-001.md",
        make_paper(
            "K-20260802-001",
            display_name="夜车",
            pages=[
                CardPageV4(name="开场", content="第一段原文", type="summary"),
                CardPageV4(name=None, content="第二段", type="snapshot"),
            ],
            tags=["重逢,旧友"],
        ),
    )
    store(
        vault,
        ".trash/cache/K-20260802-002.md",
        make_paper("K-20260802-002", pages=[CardPageV4(content="Trash only")]),
    )

    index = rebuild_index_v4(vault)

    assert index["version"] == 4
    assert len(index["papers"]) == 1
    entry = index["papers"][0]
    assert entry["path"] == str(path.relative_to(vault))
    assert entry["folder"] == "夜车"
    assert entry["preview"] == "第一段原文"
    assert entry["page_count"] == 2
    assert entry["page_names"] == ["开场"]
    assert "第二段" in entry["search_text"]
    assert "高光" in entry["search_text"]
    stored = json.loads((vault / "keikeu_index.json").read_text(encoding="utf-8"))
    assert stored == index
    assert all(not str(item["path"]).startswith(".trash/") for item in stored["papers"])


def test_index_v4_query_normalizes_nfc_casefold_and_never_returns_search_text(tmp_path):
    vault = fresh_vault(tmp_path)
    store(
        vault,
        "cache/K-20260802-001.md",
        make_paper(
            "K-20260802-001",
            pages=[CardPageV4(name="Cafe\u0301", content="安静", type="whisper")],
        ),
    )

    by_name = query_index_v4(vault, "CAFÉ")
    by_type = query_index_v4(vault, "碎碎念")

    assert len(by_name["papers"]) == len(by_type["papers"]) == 1
    assert "search_text" not in by_name["papers"][0]


def test_index_v4_verify_is_read_only_for_missing_invalid_and_stale_index(tmp_path):
    vault = fresh_vault(tmp_path)
    path = store(
        vault,
        "cache/K-20260802-001.md",
        make_paper("K-20260802-001"),
    )
    (vault / "keikeu_index.json").unlink()
    assert verify_index_v4(vault) is False
    assert not (vault / "keikeu_index.json").exists()

    rebuild_index_v4(vault)
    assert verify_index_v4(vault) is True
    stale_bytes = (vault / "keikeu_index.json").read_bytes()
    path.write_bytes(
        render_paper_v4_bytes(
            make_paper("K-20260802-001", pages=[CardPageV4(content="changed")])
        )
    )
    assert verify_index_v4(vault) is False
    assert (vault / "keikeu_index.json").read_bytes() == stale_bytes


def test_index_v4_isolates_broken_active_paper_without_rewriting_it(tmp_path):
    vault = fresh_vault(tmp_path)
    valid = store(
        vault,
        "cache/K-20260802-001.md",
        make_paper("K-20260802-001"),
    )
    broken = vault / "cache" / "K-20260802-002.md"
    broken_bytes = b"not a Paper"
    broken.write_bytes(broken_bytes)

    index = build_index_v4(vault)

    assert [item["path"] for item in index["papers"]] == [str(valid.relative_to(vault))]
    assert index["errors"][0]["path"] == "cache/K-20260802-002.md"
    assert broken.read_bytes() == broken_bytes


def test_trash_v4_query_is_ephemeral_and_broken_fallback_uses_only_path(tmp_path):
    vault = fresh_vault(tmp_path)
    store(
        vault,
        ".trash/cache/旧页/K-20260802-001.md",
        make_paper(
            "K-20260802-001",
            pages=[CardPageV4(name="回声", content="只在 Trash", type="snapshot")],
        ),
    )
    broken = vault / ".trash" / "cache" / "broken.md"
    broken.write_bytes(b"broken")
    before_index = (vault / "keikeu_index.json").read_bytes()

    good = query_trash_v4(vault, "只在 trash")
    fallback = query_trash_v4(vault, "broken")

    assert len(good["papers"]) == 1
    assert good["papers"][0]["folder"] == "旧页"
    assert "search_text" not in good["papers"][0]
    assert fallback["papers"][0]["path"] == ".trash/cache/broken.md"
    assert fallback["papers"][0]["preview"] == ""
    assert (vault / "keikeu_index.json").read_bytes() == before_index

    nested_broken = vault / ".trash" / "cache" / "旧页" / "nested-broken.md"
    nested_broken.write_bytes(b"broken")
    nested = query_trash_v4(vault, "nested-broken")
    assert nested["papers"][0]["folder"] == "旧页"


def test_branch_paper_v4_copies_author_fields_and_resets_identity_time(tmp_path):
    vault = fresh_vault(tmp_path)
    source_paper = make_paper(
        "K-20260802-001",
        display_name="名" * 200,
        pages=[
            CardPageV4(name="一", content="正文", type="summary"),
            CardPageV4(name="二", content="另一页", type="whisper"),
        ],
        tags=["a", "b"],
        legacy_title="旧名",
        extra_frontmatter={"source": "manual"},
    )
    source = store(vault, "cache/文件夹/K-20260802-001.md", source_paper)
    source_bytes = source.read_bytes()
    branch_time = datetime(2026, 8, 3, 9, 0)

    destination = branch_paper_v4(
        vault,
        "cache/文件夹/K-20260802-001.md",
        "cache/文件夹/K-20260803-001.md",
        "K-20260803-001",
        expected_source_bytes=source_bytes,
        now=branch_time,
    )
    branched = parse_paper_v4_bytes(destination.read_bytes())

    assert source.read_bytes() == source_bytes
    assert branched.code == "K-20260803-001"
    assert branched.display_name == "名" * 195 + " · 分支"
    assert branched.pages == source_paper.pages
    assert branched.tags == source_paper.tags
    assert branched.legacy_title == source_paper.legacy_title
    assert branched.extra_frontmatter == source_paper.extra_frontmatter
    assert branched.created == branched.updated == branch_time


def test_branch_paper_v4_rejects_stale_source_and_global_code_conflict(tmp_path):
    vault = fresh_vault(tmp_path)
    source = store(
        vault,
        "cache/K-20260802-001.md",
        make_paper("K-20260802-001"),
    )
    expected = source.read_bytes()
    source.write_bytes(
        render_paper_v4_bytes(
            make_paper("K-20260802-001", pages=[CardPageV4(content="external")])
        )
    )
    with pytest.raises(ValueError, match="changed before"):
        branch_paper_v4(
            vault,
            source.relative_to(vault),
            "cache/K-20260803-001.md",
            "K-20260803-001",
            expected_source_bytes=expected,
            now=NOW,
        )
    assert not (vault / "cache" / "K-20260803-001.md").exists()

    current = source.read_bytes()
    store(
        vault,
        ".trash/cache/K-20260803-001.md",
        make_paper("K-20260803-001"),
    )
    with pytest.raises(FileExistsError, match="active/Trash"):
        branch_paper_v4(
            vault,
            source.relative_to(vault),
            "cache/K-20260803-001.md",
            "K-20260803-001",
            expected_source_bytes=current,
            now=NOW,
        )
    assert not (vault / "cache" / "K-20260803-001.md").exists()
