"""Standard-stream entry point for the keikeu JSONL sidecar."""

from __future__ import annotations

from pathlib import Path
import sys

from keikeu_bridge.local_state import STATE_PATH
from keikeu_bridge.protocol import JsonlDispatcher, run_jsonl
from keikeu_bridge.service import KeikeuService

CONFIG_PATH = Path.home() / ".keikeu_config.json"


def main() -> int:
    service = KeikeuService(
        config_path=CONFIG_PATH,
        state_path=STATE_PATH,
    )
    return run_jsonl(
        JsonlDispatcher(service),
        sys.stdin,
        sys.stdout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
