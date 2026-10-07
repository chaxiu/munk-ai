#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
SRC_DIR = ROOT_DIR / "src"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from runtime_release.assembly import (  # noqa: E402
    DEFAULT_BUILD_CONFIG,
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_RELEASE_ARTIFACT_DIR,
    DEFAULT_RUNTIME_ROOT,
    DEFAULT_SIGNING_ENV_FILE,
    DEFAULT_WHEEL_BUILD_DIR,
    _assemble_release_target,
    _notarize_release_target,
    _resolve_release_build_targets,
    _should_run_notarization_recovery,
    _validate_release_args,
)
from runtime_release.signing import (  # noqa: E402
    DEFAULT_NOTARIZE_POLL_INTERVAL_SECONDS,
    DEFAULT_NOTARIZE_UPLOAD_ATTEMPTS,
    DEFAULT_NOTARIZE_WAIT_SECONDS,
)

from munk.runtime_distribution import ensure_pnpm_available, ensure_supported_platform  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble and notarize a PBS standalone runtime for Munk AI.")
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=DEFAULT_RUNTIME_ROOT,
        help="Release runtime root. Defaults to the canonical dist/runtime-release slot.",
    )
    parser.add_argument("--wheel-dir", type=Path, default=DEFAULT_WHEEL_BUILD_DIR)
    parser.add_argument("--download-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_RELEASE_ARTIFACT_DIR)
    parser.add_argument("--archive-name", default=None)
    parser.add_argument("--signing-env-file", type=Path, default=DEFAULT_SIGNING_ENV_FILE)
    parser.add_argument("--build-config", type=Path, default=DEFAULT_BUILD_CONFIG)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--enable-cython",
        action="store_true",
        help="Build perception compiled extensions (.so) instead of the default pure-Python wheel.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-sign", action="store_true")
    parser.add_argument("--skip-archive", action="store_true")
    parser.add_argument("--skip-notarize", action="store_true")
    parser.add_argument(
        "--notarize-only",
        action="store_true",
        help="Skip rebuild/sign/archive and notarize an existing release archive.",
    )
    parser.add_argument(
        "--resume-submission",
        default=None,
        help="Resume polling an existing notarytool submission id without re-uploading.",
    )
    parser.add_argument(
        "--notarize-wait-seconds",
        type=float,
        default=DEFAULT_NOTARIZE_WAIT_SECONDS,
        help="Soft timeout while polling Apple notarization status. The submission keeps processing.",
    )
    parser.add_argument(
        "--notarize-poll-interval-seconds",
        type=float,
        default=DEFAULT_NOTARIZE_POLL_INTERVAL_SECONDS,
        help="How often to poll notarytool info while waiting.",
    )
    parser.add_argument(
        "--notarize-upload-attempts",
        type=int,
        default=DEFAULT_NOTARIZE_UPLOAD_ATTEMPTS,
        help="Retry count for transient notarytool upload failures such as abortedUpload.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host_target = ensure_supported_platform()
    _validate_release_args(args, platform_name=host_target.platform)
    targets = _resolve_release_build_targets(args)
    if _should_run_notarization_recovery(args):
        for target in targets:
            _notarize_release_target(args=args, target=target, host_target=host_target)
        return 0
    if not args.skip_build:
        pnpm_bin = ensure_pnpm_available()
        _generate_contracts(pnpm_bin=pnpm_bin)
    for target in targets:
        _assemble_release_target(args=args, target=target, host_target=host_target)
    return 0


def _generate_contracts(*, pnpm_bin: str) -> None:
    subprocess.run(  # noqa: S603
        [pnpm_bin, "run", "generate:contracts"],
        cwd=ROOT_DIR,
        check=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
