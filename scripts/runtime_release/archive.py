from __future__ import annotations

import argparse
import json
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from munk.runtime_distribution import RuntimeVersionDefaults

from runtime_release.signing import (
    KeychainSession,
    NotarizationResult,
    ReleaseSigningConfig,
    _cleanup_signing_keychain,
    _codesign_runtime,
    _load_release_signing_config,
    _notarize_archive,
    _prepare_signing_keychain,
    _run_subprocess,
    _verify_codesign,
    _verify_notarized_targets,
)

ROOT_DIR = Path(__file__).resolve().parents[2]


class ReleaseMetadata(TypedDict):
    generated_at: str
    runtime_root: str
    archive_path: str | None
    archive_name: str | None
    archive_created: bool
    metadata_path: str
    manifest_path: str
    platform: str
    arch: str
    variant: str
    team_id: str | None
    bundle_id: str | None
    signing_identity: str | None
    signing_enabled: bool
    notarization_enabled: bool
    signed_target_count: int
    signed_targets: list[str]
    notarization_status: str | None
    notarization_submission_id: str | None
    notarized_at: str | None


def _finalize_release_artifacts(
    *,
    runtime_root: Path,
    runtime_python: Path,
    adb_path: Path,
    manifest_path: Path,
    runtime_defaults: RuntimeVersionDefaults,
    args: argparse.Namespace,
    variant: str,
    target_platform: str,
    target_arch: str,
    archive_name_override: str | None = None,
) -> ReleaseMetadata:
    archive_name = _resolve_archive_name(
        archive_name=archive_name_override if archive_name_override is not None else args.archive_name,
        variant=variant,
        runtime_defaults=runtime_defaults,
        platform_name=target_platform,
        arch=target_arch,
    )
    archive_path: Path | None = None
    keychain_session: KeychainSession | None = None
    signing_config: ReleaseSigningConfig | None = None
    signed_targets: list[Path] = []
    notarization_result: NotarizationResult | None = None
    signing_enabled = target_platform == "macos" and not args.skip_sign
    notarization_enabled = target_platform == "macos" and not args.skip_notarize
    if signing_enabled or notarization_enabled:
        signing_config = _load_release_signing_config(args.signing_env_file)
    try:
        if signing_config is not None and signing_enabled:
            keychain_session = _prepare_signing_keychain(signing_config)
            keychain_path = keychain_session.path if keychain_session is not None else None
            signed_targets = _codesign_runtime(
                runtime_root=runtime_root,
                signing_config=signing_config,
                keychain_path=keychain_path,
            )
            _verify_codesign(signed_targets)
        if not args.skip_archive:
            archive_path = _package_runtime_archive(
                runtime_root=runtime_root,
                archive_dir=args.archive_dir.resolve(),
                archive_name=archive_name,
                platform_name=target_platform,
            )
        if signing_config is not None and notarization_enabled:
            if archive_path is None:
                raise RuntimeError("archive path is missing; notarization requires a ZIP archive")
            notarization_result = _notarize_archive(archive_path=archive_path, signing_config=signing_config)
            _verify_notarized_targets([runtime_python, adb_path])
    finally:
        if keychain_session is not None:
            _cleanup_signing_keychain(keychain_session)
    return _write_release_metadata(
        archive_dir=args.archive_dir.resolve(),
        archive_name=archive_name,
        runtime_root=runtime_root,
        archive_path=archive_path,
        manifest_path=manifest_path,
        variant=variant,
        platform_name=target_platform,
        arch=target_arch,
        signing_config=signing_config,
        signed_targets=signed_targets,
        notarization_result=notarization_result,
        signing_enabled=signing_enabled,
        notarization_enabled=notarization_enabled,
    )


def _resolve_archive_name(
    *,
    archive_name: str | None,
    variant: str,
    runtime_defaults: RuntimeVersionDefaults,
    platform_name: str,
    arch: str,
) -> str:
    if archive_name is not None and archive_name.strip():
        stem = archive_name.strip()
    else:
        stem = f"munk-{platform_name}-{arch}-{variant}-{runtime_defaults.release_tag}"
    if stem.endswith(".tar.gz"):
        return stem[:-7]
    return stem[:-4] if stem.endswith(".zip") else stem


def _package_runtime_archive(
    *,
    runtime_root: Path,
    archive_dir: Path,
    archive_name: str,
    platform_name: str,
) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_suffix = ".tar.gz" if platform_name == "linux" else ".zip"
    archive_path = archive_dir / f"{archive_name}{archive_suffix}"
    archive_path.unlink(missing_ok=True)
    if platform_name == "macos":
        _run_subprocess(
            ["ditto", "-c", "-k", "--keepParent", str(runtime_root), str(archive_path)],
            cwd=runtime_root.parent,
        )
        return archive_path
    if platform_name == "linux":
        with tarfile.open(archive_path, mode="w:gz", dereference=False) as archive:
            archive.add(runtime_root, arcname=runtime_root.name, recursive=True)
        return archive_path
    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        root_arcname = f"{runtime_root.name}/"
        archive.writestr(root_arcname, "")
        for candidate in sorted(runtime_root.rglob("*")):
            relative = candidate.relative_to(runtime_root).as_posix()
            arcname = f"{runtime_root.name}/{relative}"
            if candidate.is_dir():
                archive.writestr(f"{arcname}/", "")
                continue
            archive.write(candidate, arcname=arcname)
    return archive_path


def _write_release_metadata(
    *,
    archive_dir: Path,
    archive_name: str,
    runtime_root: Path,
    archive_path: Path | None,
    manifest_path: Path,
    variant: str,
    platform_name: str,
    arch: str,
    signing_config: ReleaseSigningConfig | None,
    signed_targets: list[Path],
    notarization_result: NotarizationResult | None,
    signing_enabled: bool,
    notarization_enabled: bool,
) -> ReleaseMetadata:
    archive_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = archive_dir / f"{archive_name}.release.json"
    notarized_at = (
        datetime.now(tz=timezone.utc).isoformat()
        if notarization_result is not None and notarization_result.get("status", "").lower() == "accepted"
        else None
    )
    metadata: ReleaseMetadata = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "runtime_root": str(runtime_root),
        "archive_path": str(archive_path) if archive_path is not None else None,
        "archive_name": archive_path.name if archive_path is not None else None,
        "archive_created": archive_path is not None,
        "metadata_path": str(metadata_path),
        "manifest_path": str(manifest_path),
        "platform": platform_name,
        "arch": arch,
        "variant": variant,
        "team_id": signing_config.team_id if signing_config is not None else None,
        "bundle_id": signing_config.bundle_id if signing_config is not None else None,
        "signing_identity": signing_config.signing_identity if signing_config is not None else None,
        "signing_enabled": signing_enabled,
        "notarization_enabled": notarization_enabled,
        "signed_target_count": len(signed_targets),
        "signed_targets": [str(path) for path in signed_targets],
        "notarization_status": notarization_result.get("status") if notarization_result is not None else None,
        "notarization_submission_id": (
            notarization_result.get("submission_id") if notarization_result is not None else None
        ),
        "notarized_at": notarized_at,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata
