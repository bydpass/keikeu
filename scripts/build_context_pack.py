"""Build a small, local text bundle for models without repository tools."""

from __future__ import annotations

import argparse
from collections import Counter
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build" / "context" / "keikeu-context.txt"
DEFAULT_MAX_BYTES = 1_048_576
AUTHORITY_FILES = (
    PurePosixPath("AGENTS.md"),
    PurePosixPath("docs/SPEC.md"),
    PurePosixPath("docs/RULES.md"),
    PurePosixPath("docs/PROJECT.md"),
)
COLD_CONTEXT_PREFIXES = (
    PurePosixPath("docs/acceptance"),
    PurePosixPath("docs/archive"),
    PurePosixPath("docs/generated"),
    PurePosixPath("docs/manual"),
)


class ContextPackError(RuntimeError):
    """A request would produce an unsafe or misleading context pack."""


def _git_bytes(*args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ContextPackError(detail or f"git {' '.join(args)} failed")
    return completed.stdout


def _git_text(*args: str) -> str:
    return _git_bytes(*args).decode("utf-8", errors="replace")


def _tracked_files() -> set[PurePosixPath]:
    return {
        PurePosixPath(raw.decode("utf-8"))
        for raw in _git_bytes("ls-files", "-z").split(b"\0")
        if raw
    }


def _relative_request(raw: str) -> PurePosixPath:
    requested = Path(raw)
    if requested.is_absolute():
        raise ContextPackError(f"path must be repository-relative: {raw}")
    resolved = (ROOT / requested).resolve()
    try:
        relative = resolved.relative_to(ROOT)
    except ValueError as error:
        raise ContextPackError(f"path escapes the repository: {raw}") from error
    return PurePosixPath(relative.as_posix())


def _is_cold_context(path: PurePosixPath) -> bool:
    return any(path == prefix or prefix in path.parents for prefix in COLD_CONTEXT_PREFIXES)


def _read_text(path: PurePosixPath) -> str | None:
    absolute = ROOT / path.as_posix()
    if absolute.is_symlink():
        raise ContextPackError(f"symlinks are not allowed: {path}")
    if not absolute.is_file():
        raise ContextPackError(f"tracked file is missing: {path}")
    data = absolute.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _select_files(
    requests: list[str],
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    tracked = _tracked_files()
    missing_authority = [path for path in AUTHORITY_FILES if path not in tracked]
    if missing_authority:
        raise ContextPackError(f"authority file is not tracked: {missing_authority[0]}")

    selected = set(AUTHORITY_FILES)
    exact = set(AUTHORITY_FILES)
    skipped: Counter[str] = Counter()

    for raw in requests:
        requested = _relative_request(raw)
        if requested in tracked:
            selected.add(requested)
            exact.add(requested)
            continue

        prefix = "" if requested == PurePosixPath(".") else f"{requested.as_posix()}/"
        matches = sorted(path for path in tracked if path.as_posix().startswith(prefix))
        if not matches:
            raise ContextPackError(f"path is not a tracked file or directory: {raw}")
        for path in matches:
            if _is_cold_context(path):
                skipped["cold-context"] += 1
            else:
                selected.add(path)

    files: list[tuple[str, str]] = []
    for path in sorted(selected):
        text = _read_text(path)
        if text is None:
            if path in exact:
                raise ContextPackError(f"explicit file is not UTF-8 text: {path}")
            skipped["binary"] += 1
            continue
        files.append((path.as_posix(), text))
    return files, dict(sorted(skipped.items()))


def _render(files: list[tuple[str, str]], skipped: dict[str, int]) -> bytes:
    paths = [path for path, _ in files]
    branch = _git_text("branch", "--show-current").strip() or "(detached)"
    head = _git_text("rev-parse", "--short=12", "HEAD").strip()
    status = _git_text("status", "--short", "--", *paths).strip() or "(clean)"
    skipped_text = ", ".join(f"{name}={count}" for name, count in skipped.items()) or "none"
    parts = [
        "# keikeu task context pack\n",
        f"Branch: {branch}\n",
        f"HEAD: {head}\n",
        f"Selected files: {len(files)}\n",
        f"Skipped during directory expansion: {skipped_text}\n",
        "Selected-file worktree status:\n",
        f"{status}\n",
        "Source: current local working tree. This file performs no upload.\n",
    ]
    for path, text in files:
        parts.append(f"\n===== BEGIN FILE: {path} =====\n")
        parts.append(text)
        if not text.endswith("\n"):
            parts.append("\n")
        parts.append(f"===== END FILE: {path} =====\n")
    return "".join(parts).encode("utf-8")


def build_context_pack(
    requests: list[str], max_bytes: int = DEFAULT_MAX_BYTES
) -> tuple[bytes, list[str], dict[str, int]]:
    """Return a validated pack plus its selected paths and skip counts."""
    if max_bytes <= 0:
        raise ContextPackError("max bytes must be positive")
    files, skipped = _select_files(requests)
    pack = _render(files, skipped)
    if len(pack) > max_bytes:
        raise ContextPackError(
            f"pack is {len(pack)} bytes, above the {max_bytes}-byte limit; "
            "select fewer paths"
        )
    return pack, [path for path, _ in files], skipped


def _write_atomic(data: bytes) -> None:
    relative_output = OUTPUT.relative_to(ROOT)
    current = ROOT
    for part in relative_output.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise ContextPackError("context output must not traverse a symlink")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUTPUT.parent.resolve().is_relative_to(ROOT) or OUTPUT.is_symlink():
        raise ContextPackError("context output must remain inside the repository build directory")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=OUTPUT.parent,
            prefix=".keikeu-context-",
            delete=False,
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(OUTPUT)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a bounded local text pack for an external coding model."
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help=(
            "repository-relative tracked file or directory; repeat as needed. "
            "Cold evidence is included only when named as an exact file"
        ),
    )
    parser.add_argument(
        "--max-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_BYTES,
        help=f"maximum output size (default: {DEFAULT_MAX_BYTES})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and list selected files without writing the pack",
    )
    args = parser.parse_args(argv)

    try:
        pack, paths, skipped = build_context_pack(args.path, args.max_bytes)
        if args.dry_run:
            print(f"dry run: {len(paths)} files, {len(pack)} bytes, skipped={skipped}")
            for path in paths:
                print(path)
        else:
            _write_atomic(pack)
            print(f"{OUTPUT.relative_to(ROOT)}: {len(paths)} files, {len(pack)} bytes")
    except ContextPackError as error:
        print(f"Context pack failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
