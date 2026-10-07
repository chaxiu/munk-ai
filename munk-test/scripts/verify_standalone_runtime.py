#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from munk.runtime_distribution import (  # noqa: E402
    load_runtime_manifest,
    validate_runtime_manifest_contract,
)

DEFAULT_RUNTIME_ROOT = ROOT_DIR / "dist" / "runtime"
DEFAULT_REVIEW_FIXTURE = ROOT_DIR / "tests" / "reviewing" / "fixtures" / "android-review-request.json"
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the assembled standalone runtime.")
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--review-request", type=Path, default=DEFAULT_REVIEW_FIXTURE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_root = args.runtime_root.resolve()
    launcher = runtime_root / "bin" / "munk"
    if not launcher.exists():
        raise RuntimeError(f"standalone launcher not found: {launcher}")
    manifest_path = runtime_root / "manifest.lock"
    if not manifest_path.exists():
        raise RuntimeError(f"standalone manifest not found: {manifest_path}")
    manifest = load_runtime_manifest(manifest_path)
    manifest_errors = validate_runtime_manifest_contract(runtime_root, manifest)
    if manifest_errors:
        raise RuntimeError("runtime manifest contract validation failed:\n" + "\n".join(manifest_errors))
    with tempfile.TemporaryDirectory(prefix="munk-runtime-verify-") as temp_dir:
        temp_root = Path(temp_dir)
        annotate_input = temp_root / "annotate-input.png"
        annotate_output = temp_root / "annotate-output.png"
        annotate_input.write_bytes(_build_one_by_one_png())
        _run([str(launcher), "doctor"], cwd=temp_root)
        _run(
            [
                str(launcher),
                "annotate",
                str(annotate_input),
                "--output",
                str(annotate_output),
            ],
            cwd=temp_root,
        )
        review_config = args.config or _config_from_env()
        if review_config is None:
            raise RuntimeError("review verification requires --config or MUNK_CONFIG")
        _run(
            [
                str(launcher),
                "review",
                "--request-file",
                str(args.review_request.resolve()),
                "--config",
                str(review_config.resolve()),
                "--json",
            ],
            cwd=temp_root,
        )
    print(f"standalone runtime verification passed: {launcher}")
    return 0


def _config_from_env() -> Path | None:
    raw = os.environ.get("MUNK_CONFIG")
    return Path(raw).expanduser() if raw else None


def _build_one_by_one_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    width = height = 1
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanline = b"\x00\xff\xff\xff"
    idat = zlib.compress(scanline)
    return b"".join(
        [
            signature,
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", idat),
            _png_chunk(b"IEND", b""),
        ]
    )


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return b"".join(
        [
            struct.pack("!I", len(payload)),
            tag,
            payload,
            struct.pack("!I", zlib.crc32(tag + payload) & 0xFFFFFFFF),
        ]
    )


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, check=True, cwd=cwd)


if __name__ == "__main__":
    raise SystemExit(main())
