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
    UploadObject,
    build_release_uploads,
    discover_release_artifacts,
    install_object_key,
    load_publish_config,
    load_release_version,
    upload_object,
)

DEFAULT_ARTIFACT_DIR = ROOT_DIR / "dist" / "runtime-build" / "release-artifacts"
DEFAULT_CONFIG_FILE = Path("/Users/zhutao/.munk-release/cloudflare-r2.env")
DEFAULT_INSTALL_SCRIPT = ROOT_DIR / "scripts" / "install.sh"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish Munk runtime release artifacts to Cloudflare R2.")
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--config-file", type=Path, default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--channel", default=None)
    parser.add_argument("--install-script", type=Path, default=DEFAULT_INSTALL_SCRIPT)
    parser.add_argument("--skip-install-script", action="store_true")
    parser.add_argument("--only-install-script", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_publish_config(args.config_file.resolve())
    channel = args.channel or config.channel
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
    install_script_path = args.install_script.resolve()
    if args.only_install_script and args.skip_install_script:
        raise RuntimeError("--only-install-script cannot be used together with --skip-install-script")

    installer_body = None
    if not args.skip_install_script:
        if not install_script_path.exists():
            raise RuntimeError(f"install script does not exist: {install_script_path}")
        installer_body = install_script_path.read_bytes()

    print(f"channel: {config.channel}")

    if args.only_install_script:
        assert installer_body is not None
        install_key = install_object_key(prefix=config.normalized_prefix)
        print(f"install script only: {install_script_path}")
        if args.dry_run:
            print("dry-run upload plan:")
            print(f"  - {install_key} ({len(installer_body)} bytes)")
            return 0
        print(f"uploading: {install_key}")
        upload_object(
            config=config,
            upload=UploadObject(
                key=install_key,
                body=installer_body,
                content_type="text/x-shellscript; charset=utf-8",
                cache_control="no-cache",
            ),
        )
        print("install script published successfully")
        return 0

    version = load_release_version(ROOT_DIR)
    artifacts = discover_release_artifacts(artifact_dir=args.artifact_dir.resolve(), version=version)
    uploads = build_release_uploads(
        config=config,
        version=version,
        artifacts=artifacts,
        installer_body=installer_body,
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
