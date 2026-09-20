"""Standard-stream entry point for the keikeu JSONL sidecar."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from keikeu_bridge.local_state import STATE_PATH
from keikeu_bridge.protocol import JsonlDispatcher, run_jsonl
from keikeu_bridge.service import KeikeuService
from keikeu_core.vault import require_home_path

CONFIG_PATH = Path.home() / ".keikeu_config.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-directory", type=Path)
    args = parser.parse_args(argv)
    config_path, state_path = CONFIG_PATH, STATE_PATH
    if args.state_directory is not None:
        directory = require_home_path(args.state_directory)
        config_path = directory / "desktop-config.json"
        state_path = directory / "desktop-state.json"
    service = KeikeuService(config_path=config_path, state_path=state_path)
    return run_jsonl(
        JsonlDispatcher(service),
        sys.stdin,
        sys.stdout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
