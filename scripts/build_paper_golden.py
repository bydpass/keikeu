"""Generate reviewed synthetic Paper v4 cross-language examples, never author files."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/desktop/python"))
from keikeu_core.markdown_io import parse_paper_v4_bytes, render_paper_v4_bytes
from keikeu_core.models import CardPageV4, PaperV4


def projection(paper: PaperV4) -> dict:
    result = asdict(paper)
    result["created"] = paper.created.isoformat()
    result["updated"] = paper.updated.isoformat()
    result["extra_frontmatter"] = list(paper.extra_frontmatter.items())
    return result


def examples() -> dict:
    base = PaperV4(
        code="K-20260907-001", created=datetime(2026, 9, 7, 1, 2, 3),
        updated=datetime(2026, 9, 7, 1, 2, 3), display_name="合成稿 -- café",
        pages=[CardPageV4(name="第一页--", content="合成测试\n\n", type="summary"),
               CardPageV4(name=None, content="second page Straße e\u0301", type="snapshot")],
        tags=["中文", "a,b", "A", "a"],
        legacy_title="", extra_frontmatter={"unknown": "a\\b\nline\rreturn", "empty": "", "colon": "x:y"},
    )
    original = render_paper_v4_bytes(base)
    cases = [("canonical", original), ("crlf", original.replace(b"\n", b"\r\n")),
             ("no_final_newline", original[:-1])]
    for content in ["", "\n", "\nbody\n", "<!-- /keikeu:page -->", "\\<!-- /keikeu:page -->",
                    "\\\\<!-- keikeu:page arbitrary -->", "# heading\n## Tags\n- body", "😀\x00\u2028"]:
        item = PaperV4(code=base.code, created=base.created, updated=base.updated,
                       pages=[CardPageV4(name="有标题", content=content)], tags=[])
        cases.append((f"body_{len(cases)}", render_paper_v4_bytes(item)))
    for value in ["2026-09-07", "20260907T010203", "2026-W37-1T01:02:03",
                  "2026-09-07 01:02", "2026-09-07T01:02:03.123456",
                  "2026-09-07T01:02:03Z", "2026-09-07T01:02:03+05:30",
                  "2026-09-07T01:02:03-04:00", "2026-09-07T01:02:03.123456789",
                  "2026-W37", "2026W37", "2026W371", "2026-09-07T01",
                  "2026-09-07T01:02:03+00:00:00.5", "2026-09-07T01:02:03+01:60"]:
        cases.append(("datetime_" + value, original.replace(b"2026-09-07T01:02:03", value.encode())))
    cases.extend([
        ("tags_trim_deduplicate", original.replace("- 中文".encode(), "-   中文  \n- 中文".encode())),
        ("unknown_scalar_escape", original.replace(b"unknown: a", b"unknown: \\q\\a")),
        ("unicode_sequence", original.replace(b"K-20260907-001", "K-20260907-٠٠١".encode())),
    ])
    mutations = [
        ("duplicate_frontmatter", b"type: paper", b"type: paper\ntype: paper"),
        ("missing_code", b"code: K-20260907-001\n", b""),
        ("bad_date", b"2026-09-07T01:02:03", b"2026-02-30T00:00:00"),
        ("zero_sequence", b"K-20260907-001", b"K-20260907-000"),
        ("bare_cr", b"\n", b"\r"),
        ("mixed_newlines", b"---\n", b"---\r\n"),
        ("heading_mismatch", b"# K-20260907-001", b"# K-20260907-002"),
        ("extra_blank", b"---\n#", b"---\n\n#"),
        ("second_summary", b'"type":"snapshot"', b'"type":"summary"'),
        ("unknown_page_type", b'"type":"snapshot"', b'"type":"outline"'),
        ("duplicate_json", b'"name":null', b'"name":null,"name":null'),
        ("missing_json_key", b'"name":null,', b""),
        ("extra_json_key", b'"name":null,', b'"name":null,"other":null,'),
        ("json_wrong_type", b'"name":null', b'"name":5'),
        ("raw_hyphens", b'\\u002d\\u002d', b'--'),
        ("missing_end", b"<!-- /keikeu:page -->", b""),
        ("nested_start", "合成测试".encode(), b'<!-- keikeu:page {"name":null,"type":null} -->'),
        ("missing_tags", b"## Tags", b"## Other"),
        ("empty_tag", "- 中文".encode(), b"- "),
        ("control_tag", "- 中文".encode(), b"- a\x00b"),
        ("name_control", "第一页".encode(), b"a\\u0000b"),
    ]
    for name, old, new in mutations:
        assert old in original, name
        cases.append((name, original.replace(old, new, 1)))
    cases.extend([("bom", b"\xef\xbb\xbf" + original), ("invalid_utf8", b"\xff" + original),
                  ("trailing_text", original + b"bad\n"), ("trailing_blank", original + b"\n")])
    records = []
    for name, raw in cases:
        record = {"name": name, "hex": raw.hex()}
        try:
            paper = parse_paper_v4_bytes(raw)
            record.update(paper=projection(paper), canonical=render_paper_v4_bytes(paper).decode())
        except (ValueError, UnicodeError):
            record["error"] = "repair_required"
        records.append(record)
    return {"version": 1, "source": "Paper v4 design section 8 plus reviewed Python parser semantics",
            "cases": records}


if __name__ == "__main__":
    target = ROOT / "tests/fixtures/paper-v4-golden.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(examples(), ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(examples()['cases'])} synthetic cases to {target.relative_to(ROOT)}")
    # Case folding must follow the accepted Python runtime, not a dependency's older table.
    pairs = []
    zeroes = []
    for codepoint in range(0x110000):
        char = chr(codepoint)
        if char.casefold() != char:
            folded = "".join(f"\\u{{{ord(c):x}}}" for c in char.casefold())
            pairs.append(f"    ('\\u{{{codepoint:x}}}', \"{folded}\"),")
        if unicodedata.category(char) == "Nd" and unicodedata.decimal(char) == 0:
            zeroes.append(hex(codepoint))
    table = ROOT / "crates/keikeu-core/src/unicode_data.rs"
    table.write_text(
        f"// Generated by scripts/build_paper_golden.py; Python Unicode {unicodedata.unidata_version}.\n"
        "// Comparison only: never rewrite author content.\n"
        "#[rustfmt::skip]\npub const DECIMAL_ZEROES: &[u32] = &[" + ", ".join(zeroes) + "];\n"
        "#[rustfmt::skip]\npub const CASEFOLD: &[(char, &str)] = &[\n" + "\n".join(pairs) + "\n];\n"
    )
