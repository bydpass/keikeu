"""Markdown serialization for keikeu (appdesign.md Step 4).

Pure Python. No Flet, no GUI, no third-party dependencies (no PyYAML).

Each user asset is one Markdown file: a flat ``key: value`` frontmatter block
fenced by ``---`` lines at the very top, then a body of ``#``/``##`` sections.
Frontmatter holds authoritative scalars (status, enums, datetimes) parsed back
exactly; the body holds free-text prose and lists.

Product invariant 1 (sacred): the user's words are preserved verbatim. Free-text
body fields (a cache's raw spark, an outline's raw inspiration, etc.) round-trip
without summarizing, flattening, or rewriting. The only framing this module owns
is the single blank line inserted after each header — that one blank line is
stripped on read; everything else, including internal blank lines, ``##`` and
``---`` lines inside content, is kept byte-for-byte.

Documented limitations (acceptable for MVP): a free-text field loses purely
leading/trailing newline framing; a content line byte-identical to a known
structural header is not supported; interior CRLF is normalized to LF. In the
list fields, a character name containing ``", "`` is split on that delimiter.
Frontmatter scalars are backslash-escaped, so they round-trip exactly even
across embedded newlines.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
import os
from pathlib import Path
import re
import secrets
import tempfile

from keikeu_core.models import (
    Cache,
    CacheStatus,
    EndingType,
    Outline,
    Paper,
    Relation,
    RelationType,
    validate_paper_code,
)

__all__ = [
    "write_cache",
    "read_cache",
    "update_cache",
    "next_paper_code",
    "write_paper",
    "read_paper",
    "update_paper",
    "copy_paper_with_code",
    "rename_paper",
    "write_outline",
    "read_outline",
    "update_outline",
]

_FENCE = "---"

# Body section headers, byte-exact and in document order. A body line is treated
# as a section boundary only if it is identical to one of these for its type.
_CACHE_HEADERS = ("## 原始灵感", "## 临时备注")
_PAPER_HEADERS = ("## 初稿副本", "## Summary", "## Highlights", "## Tags")
_OUTLINE_HEADERS = (
    "## 1. 原始灵感",
    "## 2. 整理后摘要",
    "## 3. Fandom + 人物 / CP",
    "## 4. 观前提醒",
    "## 5. 流水账",
    "## 6. Ending Type",
    "## 7. 与其他灵感的逻辑关联（Optional）",
)

# Characters that are unsafe in a filename on common filesystems.
_DANGEROUS_CHARS = set('/\\:*?"<>|')
_PAPER_NUMBERED_ITEM_RE = re.compile(r"^([1-9]\d*)\. (.*)$")
_PAPER_CODE_FILENAME_RE = re.compile(r"^K-\d{8}-(\d{3})$")


# --------------------------------------------------------------------------- #
# Filename helpers
# --------------------------------------------------------------------------- #


def _slugify(title: str) -> str:
    """Turn ``title`` into a filesystem-safe slug, keeping CJK and alphanumerics.

    Removes filesystem-dangerous characters and ASCII control characters,
    collapses internal whitespace runs to a single ``-``, and strips leading and
    trailing dots and whitespace. Falls back to ``"untitled"`` when nothing
    usable remains.
    """
    kept = []
    for ch in title:
        if ch in _DANGEROUS_CHARS:
            continue
        # Drop ASCII control characters, but keep whitespace controls (tab,
        # newline): str.split below treats them as word separators, so they
        # become slug "-" boundaries rather than being silently swallowed.
        if ord(ch) < 0x20 and not ch.isspace():
            continue
        kept.append(ch)
    cleaned = "".join(kept)
    # Collapse internal whitespace runs (incl. tab/newline) to a single "-".
    slug = "-".join(cleaned.split())
    slug = slug.strip(". \t")
    return slug or "untitled"


def _unique_path(directory: Path, created: datetime, title: str) -> Path:
    """Return a not-yet-existing file path in ``directory`` for the asset.

    Filename is ``<YYYY-MM-DD-HHMMSS>-<short_id>-<slug>.md``. ``short_id`` is a
    fresh 4-hex-char token regenerated until the path does not already exist, so
    two assets with the same second and title never collide.
    """
    stamp = created.strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(title)
    while True:
        short_id = secrets.token_hex(2)
        candidate = directory / f"{stamp}-{short_id}-{slug}.md"
        if not candidate.exists():
            return candidate


# --------------------------------------------------------------------------- #
# Frontmatter helpers
# --------------------------------------------------------------------------- #


def _escape_scalar(value: str) -> str:
    """Escape characters that would break a single-line frontmatter scalar.

    Frontmatter is flat ``key: value`` lines, so a raw newline (which would
    split the block — a ``---`` on its own line even terminates the fence) or a
    backslash must not appear unescaped. We backslash-escape ``\\``, ``\n`` and
    ``\r`` on write and reverse it on read, so any scalar — e.g. a hand-edited
    ``linked_outline`` — round-trips without corrupting the block or crashing
    the reader. Free-text prose lives in the body, not here.
    """
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def _unescape_scalar(value: str) -> str:
    """Reverse :func:`_escape_scalar`, decoding ``\\n`` / ``\\r`` / ``\\\\``."""
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            out.append({"n": "\n", "r": "\r", "\\": "\\"}.get(value[i + 1], value[i + 1]))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _format_frontmatter(pairs: list[tuple[str, str]]) -> str:
    """Render ordered ``key: value`` pairs as a fenced frontmatter block."""
    lines = [_FENCE]
    lines.extend(f"{key}: {_escape_scalar(value)}" for key, value in pairs)
    lines.append(_FENCE)
    return "\n".join(lines)


def _split_document(text: str) -> tuple[dict[str, str], list[str]]:
    """Split a document into (frontmatter dict, body lines).

    The frontmatter is the block between the first ``---`` line and the FIRST
    following ``---`` line; a later ``---`` in the body never terminates it.
    Body lines are returned without trailing newlines.
    """
    lines = text.split("\n")
    if not lines or lines[0] != _FENCE:
        raise ValueError("missing frontmatter fence at start of document")
    fm: dict[str, str] = {}
    idx = 1
    closed = False
    while idx < len(lines):
        line = lines[idx]
        idx += 1
        if line == _FENCE:
            closed = True
            break
        key, sep, value = line.partition(":")
        if sep:
            fm[key.strip()] = _unescape_scalar(value.strip())
    if not closed:
        raise ValueError("frontmatter fence was never closed")
    return fm, lines[idx:]


def _split_sections(
    body_lines: list[str], headers: tuple[str, ...]
) -> dict[str, str]:
    """Map each known header to its verbatim content within ``body_lines``.

    A line is a section boundary only if it is byte-identical to one of
    ``headers``. Content is everything between a header and the next header (or
    EOF). The single blank line this module inserts after each header is
    stripped; all other content — internal blank lines, ``##`` and ``---`` lines
    — is preserved verbatim.
    """
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body_lines:
        if line in headers:
            if current is not None:
                sections[current] = "\n".join(buf)
            current = line
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    # Strip exactly the one framing blank line we add after each header and
    # before the next header / EOF.
    for header, content in sections.items():
        if content.startswith("\n"):
            content = content[1:]
        if content.endswith("\n"):
            content = content[:-1]
        sections[header] = content
    return sections


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #


def _render_cache(cache: Cache) -> str:
    """Render ``cache`` to its full Markdown document text (frontmatter + body).

    The single source of truth for cache serialization, shared by
    :func:`write_cache` (fresh path) and :func:`update_cache` (in place).
    """
    frontmatter = _format_frontmatter(
        [
            ("type", "cache"),
            ("status", cache.status.value),
            ("created", cache.created.isoformat()),
            ("updated", cache.updated.isoformat()),
            ("linked_outline", cache.linked_outline or ""),
        ]
    )
    body = "\n".join(
        [
            f"# {cache.title}",
            "",
            "## 原始灵感",
            "",
            cache.raw,
            "",
            "## 临时备注",
            "",
            cache.notes,
        ]
    )
    return f"{frontmatter}\n{body}\n"


def write_cache(vault: Path, cache: Cache) -> Path:
    """Write ``cache`` as a Markdown file under ``vault/cache/`` (appdesign.md 6).

    Returns the path written. Creates the ``cache`` subdirectory if missing and
    chooses a collision-free filename from the cache's ``created`` timestamp.
    """
    directory = vault / "cache"
    directory.mkdir(parents=True, exist_ok=True)
    path = _unique_path(directory, cache.created, cache.title)
    path.write_text(_render_cache(cache), encoding="utf-8")
    return path


def update_cache(path: Path, cache: Cache) -> None:
    """Overwrite the cache file at ``path`` in place with ``cache``.

    Unlike :func:`write_cache`, this never picks a new filename: the GUI edits,
    saves, and archives an existing asset against its own path. Serialization
    stays in core via :func:`_render_cache`, never duplicated in the GUI layer.
    """
    path.write_text(_render_cache(cache), encoding="utf-8")


def read_cache(path: Path) -> Cache:
    """Read a cache Markdown file written by :func:`write_cache`.

    Frontmatter scalars are authoritative; ``raw`` and ``notes`` come from the
    body verbatim. An empty ``linked_outline`` in the file becomes ``None``.
    """
    text = path.read_text(encoding="utf-8")
    fm, body_lines = _split_document(text)
    title = _read_title(body_lines)
    sections = _split_sections(body_lines, _CACHE_HEADERS)
    linked = fm.get("linked_outline", "")
    return Cache(
        title=title,
        raw=sections.get("## 原始灵感", ""),
        notes=sections.get("## 临时备注", ""),
        status=CacheStatus(fm["status"]),
        created=datetime.fromisoformat(fm["created"]),
        updated=datetime.fromisoformat(fm["updated"]),
        linked_outline=linked or None,
    )


# --------------------------------------------------------------------------- #
# Paper v2
# --------------------------------------------------------------------------- #


def _paper_path(vault: Path, code: str) -> Path:
    """Return the fixed v2 path for ``code`` under ``vault/cache``."""
    return vault / "cache" / f"{validate_paper_code(code)}.md"


def next_paper_code(vault: Path, on_date: date | datetime | None = None) -> str:
    """Return the next unused neutral Paper code for ``on_date``.

    Existing matching filenames reserve their sequence even when their content
    is malformed, so generating a new Paper never overwrites an asset that
    needs recovery. ``on_date`` is injectable for deterministic tests.
    """
    if on_date is None:
        day = datetime.now().date()
    elif isinstance(on_date, datetime):
        day = on_date.date()
    elif isinstance(on_date, date):
        day = on_date
    else:
        raise ValueError("on_date must be a date or datetime")

    prefix = f"K-{day.strftime('%Y%m%d')}-"
    cache_dir = vault / "cache"
    used_sequences: set[int] = set()
    if cache_dir.is_dir():
        for path in cache_dir.glob(f"{prefix}*.md"):
            match = _PAPER_CODE_FILENAME_RE.fullmatch(path.stem)
            if match is not None:
                used_sequences.add(int(match.group(1)))

    for sequence in range(1, 1000):
        if sequence not in used_sequences:
            return f"{prefix}{sequence:03d}"
    raise ValueError(f"all Paper codes for {day.isoformat()} are in use")


def _render_paper(paper: Paper) -> str:
    """Render a validated Paper as the stable v2 Markdown contract."""
    paper.normalize()
    frontmatter: list[tuple[str, str]] = [
        ("type", "paper"),
        ("schema_version", "2"),
        ("code", paper.code),
        ("created", paper.created.isoformat()),
        ("updated", paper.updated.isoformat()),
    ]
    if paper.legacy_title is not None:
        frontmatter.append(("legacy_title", paper.legacy_title))
    known_fields = {key for key, _ in frontmatter}
    frontmatter.extend(
        (key, value)
        for key, value in paper.extra_frontmatter.items()
        if key not in known_fields
    )
    highlights = "\n".join(
        f"{index}. {highlight}"
        for index, highlight in enumerate(paper.highlights, start=1)
    )
    tags = "\n".join(f"- {tag}" for tag in paper.tags)
    def section(header: str, content: str) -> str:
        return f"{header}\n\n{content}" if content else header

    body = "\n\n".join(
        [
            f"# {paper.code}",
            section("## 初稿副本", paper.initial_summary),
            section("## Summary", paper.summary),
            section("## Highlights", highlights),
            section("## Tags", tags),
        ]
    )
    return f"{_format_frontmatter(frontmatter)}\n{body}\n"


def _parse_numbered_items(content: str) -> list[str]:
    """Read the simple ordered Markdown list used for Paper Highlights."""
    if not content:
        return []
    items: list[str] = []
    current: str | None = None
    for line in content.split("\n"):
        match = _PAPER_NUMBERED_ITEM_RE.fullmatch(line)
        if match is not None:
            if current is not None:
                items.append(current)
            current = match.group(2)
        elif current is not None:
            current = f"{current}\n{line}"
    if current is not None:
        items.append(current)
    # A manually repaired document without an ordered marker is kept as one
    # Highlight instead of being silently discarded.
    return items or [content]


def _parse_bullet_items(content: str) -> list[str]:
    """Read the simple unordered Markdown list used for Paper Tags."""
    if not content:
        return []
    items: list[str] = []
    current: str | None = None
    for line in content.split("\n"):
        if line.startswith("- "):
            if current is not None:
                items.append(current)
            current = line[2:]
        elif current is not None:
            current = f"{current}\n{line}"
    if current is not None:
        items.append(current)
    return items or [content]


def _write_temp_file(target: Path, text: str) -> Path:
    """Write complete text beside ``target`` and return its temporary path."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        return Path(handle.name)


def _atomic_replace_text(target: Path, text: str) -> None:
    """Replace an existing Paper atomically after its full temp write succeeds."""
    temporary = _write_temp_file(target, text)
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_create_text(target: Path, text: str) -> None:
    """Create a new Paper without ever replacing an existing destination."""
    temporary = _write_temp_file(target, text)
    try:
        # Linking within the same directory atomically fails when ``target``
        # already exists, avoiding a check-then-replace overwrite race.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def copy_paper_with_code(source: Path, destination: Path, new_code: str) -> None:
    """Create ``destination`` from ``source`` with an explicit new Paper code.

    The destination is created atomically without overwrite.  This is shared by
    explicit rename and recovery-bin collision handling so both preserve the
    stored initial draft, current Summary, and unknown frontmatter.
    """
    new_code = validate_paper_code(new_code)
    paper = read_paper(source)
    renamed = replace(paper, code=new_code)
    _atomic_create_text(destination, _render_paper(renamed))


def write_paper(vault: Path, paper: Paper) -> Path:
    """Persist a new Paper and freeze its initial Summary on first save.

    The code determines the fixed filename. Existing files are never replaced;
    use :func:`update_paper` or :func:`rename_paper` for later changes.
    """
    paper.normalize()
    path = _paper_path(vault, paper.code)
    if path.exists():
        raise FileExistsError(f"Paper already exists: {path}")
    stored = replace(paper, initial_summary=paper.summary)
    _atomic_create_text(path, _render_paper(stored))
    paper.initial_summary = stored.initial_summary
    return path


def read_paper(path: Path) -> Paper:
    """Read a Paper v2 Markdown file and preserve unknown frontmatter fields."""
    text = path.read_text(encoding="utf-8")
    frontmatter, body_lines = _split_document(text)
    if frontmatter.get("type") != "paper":
        raise ValueError("Paper must declare type: paper")
    if frontmatter.get("schema_version") != "2":
        raise ValueError("Paper must declare schema_version: 2")
    try:
        code = frontmatter["code"]
        created = datetime.fromisoformat(frontmatter["created"])
        updated = datetime.fromisoformat(frontmatter["updated"])
    except KeyError as exc:
        raise ValueError(f"Paper frontmatter is missing {exc.args[0]}") from None
    except ValueError:
        raise ValueError("Paper has invalid datetime frontmatter") from None

    sections = _split_sections(body_lines, _PAPER_HEADERS)
    initial_summary = sections.get("## 初稿副本", "")
    if not initial_summary.strip():
        raise ValueError("Paper initial_summary must not be blank")
    known_fields = {
        "type",
        "schema_version",
        "code",
        "created",
        "updated",
        "legacy_title",
    }
    return Paper(
        code=code,
        initial_summary=initial_summary,
        summary=sections.get("## Summary", ""),
        highlights=_parse_numbered_items(sections.get("## Highlights", "")),
        tags=_parse_bullet_items(sections.get("## Tags", "")),
        created=created,
        updated=updated,
        legacy_title=(
            frontmatter["legacy_title"] if "legacy_title" in frontmatter else None
        ),
        extra_frontmatter={
            key: value
            for key, value in frontmatter.items()
            if key not in known_fields
        },
    )


def update_paper(path: Path, paper: Paper) -> None:
    """Update a stored Paper while preserving its immutable first-save fields."""
    existing = read_paper(path)
    if paper.code != existing.code:
        raise ValueError("Paper code changes require rename_paper")
    paper.initial_summary = existing.initial_summary
    paper.legacy_title = existing.legacy_title
    paper.extra_frontmatter = existing.extra_frontmatter.copy()
    paper.normalize()
    _atomic_replace_text(path, _render_paper(paper))


def rename_paper(vault: Path, old_code: str, new_code: str) -> Path:
    """Explicitly rename one Paper code and its fixed Markdown filename.

    The replacement file is created first without overwriting anything. The
    old file is removed only after the new complete Paper exists, so a failed
    rename leaves the original asset available.
    """
    old_code = validate_paper_code(old_code)
    new_code = validate_paper_code(new_code)
    if old_code == new_code:
        raise ValueError("new Paper code must differ from the current code")
    source = _paper_path(vault, old_code)
    target = _paper_path(vault, new_code)
    if target.exists():
        raise FileExistsError(f"Paper already exists: {target}")
    existing = read_paper(source)
    if existing.code != old_code:
        raise ValueError("Paper filename and frontmatter code do not match")
    copy_paper_with_code(source, target, new_code)
    try:
        source.unlink()
    except OSError:
        # Best-effort rollback preserves the original source as the authority
        # if removing it fails after target creation.
        target.unlink(missing_ok=True)
        raise
    return target


# --------------------------------------------------------------------------- #
# Outline
# --------------------------------------------------------------------------- #


def _render_outline(outline: Outline) -> str:
    """Render ``outline`` to its full Markdown document text (frontmatter + body).

    The single source of truth for outline serialization, shared by
    :func:`write_outline` (fresh path) and :func:`update_outline` (in place).
    ``ending_type`` is an authoritative frontmatter scalar; ``custom_ending`` is
    free text stored verbatim in section 6 and parsed back from there (so a
    multi-line custom ending never enters the frontmatter).
    """
    frontmatter = _format_frontmatter(
        [
            ("type", "outline"),
            ("ending_type", outline.ending_type.value),
            ("created", outline.created.isoformat()),
            ("updated", outline.updated.isoformat()),
        ]
    )
    fandom_cp = "\n".join(
        [
            f"- Fandom: {outline.fandom}",
            f"- 人物: {', '.join(outline.characters)}",
            f"- CP: {outline.cp}",
        ]
    )
    warnings = "\n".join(
        [
            f"- 原作 / AU / IF / PA: {outline.warning_setting}",
            f"- CP 结构: {outline.warning_cp_structure}",
            f"- 情节元素: {outline.warning_elements}",
        ]
    )
    ending_body = (
        outline.custom_ending
        if outline.ending_type is EndingType.CUSTOM
        else outline.ending_type.value
    )
    relations_block = "\n\n".join(
        "\n".join(
            [
                f"- 关系: {rel.relation_type.value}",
                f"- 关联对象: {rel.target_path}",
                f"- 说明: {rel.note}",
            ]
        )
        for rel in outline.relations
    )
    body = "\n".join(
        [
            f"# {outline.title}",
            "",
            "## 1. 原始灵感",
            "",
            outline.raw_inspiration,
            "",
            "## 2. 整理后摘要",
            "",
            outline.summary,
            "",
            "## 3. Fandom + 人物 / CP",
            "",
            fandom_cp,
            "",
            "## 4. 观前提醒",
            "",
            warnings,
            "",
            "## 5. 流水账",
            "",
            outline.plot,
            "",
            "## 6. Ending Type",
            "",
            ending_body,
            "",
            "## 7. 与其他灵感的逻辑关联（Optional）",
            "",
            relations_block,
        ]
    )
    return f"{frontmatter}\n{body}\n"


def write_outline(vault: Path, outline: Outline) -> Path:
    """Write ``outline`` as a Markdown file under ``vault/outlines/`` (appdesign.md 5).

    Returns the path written. Creates the ``outlines`` subdirectory if missing
    and chooses a collision-free filename from the outline's ``created``
    timestamp.
    """
    directory = vault / "outlines"
    directory.mkdir(parents=True, exist_ok=True)
    path = _unique_path(directory, outline.created, outline.title)
    path.write_text(_render_outline(outline), encoding="utf-8")
    return path


def update_outline(path: Path, outline: Outline) -> None:
    """Overwrite the outline file at ``path`` in place with ``outline``.

    Unlike :func:`write_outline`, this never picks a new filename: the GUI edits,
    saves, and archives an existing asset against its own path. Serialization
    stays in core via :func:`_render_outline`, never duplicated in the GUI layer.
    """
    path.write_text(_render_outline(outline), encoding="utf-8")


def read_outline(path: Path) -> Outline:
    """Read an outline Markdown file written by :func:`write_outline`.

    ``ending_type`` is authoritative from frontmatter; ``custom_ending`` is read
    verbatim from section 6. Free-text sections round-trip verbatim; characters
    and relations are parsed from their list lines.
    """
    text = path.read_text(encoding="utf-8")
    fm, body_lines = _split_document(text)
    title = _read_title(body_lines)
    sections = _split_sections(body_lines, _OUTLINE_HEADERS)

    fandom, characters, cp = _parse_fandom_cp(
        sections.get("## 3. Fandom + 人物 / CP", "")
    )
    warning_setting, warning_cp_structure, warning_elements = _parse_warnings(
        sections.get("## 4. 观前提醒", "")
    )
    ending_type = EndingType(fm["ending_type"])
    ending_body = sections.get("## 6. Ending Type", "")
    custom_ending = ending_body if ending_type is EndingType.CUSTOM else ""
    relations = _parse_relations(
        sections.get("## 7. 与其他灵感的逻辑关联（Optional）", "")
    )
    return Outline(
        title=title,
        raw_inspiration=sections.get("## 1. 原始灵感", ""),
        summary=sections.get("## 2. 整理后摘要", ""),
        fandom=fandom,
        characters=characters,
        cp=cp,
        warning_setting=warning_setting,
        warning_cp_structure=warning_cp_structure,
        warning_elements=warning_elements,
        plot=sections.get("## 5. 流水账", ""),
        ending_type=ending_type,
        custom_ending=custom_ending,
        relations=relations,
        created=datetime.fromisoformat(fm["created"]),
        updated=datetime.fromisoformat(fm["updated"]),
    )


# --------------------------------------------------------------------------- #
# Body parsing helpers
# --------------------------------------------------------------------------- #


def _read_title(body_lines: list[str]) -> str:
    """Return the title from the first ``# `` heading, or ``""`` if absent."""
    for line in body_lines:
        if line.startswith("# "):
            return line[2:]
    return ""


def _parse_fandom_cp(content: str) -> tuple[str, list[str], str]:
    """Parse a section-3 block into (fandom, characters, cp).

    Characters are the ``- 人物: `` value split on ``", "`` with empties
    dropped, mirroring how :func:`write_outline` joins them.
    """
    fandom = ""
    characters: list[str] = []
    cp = ""
    for line in content.split("\n"):
        if line.startswith("- Fandom: "):
            fandom = line[len("- Fandom: ") :]
        elif line.startswith("- 人物: "):
            value = line[len("- 人物: ") :]
            characters = [c for c in value.split(", ") if c]
        elif line.startswith("- CP: "):
            cp = line[len("- CP: ") :]
    return fandom, characters, cp


def _parse_warnings(content: str) -> tuple[str, str, str]:
    """Parse section 4 into the three WI-1 warning/content-element fields."""
    warning_setting = ""
    warning_cp_structure = ""
    warning_elements = ""
    for line in content.split("\n"):
        if line.startswith("- 原作 / AU / IF / PA: "):
            warning_setting = line[len("- 原作 / AU / IF / PA: ") :]
        elif line.startswith("- CP 结构: "):
            warning_cp_structure = line[len("- CP 结构: ") :]
        elif line.startswith("- 情节元素: "):
            warning_elements = line[len("- 情节元素: ") :]
    return warning_setting, warning_cp_structure, warning_elements


def _parse_relations(content: str) -> list[Relation]:
    """Parse section-7 three-line relation blocks into ``Relation`` objects.

    An empty section yields ``[]``. Incomplete blocks are ignored so hand-edited
    Markdown with missing labels leaves relations blank rather than crashing.
    """
    relations: list[Relation] = []
    current: dict[str, str] = {}
    for raw_line in content.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- 关系: "):
            if current:
                _append_relation_if_complete(relations, current)
            current = {"relation_type": line[len("- 关系: ") :]}
        elif line.startswith("- 关联对象: "):
            current["target_path"] = line[len("- 关联对象: ") :]
        elif line.startswith("- 说明: "):
            current["note"] = line[len("- 说明: ") :]
    if current:
        _append_relation_if_complete(relations, current)
    return relations


def _append_relation_if_complete(
    relations: list[Relation], values: dict[str, str]
) -> None:
    """Append one parsed relation block if relation type and target are present."""
    relation_type = values.get("relation_type", "")
    target_path = values.get("target_path", "")
    if not relation_type or not target_path:
        return
    try:
        relations.append(
            Relation(
                relation_type=RelationType(relation_type),
                target_path=target_path,
                note=values.get("note", ""),
            )
        )
    except ValueError:
        return
