"""Check active documentation structure, budgets, links, and archive markers."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs" / "archive"
GENERATED = ROOT / "docs" / "generated"
BUDGETS = {
    ROOT / "README.md": 140,
    ROOT / "README_EN.md": 140,
    ROOT / "AGENTS.md": 120,
    ROOT / "docs" / "PROJECT.md": 200,
    ROOT / "docs" / "SPEC.md": 280,
    ROOT / "docs" / "RULES.md": 140,
}
REQUIRED = {
    *BUDGETS,
    ROOT / "docs" / "design" / "design.html",
    ROOT / "docs" / "design" / "interaction.html",
    ROOT / "docs" / "architecture" / "architecture.html",
    ROOT / "docs" / "architecture" / "decisions" / "0001-document-authority.md",
    ROOT / "docs" / "cold_start_report.md",
    ROOT / "docs" / "acceptance" / "README.md",
    ROOT / "docs" / "generated" / "README.md",
    ROOT / "docs" / "archive" / "README.md",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
DOCUMENT_SUFFIXES = {".md", ".html", ".css", ".js"}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag in {"a", "link"} and values.get("href"):
            self.links.append(("href", values["href"] or ""))
        if tag == "script" and values.get("src"):
            self.links.append(("src", values["src"] or ""))


def active_documents() -> list[Path]:
    roots = [ROOT / "README.md", ROOT / "README_EN.md", ROOT / "AGENTS.md"]
    docs = [
        path
        for path in (ROOT / "docs").rglob("*")
        if path.is_file()
        and path.suffix in DOCUMENT_SUFFIXES
        and ARCHIVE not in path.parents
        and (GENERATED not in path.parents or path.name == "README.md")
    ]
    return sorted({*roots, *docs})


def local_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not parts.path:
        return None
    decoded = unquote(parts.path)
    if decoded.startswith("/"):
        return Path(decoded)
    return (source.parent / decoded).resolve()


def markdown_links(path: Path) -> list[str]:
    return MARKDOWN_LINK.findall(path.read_text(encoding="utf-8"))


def html_links(path: Path, errors: list[str]) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    parser = LinkParser()
    parser.feed(text)
    duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    for value in duplicate_ids:
        errors.append(f"{path.relative_to(ROOT)}: duplicate HTML id #{value}")
    for marker in ("data-doc-search", "data-theme-toggle"):
        if marker not in text:
            errors.append(f"{path.relative_to(ROOT)}: missing {marker}")
    return parser.links


def main() -> int:
    errors: list[str] = []
    inbound: set[Path] = set()

    for path in sorted(REQUIRED):
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")

    for path, limit in BUDGETS.items():
        if path.exists():
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > limit:
                errors.append(f"{path.relative_to(ROOT)}: {lines} lines exceeds {limit}")

    documents = active_documents()
    for path in documents:
        if path.suffix == ".md":
            links = [("href", target) for target in markdown_links(path)]
        elif path.suffix == ".html":
            links = html_links(path, errors)
        else:
            links = []

        for kind, raw_target in links:
            parts = urlsplit(raw_target.strip().strip("<>"))
            if kind == "src" and parts.scheme in {"http", "https"}:
                errors.append(f"{path.relative_to(ROOT)}: external runtime asset {raw_target}")
                continue
            target = local_target(path, raw_target)
            if target is None:
                continue
            if not target.exists():
                errors.append(
                    f"{path.relative_to(ROOT)}: broken link {raw_target}"
                )
            else:
                inbound.add(target)

    allowed_orphans = {ROOT / "README.md"}
    for path in documents:
        if path not in inbound and path not in allowed_orphans:
            errors.append(f"orphan active document: {path.relative_to(ROOT)}")

    for path in sorted(ARCHIVE.rglob("*")):
        if path.is_file() and path.suffix in {".md", ".html"}:
            text = path.read_text(encoding="utf-8", errors="replace").upper()
            if "ARCHIV" not in text or "READ ONLY" not in text.replace("-", " "):
                errors.append(f"{path.relative_to(ROOT)}: missing archive marker")

    if errors:
        print("Documentation check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Documentation check passed: {len(documents)} active files, "
        f"{len(REQUIRED)} required files, all budgets and local links valid."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
