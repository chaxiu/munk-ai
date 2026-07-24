from __future__ import annotations

import argparse
import json
import tarfile
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from runtime_release.signing import (
    DEFAULT_NOTARIZE_POLL_INTERVAL_SECONDS,
    DEFAULT_NOTARIZE_UPLOAD_ATTEMPTS,
    DEFAULT_NOTARIZE_WAIT_SECONDS,
    KeychainSession,
    NotarizationResult,
    NotarizationTimedOutError,
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

from munk.runtime_distribution import RuntimeVersionDefaults, find_runtime_python

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
    archive_dir = args.archive_dir.resolve()
    state: dict[str, Any] = {
        "archive_path": None,
        "signed_targets": [],
        "notarization_result": None,
    }
    keychain_session: KeychainSession | None = None
    signing_config: ReleaseSigningConfig | None = None
    signing_enabled = target_platform == "macos" and not args.skip_sign
    notarization_enabled = target_platform == "macos" and not args.skip_notarize
    if signing_enabled or notarization_enabled:
        signing_config = _load_release_signing_config(args.signing_env_file)

    def write_metadata() -> ReleaseMetadata:
        return _write_release_metadata(
            archive_dir=archive_dir,
            archive_name=archive_name,
            runtime_root=runtime_root,
            archive_path=state["archive_path"],
            manifest_path=manifest_path,
            variant=variant,
            platform_name=target_platform,
            arch=target_arch,
            signing_config=signing_config,
            signed_targets=list(state["signed_targets"]),
            notarization_result=state["notarization_result"],
            signing_enabled=signing_enabled,
            notarization_enabled=notarization_enabled,
        )

    try:
        if signing_config is not None and signing_enabled:
            keychain_session = _prepare_signing_keychain(signing_config)
            keychain_path = keychain_session.path if keychain_session is not None else None
            state["signed_targets"] = _codesign_runtime(
                runtime_root=runtime_root,
                signing_config=signing_config,
                keychain_path=keychain_path,
            )
            _verify_codesign(state["signed_targets"])
        if not args.skip_archive:
            state["archive_path"] = _package_runtime_archive(
                runtime_root=runtime_root,
                archive_dir=archive_dir,
                archive_name=archive_name,
                platform_name=target_platform,
            )
            write_metadata()
        if signing_config is not None and notarization_enabled:
            state["archive_path"] = _require_archive_path(
                archive_path=state["archive_path"],
                archive_dir=archive_dir,
                archive_name=archive_name,
                platform_name=target_platform,
            )
            state["notarization_result"] = _notarize_with_metadata_checkpoint(
                archive_path=state["archive_path"],
                signing_config=signing_config,
                args=args,
                resume_submission_id=_explicit_resume_submission_id(args),
                state=state,
                write_metadata=write_metadata,
            )
            _verify_notarized_targets([runtime_python, adb_path])
    finally:
        if keychain_session is not None:
            _cleanup_signing_keychain(keychain_session)
    return write_metadata()


def _finalize_notarization_only(
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
    if target_platform != "macos":
        raise RuntimeError("notarization recovery is only supported on macOS")
    archive_name = _resolve_archive_name(
        archive_name=archive_name_override if archive_name_override is not None else args.archive_name,
        variant=variant,
        runtime_defaults=runtime_defaults,
        platform_name=target_platform,
        arch=target_arch,
    )
    archive_dir = args.archive_dir.resolve()
    metadata_path = archive_dir / f"{archive_name}.release.json"
    existing_metadata = _load_release_metadata(metadata_path)
    archive_path = _resolve_recovery_archive_path(
        archive_dir=archive_dir,
        archive_name=archive_name,
        existing_metadata=existing_metadata,
    )
    resume_submission_id = _explicit_resume_submission_id(args)
    if resume_submission_id is None:
        _maybe_print_pending_submission_hint(existing_metadata)
    signing_config = _load_release_signing_config(args.signing_env_file)
    resolved_manifest = (
        manifest_path
        if manifest_path.exists()
        else _manifest_path_from_metadata(existing_metadata, runtime_root=runtime_root)
    )
    state: dict[str, Any] = {
        "archive_path": archive_path,
        "signed_targets": _signed_targets_from_metadata(existing_metadata),
        "notarization_result": None,
    }

    def write_metadata() -> ReleaseMetadata:
        return _write_release_metadata(
            archive_dir=archive_dir,
            archive_name=archive_name,
            runtime_root=runtime_root,
            archive_path=state["archive_path"],
            manifest_path=resolved_manifest,
            variant=variant,
            platform_name=target_platform,
            arch=target_arch,
            signing_config=signing_config,
            signed_targets=list(state["signed_targets"]),
            notarization_result=state["notarization_result"],
            signing_enabled=True,
            notarization_enabled=True,
        )

    write_metadata()
    state["notarization_result"] = _notarize_with_metadata_checkpoint(
        archive_path=archive_path,
        signing_config=signing_config,
        args=args,
        resume_submission_id=resume_submission_id,
        state=state,
        write_metadata=write_metadata,
    )
    _verify_notarized_targets([runtime_python, adb_path])
    return write_metadata()


def _notarize_with_metadata_checkpoint(
    *,
    archive_path: Path,
    signing_config: ReleaseSigningConfig,
    args: argparse.Namespace,
    resume_submission_id: str | None,
    state: dict[str, Any],
    write_metadata: Callable[[], ReleaseMetadata],
) -> NotarizationResult:
    def on_submission(submission_id: str) -> None:
        state["notarization_result"] = NotarizationResult(
            submission_id=submission_id,
            status="In Progress",
        )
        write_metadata()

    try:
        return _notarize_archive(
            archive_path=archive_path,
            signing_config=signing_config,
            resume_submission_id=resume_submission_id,
            upload_attempts=_int_arg(args, "notarize_upload_attempts", DEFAULT_NOTARIZE_UPLOAD_ATTEMPTS),
            poll_interval_seconds=_float_arg(
                args,
                "notarize_poll_interval_seconds",
                DEFAULT_NOTARIZE_POLL_INTERVAL_SECONDS,
            ),
            wait_seconds=_float_arg(args, "notarize_wait_seconds", DEFAULT_NOTARIZE_WAIT_SECONDS),
            on_submission=on_submission,
        )
    except NotarizationTimedOutError as exc:
        state["notarization_result"] = NotarizationResult(
            submission_id=exc.submission_id,
            status="Timed Out",
            message=str(exc),
        )
        write_metadata()
        raise


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


def _load_release_metadata(metadata_path: Path) -> dict[str, Any] | None:
    if not metadata_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid release metadata JSON: {metadata_path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"release metadata must be a JSON object: {metadata_path}")
    return payload


def _require_archive_path(
    *,
    archive_path: Path | None,
    archive_dir: Path,
    archive_name: str,
    platform_name: str,
) -> Path:
    if archive_path is not None:
        if not archive_path.is_file():
            raise RuntimeError(f"archive path is missing; notarization requires a ZIP archive: {archive_path}")
        return archive_path
    suffix = ".tar.gz" if platform_name == "linux" else ".zip"
    candidate = archive_dir / f"{archive_name}{suffix}"
    if not candidate.is_file():
        raise RuntimeError(f"archive path is missing; notarization requires a ZIP archive: {candidate}")
    return candidate


def _resolve_recovery_archive_path(
    *,
    archive_dir: Path,
    archive_name: str,
    existing_metadata: dict[str, Any] | None,
) -> Path:
    if existing_metadata is not None:
        raw_archive_path = existing_metadata.get("archive_path")
        if isinstance(raw_archive_path, str) and raw_archive_path.strip():
            candidate = Path(raw_archive_path).expanduser().resolve()
            if candidate.is_file():
                return candidate
    candidate = archive_dir / f"{archive_name}.zip"
    if not candidate.is_file():
        raise RuntimeError(
            "archive not found for notarization recovery.\n"
            f"expected: {candidate}\n"
            "re-run a full assemble, or pass matching --archive-dir/--archive-name."
        )
    return candidate


def _explicit_resume_submission_id(args: argparse.Namespace) -> str | None:
    raw_resume = getattr(args, "resume_submission", None)
    if isinstance(raw_resume, str) and raw_resume.strip():
        return raw_resume.strip()
    return None


def _maybe_print_pending_submission_hint(existing_metadata: dict[str, Any] | None) -> None:
    if existing_metadata is None:
        return
    submission_id = existing_metadata.get("notarization_submission_id")
    status = str(existing_metadata.get("notarization_status") or "").strip().lower()
    if not isinstance(submission_id, str) or not submission_id.strip():
        return
    if status == "accepted":
        return
    print(
        "note: release metadata already has "
        f"submission_id={submission_id.strip()} status={existing_metadata.get('notarization_status')!r}; "
        "pass --resume-submission to avoid re-uploading."
    )


def _signed_targets_from_metadata(existing_metadata: dict[str, Any] | None) -> list[Path]:
    if existing_metadata is None:
        return []
    raw_targets = existing_metadata.get("signed_targets")
    if not isinstance(raw_targets, list):
        return []
    paths: list[Path] = []
    for item in raw_targets:
        if isinstance(item, str) and item.strip():
            paths.append(Path(item))
    return paths


def _manifest_path_from_metadata(
    existing_metadata: dict[str, Any] | None,
    *,
    runtime_root: Path,
) -> Path:
    if existing_metadata is not None:
        raw_manifest = existing_metadata.get("manifest_path")
        if isinstance(raw_manifest, str) and raw_manifest.strip():
            return Path(raw_manifest)
    return runtime_root / "manifest.lock"


def _int_arg(args: argparse.Namespace, name: str, default: int) -> int:
    value = getattr(args, name, default)
    if value is None:
        return default
    return int(value)


def _float_arg(args: argparse.Namespace, name: str, default: float) -> float:
    value = getattr(args, name, default)
    if value is None:
        return default
    return float(value)


def resolve_runtime_python_for_recovery(runtime_root: Path) -> Path:
    return find_runtime_python(runtime_root / "python")
