#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from munk.runtime_distribution.release_publish import (  # noqa: E402
    build_installer_uploads,
    build_release_uploads,
    discover_release_artifacts,
    load_publish_config,
    load_release_version,
    normalize_release_channel,
    upload_object,
    validate_release_channel_version,
)

DEFAULT_ARTIFACT_DIR = ROOT_DIR / "dist" / "runtime-build" / "release-artifacts"
DEFAULT_CONFIG_FILE = Path("/Users/zhutao/.munk-release/cloudflare-r2.env")
DEFAULT_INSTALL_SCRIPT = ROOT_DIR / "scripts" / "install.sh"
DEFAULT_INSTALL_PS1_SCRIPT = ROOT_DIR / "scripts" / "install.ps1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish Munk runtime release artifacts to Cloudflare R2.")
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--config-file", type=Path, default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--channel", default=None)
    parser.add_argument("--install-script", type=Path, default=DEFAULT_INSTALL_SCRIPT)
    parser.add_argument("--install-ps1-script", type=Path, default=DEFAULT_INSTALL_PS1_SCRIPT)
    parser.add_argument("--skip-install-script", action="store_true")
    parser.add_argument("--only-install-script", action="store_true")
    parser.add_argument(
        "--allow-channel-version-mismatch",
        action="store_true",
        help="Allow publishing a final version to beta or a pre-release version to stable.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _load_installer_bodies(args: argparse.Namespace) -> tuple[bytes | None, bytes | None]:
    if args.skip_install_script:
        return None, None

    install_script_path = args.install_script.resolve()
    install_ps1_script_path = args.install_ps1_script.resolve()
    if not install_script_path.exists():
        raise RuntimeError(f"install script does not exist: {install_script_path}")
    if not install_ps1_script_path.exists():
        raise RuntimeError(f"install.ps1 script does not exist: {install_ps1_script_path}")
    return install_script_path.read_bytes(), install_ps1_script_path.read_bytes()


def main() -> int:
    args = parse_args()
    config = load_publish_config(args.config_file.resolve())
    channel = normalize_release_channel(args.channel or config.channel)
    if not channel:
        raise RuntimeError("release channel must not be empty")
    config = config.__class__(
        account_id=config.account_id,
        access_key_id=config.access_key_id,
        secret_access_key=config.secret_access_key,
        bucket_name=config.bucket_name,
        public_base_url=config.public_base_url,
        region=config.region,
        channel=channel,
        prefix=config.prefix,
    )
    if args.only_install_script and args.skip_install_script:
        raise RuntimeError("--only-install-script cannot be used together with --skip-install-script")

    installer_body, installer_ps1_body = _load_installer_bodies(args)
    print(f"channel: {config.channel}")

    if args.only_install_script:
        uploads = build_installer_uploads(
            prefix=config.normalized_prefix,
            installer_body=installer_body,
            installer_ps1_body=installer_ps1_body,
        )
        print(f"install scripts only: {args.install_script} + {args.install_ps1_script}")
        if args.dry_run:
            print("dry-run upload plan:")
            for upload in uploads:
                print(f"  - {upload.key} ({len(upload.body)} bytes)")
            return 0
        for upload in uploads:
            print(f"uploading: {upload.key}")
            upload_object(config=config, upload=upload)
        print("install scripts published successfully")
        return 0

    version = load_release_version(ROOT_DIR)
    validate_release_channel_version(
        channel=config.channel,
        version=version,
        allow_mismatch=args.allow_channel_version_mismatch,
    )
    artifacts = discover_release_artifacts(artifact_dir=args.artifact_dir.resolve(), version=version)
    uploads = build_release_uploads(
        config=config,
        version=version,
        artifacts=artifacts,
        installer_body=installer_body,
        installer_ps1_body=installer_ps1_body,
    )
    print(f"release version: {version}")
    print(f"artifact count: {len(artifacts)}")
    for artifact in artifacts:
        print(
            "artifact: "
            f"platform={artifact.platform} arch={artifact.arch} variant={artifact.variant} "
            f"archive={artifact.archive_path}"
        )
    if args.dry_run:
        print("dry-run upload plan:")
        for upload in uploads:
            print(f"  - {upload.key} ({len(upload.body)} bytes)")
        return 0
    for upload in uploads:
        print(f"uploading: {upload.key}")
        upload_object(config=config, upload=upload)
    print("release artifacts published successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
