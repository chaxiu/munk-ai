#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from munk.runtime_distribution.build_env import (  # noqa: E402
    ADB_VERSION_MARKER_FILE,
    install_android_platform_tools,
    load_android_platform_tools_pin,
    resolve_android_platform_tools_target_platform,
)

RUNTIME_VERSION_CONFIG = ROOT_DIR / "config" / "build" / "runtime-version.json"
DEFAULT_DOWNLOAD_DIR = ROOT_DIR / "dist" / "runtime-build" / "downloads"
DEFAULT_DESTINATION_ROOT = ROOT_DIR / "android-adb"
ADB_VERSION_MARKER = ADB_VERSION_MARKER_FILE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download pinned Android SDK Platform-Tools from Google.")
    parser.add_argument(
        "--version-config",
        type=Path,
        default=RUNTIME_VERSION_CONFIG,
        help="Path to the runtime version config containing android_platform_tools pins.",
    )
    parser.add_argument(
        "--platform",
        choices=("auto", "macos", "linux", "windows"),
        default="auto",
        help="Target host platform archive to download.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=DEFAULT_DOWNLOAD_DIR,
        help="Directory used to cache downloaded archives.",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=DEFAULT_DESTINATION_ROOT,
        help="Root directory where platform-specific android-adb assets will be extracted.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and re-extract even if the requested version is already present.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested_platform = resolve_target_platform(args.platform)
    pin = load_android_platform_tools_pin(config_path=args.version_config.resolve(), target_platform=requested_platform)
    installed_adb = install_android_platform_tools(
        pin=pin,
        target_platform=requested_platform,
        download_dir=args.download_dir.resolve(),
        destination_root=args.destination_root.resolve(),
        force=args.force,
    )
    print(f"android platform-tools version: {pin.version}")
    print(f"platform: {requested_platform}")
    print(f"archive: {pin.url}")
    print(f"adb: {installed_adb}")
    return 0
def resolve_target_platform(requested: str) -> str:
    return resolve_android_platform_tools_target_platform(requested)


if __name__ == "__main__":
    raise SystemExit(main())
