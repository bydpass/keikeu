from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAURI_DIR = ROOT / "frontend" / "src-tauri"
BUILD_DIR = ROOT / "build" / "pyinstaller"


def _target_triple() -> str:
    completed = subprocess.run(
        ["rustc", "-Vv"],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in completed.stdout.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    raise RuntimeError("rustc -Vv did not report a host target")


def main() -> int:
    target = _target_triple()
    output_name = f"keikeu-sidecar-{target}"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        output_name,
        "--paths",
        str(ROOT / "src"),
        "--distpath",
        str(TAURI_DIR / "binaries"),
        "--workpath",
        str(BUILD_DIR / "work"),
        "--specpath",
        str(BUILD_DIR),
        str(ROOT / "scripts" / "sidecar_entry.py"),
    ]
    environment = os.environ.copy()
    environment["PYINSTALLER_CONFIG_DIR"] = str(BUILD_DIR / "cache")
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    print(TAURI_DIR / "binaries" / output_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
