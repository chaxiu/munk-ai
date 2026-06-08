#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import install_real_device_wda  # noqa: E402
import install_simulator_wda  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Thin dispatcher for simulator / real-device WDA installers.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--simulator-udid", help="Booted iOS Simulator UDID.")
    group.add_argument("--device-udid", help="Connected iOS real-device UDID.")
    return parser


def main(argv: list[str] | None = None) -> int:
    raw_args = argv if argv is not None else sys.argv[1:]
    parsed, _ = build_parser().parse_known_args(raw_args)
    if parsed.simulator_udid is not None:
        return install_simulator_wda.main(raw_args)
    return install_real_device_wda.main(raw_args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
