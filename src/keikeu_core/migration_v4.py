"""Explicit, additive Paper v2/v3 to v4 migration for copied/test Vaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import unicodedata
from typing import Callable

from keikeu_core.indexer import _write_json_at, rebuild_index_v4
from keikeu_core.legacy_v3 import PaperV3, parse_paper_v3_bytes
from keikeu_core.markdown_io import (
    parse_paper_v4_bytes,
    render_paper_v4_bytes,
    replace_paper_v4_bytes,
)
from keikeu_core.models import CardPageV4, PaperV4
from keikeu_core.vault import (
    _open_pinned_vault_root,
    _open_relative_directory_no_follow,
    _read_regular_bytes_at,
    _require_directory_path_identity,
    _scan_paper_area_at,
    copy_vault_no_follow,
    snapshot_regular_tree_no_follow,
)

__all__ = [
    "MigrationCandidateV4",
    "MigrationCommitUnknown",
    "MigrationIssueV4",
    "MigrationPreflightV4",
    "MigrationResultV4",
    "classify_migration_stage",
    "inspect_paper_v4_migration",
    "migrate_papers_to_v4",
]


_FENCE = "---"
_LEGACY_HEADERS = ("## 初稿副本", "## Summary", "## Highlights", "## Tags")
_V2_ITEM = re.compile(r"^([1-9]\d*)\. (.*)$")
_V3_ITEM = re.compile(r"^([1-9]\d*)\. 名称：(.*)$")
_REPORT_NAME = "keikeu_migration_v4.json"


@dataclass(frozen=True)
class MigrationIssueV4:
    path: Path
    category: str
    reason: str


@dataclass(frozen=True)
class MigrationCandidateV4:
    path: Path
    source_schema: int
    source_digest: str
    source_bytes: bytes = field(repr=False)
    target_bytes: bytes = field(repr=False)


@dataclass(frozen=True)
class MigrationPreflightV4:
    vault: Path
    state: str
    candidates: tuple[MigrationCandidateV4, ...]
    v4_paths: tuple[Path, ...]
    observed: tuple[tuple[Path, str, int], ...]
    issues: tuple[MigrationIssueV4, ...]
    tree_snapshot: tuple[object, ...] = field(repr=False)

    @property
    def ready(self) -> bool:
        return not self.issues and bool(self.candidates)

    @property
    def complete(self) -> bool:
        return not self.issues and not self.candidates


@dataclass(frozen=True)
class MigrationResultV4:
    backup_path: Path
    report_path: Path
    converted_count: int
    warnings: tuple[str, ...]


class MigrationCommitUnknown(RuntimeError):
    """Migration crossed its first Paper replacement and must be rescanned."""

    def __init__(self, converted_count: int) -> None:
        super().__init__(
            f"migration result is unknown after {converted_count} Paper replacement(s)"
        )
        self.converted_count = converted_count


def _decode_legacy(data: bytes) -> tuple[str, list[str]]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("legacy Paper must not contain a UTF-8 BOM")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("legacy Paper must be valid UTF-8") from None
    if "\r" in text:
        raise ValueError("legacy Paper line endings are not valid for the frozen parser")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return text, lines


def _unescape_scalar(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            escaped = value[index + 1]
            decoded = {"n": "\n", "r": "\r", "\\": "\\"}.get(escaped)
            out.extend(("\\", escaped)) if decoded is None else out.append(decoded)
            index += 2
        else:
            out.append(value[index])
            index += 1
    return "".join(out)


def _frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    if not lines or lines[0] != _FENCE:
        raise ValueError("frontmatter must start on the first line")
    values: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line == _FENCE:
            return values, index + 1
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError("frontmatter line has no colon")
        key = key.strip()
        if not key:
            raise ValueError("frontmatter key is empty")
        if any(
            unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
            for character in key
        ):
            raise ValueError("frontmatter key contains an invalid character")
        if key in values:
            raise ValueError(f"frontmatter repeats key: {key}")
        values[key] = _unescape_scalar(value.strip())
    raise ValueError("frontmatter fence was never closed")


def _section_payloads(lines: list[str], start: int) -> dict[str, list[str]]:
    body = lines[start:]
    if len(body) < 3 or not body[0].startswith("# ") or body[1] != "":
        raise ValueError("legacy body must start with one code heading and blank line")
    positions = [index for index, line in enumerate(body) if line in _LEGACY_HEADERS]
    headers = [body[index] for index in positions]
    if headers != list(_LEGACY_HEADERS):
        raise ValueError("legacy sections must appear exactly once in the required order")
    if positions[0] != 2:
        raise ValueError("stray text appears before the first legacy section")
    payloads: dict[str, list[str]] = {}
    for section_index, position in enumerate(positions):
        next_position = (
            positions[section_index + 1]
            if section_index + 1 < len(positions)
            else len(body)
        )
        block = body[position + 1 : next_position]
        if section_index + 1 < len(positions):
            if not block or block[0] != "" or block[-1] != "":
                raise ValueError(f"legacy section spacing is ambiguous: {body[position]}")
            block = block[1:-1]
        elif block:
            if block[0] != "":
                raise ValueError("legacy Tags items require one blank line")
            block = block[1:]
        payloads[body[position]] = block
    return payloads


def _audit_v2_highlights(lines: list[str]) -> None:
    if not lines:
        return
    expected = 1
    content_seen = False
    for line in lines:
        match = _V2_ITEM.fullmatch(line)
        if match is not None:
            if int(match.group(1)) != expected:
                raise ValueError(f"v2 Highlight numbering must be sequential at {expected}")
            if content_seen is False and expected > 1:
                raise ValueError(f"v2 Highlight {expected - 1} is empty")
            expected += 1
            content_seen = bool(match.group(2).strip())
        elif expected == 1:
            raise ValueError("unassigned text appears before the first v2 Highlight")
        else:
            content_seen = content_seen or bool(line.strip())
    if not content_seen:
        raise ValueError(f"v2 Highlight {expected - 1} is empty")


def _audit_v3_highlights(lines: list[str]) -> None:
    if not lines:
        return
    index = 0
    expected = 1
    while index < len(lines):
        match = _V3_ITEM.fullmatch(lines[index])
        if match is None or int(match.group(1)) != expected:
            raise ValueError(f"v3 Highlight descriptor is malformed at item {expected}")
        raw_name = match.group(2)
        if raw_name != raw_name.strip():
            raise ValueError(f"v3 Highlight {expected} name has outer whitespace")
        index += 1
        if index >= len(lines) or lines[index] != "   内容：":
            raise ValueError(f"v3 Highlight {expected} is missing its 内容 marker")
        index += 1
        content: list[str] = []
        while index < len(lines) and _V3_ITEM.fullmatch(lines[index]) is None:
            if lines[index] == "" and index + 1 < len(lines) and _V3_ITEM.fullmatch(lines[index + 1]):
                index += 1
                break
            if not lines[index].startswith("   "):
                raise ValueError(f"v3 Highlight {expected} contains unassigned text")
            content.append(lines[index][3:])
            index += 1
        if not "\n".join(content).strip():
            raise ValueError(f"v3 Highlight {expected} is empty")
        expected += 1


def _audit_tags(lines: list[str]) -> list[str]:
    tags: list[str] = []
    for index, line in enumerate(lines, start=1):
        if not line.startswith("- "):
            raise ValueError(f"legacy Tag {index} is multiline or malformed")
        tag = line[2:]
        if not tag:
            raise ValueError(f"legacy Tag {index} is empty")
        if tag != tag.strip():
            raise ValueError(f"legacy Tag {index} has outer whitespace")
        if any(
            unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
            for character in tag
        ):
            raise ValueError(f"legacy Tag {index} contains an invalid character")
        if tag in tags:
            raise ValueError(f"legacy Tag {index} duplicates an earlier Tag after trim")
        tags.append(tag)
    return tags


def _legacy_to_v4(data: bytes) -> tuple[int, PaperV3, PaperV4, bytes]:
    _text, lines = _decode_legacy(data)
    values, body_start = _frontmatter(lines)
    schema_value = values.get("schema_version")
    if schema_value not in {"2", "3"}:
        raise ValueError("legacy Paper must declare schema_version 2 or 3")
    if values.get("type") != "paper":
        raise ValueError("legacy Paper must declare type: paper")
    for key in ("code", "created", "updated"):
        if key not in values:
            raise ValueError(f"legacy Paper frontmatter is missing {key}")
    payloads = _section_payloads(lines, body_start)
    if lines[body_start] != f"# {values['code']}":
        raise ValueError("legacy heading does not match frontmatter code")
    if not "\n".join(payloads["## 初稿副本"]).strip():
        raise ValueError("legacy initial_summary must not be blank")
    if not "\n".join(payloads["## Summary"]).strip():
        raise ValueError("legacy Summary must not be blank")
    if schema_value == "2":
        _audit_v2_highlights(payloads["## Highlights"])
    else:
        _audit_v3_highlights(payloads["## Highlights"])
    raw_tags = _audit_tags(payloads["## Tags"])
    paper = parse_paper_v3_bytes(data)
    if paper.tags != raw_tags:
        raise ValueError("legacy Tags would change during normalization")
    target = PaperV4(
        code=paper.code,
        display_name=paper.display_name,
        pages=[
            CardPageV4(name=None, content=paper.summary, type="summary"),
            *[
                CardPageV4(
                    name=highlight.display_name,
                    content=highlight.content,
                    type="snapshot",
                )
                for highlight in paper.highlights
            ],
        ],
        tags=list(paper.tags),
        created=paper.created,
        updated=paper.updated,
        legacy_title=paper.legacy_title,
        extra_frontmatter=paper.extra_frontmatter.copy(),
    )
    target_bytes = render_paper_v4_bytes(target)
    if parse_paper_v4_bytes(target_bytes) != target:
        raise ValueError("v4 staging round-trip changed mapped fields")
    return int(schema_value), paper, target, target_bytes


def _read_relative(root_fd: int, vault: Path, relative: Path) -> bytes:
    parent_fd = _open_relative_directory_no_follow(root_fd, relative.parent, vault)
    try:
        data, _identity = _read_regular_bytes_at(parent_fd, relative.name, vault / relative)
        _require_directory_path_identity(vault / relative.parent, parent_fd)
        return data
    finally:
        os.close(parent_fd)


def _schema_hint(data: bytes) -> int:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Paper must not contain a UTF-8 BOM")
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise ValueError("Paper must be valid UTF-8") from None
    values, _body_start = _frontmatter(lines)
    value = values.get("schema_version")
    if value not in {"2", "3", "4"}:
        raise ValueError("unsupported or missing Paper schema_version")
    return int(value)


def inspect_paper_v4_migration(vault: Path) -> MigrationPreflightV4:
    """Read all active/folder/Trash Papers and build a zero-write preflight."""
    snapshot_error: str | None = None
    try:
        before_snapshot = snapshot_regular_tree_no_follow(vault)
    except (OSError, ValueError) as exc:
        before_snapshot = ()
        snapshot_error = str(exc)
    vault, root_fd = _open_pinned_vault_root(vault)
    candidates: list[MigrationCandidateV4] = []
    v4_paths: list[Path] = []
    observed: list[tuple[Path, str, int]] = []
    issues: list[MigrationIssueV4] = []
    if snapshot_error is not None:
        issues.append(MigrationIssueV4(Path("."), "tree", snapshot_error))
    code_paths: dict[str, list[Path]] = {}
    try:
        active, active_errors = _scan_paper_area_at(root_fd, vault, Path("cache"))
        try:
            trash, trash_errors = _scan_paper_area_at(
                root_fd,
                vault,
                Path(".trash/cache"),
            )
        except FileNotFoundError:
            trash, trash_errors = [], []
        issues.extend(
            MigrationIssueV4(Path(item["path"]), "path", item["reason"])
            for item in [*active_errors, *trash_errors]
        )
        for relative in [*active, *trash]:
            try:
                data = _read_relative(root_fd, vault, relative)
                digest = hashlib.sha256(data).hexdigest()
                schema = _schema_hint(data)
                if schema == 4:
                    try:
                        paper = parse_paper_v4_bytes(data)
                    except (ValueError, UnicodeError) as exc:
                        issues.append(MigrationIssueV4(relative, "v4_paper", str(exc)))
                        continue
                    v4_paths.append(relative)
                else:
                    schema, _legacy, paper, target_bytes = _legacy_to_v4(data)
                    candidates.append(
                        MigrationCandidateV4(
                            path=relative,
                            source_schema=schema,
                            source_digest=digest,
                            source_bytes=data,
                            target_bytes=target_bytes,
                        )
                    )
                if relative.name != f"{paper.code}.md":
                    raise ValueError("Paper filename and frontmatter code do not match")
                observed.append((relative, digest, schema))
                code_paths.setdefault(paper.code, []).append(relative)
            except (OSError, ValueError, UnicodeError) as exc:
                issues.append(MigrationIssueV4(relative, "paper", str(exc)))
        for code, paths in sorted(code_paths.items()):
            if len(paths) > 1:
                issues.extend(
                    MigrationIssueV4(
                        relative,
                        "duplicate_code",
                        f"duplicate Paper code across active/Trash: {code}",
                    )
                    for relative in paths
                )
        _require_directory_path_identity(vault, root_fd)
    finally:
        os.close(root_fd)
    if before_snapshot:
        after_snapshot = snapshot_regular_tree_no_follow(vault)
        if after_snapshot != before_snapshot:
            raise ValueError("Vault changed during Paper migration preflight")
    candidates.sort(key=lambda item: str(item.path))
    v4_paths.sort(key=str)
    observed.sort(key=lambda item: str(item[0]))
    issues = sorted(
        {
            (item.path, item.category, item.reason): item
            for item in issues
        }.values(),
        key=lambda item: (str(item.path), item.category, item.reason),
    )
    blocking_issues = [item for item in issues if item.category != "v4_paper"]
    if blocking_issues or (issues and candidates):
        state = "repair_required"
    elif candidates and v4_paths:
        state = "mixed"
    elif candidates:
        state = "legacy"
    elif v4_paths:
        state = "pure_v4"
    else:
        state = "empty"
    return MigrationPreflightV4(
        vault=vault,
        state=state,
        candidates=tuple(candidates),
        v4_paths=tuple(v4_paths),
        observed=tuple(observed),
        issues=tuple(issues),
        tree_snapshot=before_snapshot,
    )


def classify_migration_stage(vault: Path) -> str:
    """Classify the next explicit migration Gate without changing the Vault."""
    has_v01, unsafe = _v01_marker_no_follow(vault)
    if unsafe:
        return "repair_required"
    if has_v01:
        if _vault_contains_paper_marker(vault):
            return "repair_required"
        return "v01_to_v3"
    preflight = inspect_paper_v4_migration(vault)
    if any(item.category != "v4_paper" for item in preflight.issues):
        return "repair_required"
    if preflight.issues and preflight.candidates:
        return "repair_required"
    if preflight.candidates:
        return "paper_to_v4"
    return "ready"


def _v01_marker_no_follow(vault: Path) -> tuple[bool, bool]:
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        marker = False
        unsafe = False
        try:
            index_bytes, _identity = _read_regular_bytes_at(
                root_fd,
                "keikeu_index.json",
                vault / "keikeu_index.json",
            )
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            unsafe = True
        else:
            try:
                index = json.loads(index_bytes.decode("utf-8"))
            except (ValueError, UnicodeError):
                pass
            else:
                marker = isinstance(index, dict) and index.get("version") == 1
        try:
            outlines = os.stat("outlines", dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISDIR(outlines.st_mode):
                marker = True
            else:
                unsafe = True
        try:
            paths, errors = _scan_paper_area_at(root_fd, vault, Path("cache"))
        except FileNotFoundError:
            paths, errors = [], []
        unsafe = unsafe or bool(errors)
        for relative in paths:
            try:
                text = _read_relative(root_fd, vault, relative).decode("utf-8")
            except (OSError, ValueError, UnicodeError):
                unsafe = True
                continue
            if any(line.strip() == "type: cache" for line in text.splitlines()):
                marker = True
        return marker, unsafe
    finally:
        os.close(root_fd)


def _vault_contains_paper_marker(vault: Path) -> bool:
    vault, root_fd = _open_pinned_vault_root(vault)
    try:
        paths: list[Path] = []
        for base in (Path("cache"), Path(".trash/cache")):
            try:
                area_paths, _errors = _scan_paper_area_at(root_fd, vault, base)
            except FileNotFoundError:
                continue
            paths.extend(area_paths)
        for relative in paths:
            try:
                text = _read_relative(root_fd, vault, relative).decode("utf-8")
            except (OSError, UnicodeError, ValueError):
                continue
            if any(line.strip() == "type: paper" for line in text.splitlines()):
                return True
        return False
    finally:
        os.close(root_fd)


def _unique_backup_path(vault: Path, backup_root: Path, now: datetime) -> Path:
    root = backup_root.expanduser().absolute()
    vault_absolute = vault.expanduser().absolute()
    if root == vault_absolute or vault_absolute in root.parents:
        raise ValueError("backup_root must be outside the active Vault")
    stem = f"{vault.name}-paper-v4-backup-{now:%Y%m%d-%H%M%S}"
    candidate = root / stem
    suffix = 2
    while os.path.lexists(candidate):
        candidate = root / f"{stem}-{suffix}"
        suffix += 1
    return candidate


def _preflight_signature(preflight: MigrationPreflightV4) -> tuple[object, ...]:
    return (
        preflight.state,
        tuple((item.path, item.source_digest, item.source_schema) for item in preflight.candidates),
        preflight.v4_paths,
        preflight.observed,
        preflight.issues,
        preflight.tree_snapshot,
    )


def migrate_papers_to_v4(
    vault: Path,
    preflight: MigrationPreflightV4,
    *,
    backup_root: Path | None = None,
    now: datetime | None = None,
    failure_hook: Callable[[str], None] | None = None,
) -> MigrationResultV4:
    """Back up, verify, then CAS-replace every preflight-approved legacy Paper."""
    current = inspect_paper_v4_migration(vault)
    if current.vault != preflight.vault or _preflight_signature(current) != _preflight_signature(preflight):
        raise ValueError("Paper migration preflight is stale")
    if not current.ready:
        raise ValueError("Paper migration preflight is not ready")
    migration_time = now or datetime.now()
    backup_path = _unique_backup_path(
        current.vault,
        backup_root or current.vault.parent / "keikeu-v4-backups",
        migration_time,
    )
    source_snapshot = snapshot_regular_tree_no_follow(current.vault)
    if source_snapshot != current.tree_snapshot:
        raise ValueError("Paper migration preflight is stale")
    if failure_hook is not None:
        failure_hook("before_backup")
    copy_vault_no_follow(current.vault, backup_path)
    if snapshot_regular_tree_no_follow(backup_path) != source_snapshot:
        raise ValueError("verified backup manifest differs from the source Vault")
    if snapshot_regular_tree_no_follow(current.vault) != source_snapshot:
        raise ValueError("source Vault changed before Paper replacement")
    if failure_hook is not None:
        failure_hook("after_backup")

    converted = 0
    try:
        for index, candidate in enumerate(current.candidates, start=1):
            if failure_hook is not None:
                failure_hook(f"before_replace:{index}")
            replace_paper_v4_bytes(
                current.vault,
                candidate.path,
                candidate.target_bytes,
                expected_source_bytes=candidate.source_bytes,
            )
            converted += 1
            if failure_hook is not None:
                failure_hook(f"after_replace:{index}")
        completed = inspect_paper_v4_migration(current.vault)
        if not completed.complete or completed.state not in {"pure_v4", "empty"}:
            raise ValueError("Paper migration did not converge to a pure v4 Vault")
        warnings: list[str] = []
        try:
            rebuild_index_v4(current.vault)
        except (OSError, ValueError, UnicodeError):
            warnings.append("index_degraded")
        vault_path, root_fd = _open_pinned_vault_root(current.vault)
        try:
            _write_json_at(
                root_fd,
                _REPORT_NAME,
                {
                    "version": 1,
                    "completed_at": migration_time.isoformat(),
                    "backup_verified": True,
                    "backup_name": backup_path.name,
                    "converted_count": converted,
                    "remaining_count": 0,
                    "discarded_initial_summary_count": converted,
                    "paths": [str(item.path) for item in current.candidates],
                },
                guard_path=vault_path,
                guard_fd=root_fd,
            )
        finally:
            os.close(root_fd)
    except Exception as exc:
        if converted:
            raise MigrationCommitUnknown(converted) from exc
        raise
    return MigrationResultV4(
        backup_path=backup_path,
        report_path=current.vault / _REPORT_NAME,
        converted_count=converted,
        warnings=tuple(warnings),
    )
