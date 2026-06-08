#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, cast

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from munk.runtime_distribution import (  # noqa: E402
    DependencyProject,
    InstalledDistributionDescriptor,
    RuntimeVersionDefaults,
    build_distribution_layer_map,
    build_runtime_data_dir_relpaths,
    build_runtime_manifest,
    clean_project_build_artifacts,
    copy_adb_sidecar,
    copy_recording_runtime_assets,
    default_state_path,
    ensure_supported_platform,
    ensure_uv_available,
    extract_pbs_archive,
    find_runtime_python,
    fingerprint_paths,
    flatten_workspace_projects,
    install_wheel_files,
    load_android_platform_tools_pin,
    load_runtime_version_defaults,
    load_state,
    normalized_arch,
    pbs_target_triple,
    prepare_recording_source_assets,
    recording_asset_fingerprint,
    recording_runtime_asset_relpaths,
    recording_runtime_assets_present,
    recording_source_assets_ready,
    resolve_pbs_archive,
    resolve_workspace_sections,
    run_command,
    run_uv_pip_check,
    sync_project_dependencies,
    verify_bundled_node_runtime,
    write_launcher,
    write_runtime_manifest,
    write_state,
)

RUNTIME_VERSION_CONFIG = ROOT_DIR / "config" / "build" / "runtime-version.json"
DEFAULT_RUNTIME_ROOT = ROOT_DIR / "dist" / "runtime-release"
DEFAULT_WHEEL_BUILD_DIR = ROOT_DIR / "dist" / "runtime-build" / "wheels"
DEFAULT_DOWNLOAD_DIR = ROOT_DIR / "dist" / "runtime-build" / "downloads"
DEFAULT_RELEASE_ARTIFACT_DIR = ROOT_DIR / "dist" / "runtime-build" / "release-artifacts"
DEFAULT_BUILD_CONFIG = ROOT_DIR / "config" / "build" / "build.yaml"
DEFAULT_NO_REVIEW_BUILD_CONFIG = ROOT_DIR / "config" / "build" / "build.no-review.yaml"
DEFAULT_SIGNING_ENV_FILE = Path("/Users/zhutao/.munk-release/secrets.env")
BUILD_REVIEW_KNOWLEDGE_SCRIPT = ROOT_DIR / "scripts" / "build_review_knowledge.py"
NODE_JIT_ENTITLEMENTS_PATH = ROOT_DIR / "scripts" / "node_jit_entitlements.plist"
MACHO_MAGIC_NUMBERS = {
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}
LOCAL_PROJECTS = flatten_workspace_projects(
    resolve_workspace_sections(build_config=DEFAULT_BUILD_CONFIG, project_root=ROOT_DIR)
)
LOCAL_DISTRIBUTIONS = [project.name for project in LOCAL_PROJECTS]
LOCAL_DISTRIBUTION_LAYERS = build_distribution_layer_map()


class RuntimeInspectionPayload(TypedDict):
    python_version: str
    site_packages: str
    installed_distributions: dict[str, str]


class NotarizationResult(TypedDict, total=False):
    submission_id: str
    status: str
    message: str
    raw_payload: dict[str, Any]


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


@dataclass(frozen=True)
class ReleaseSigningConfig:
    team_id: str
    bundle_id: str
    signing_identity: str
    asc_key_id: str
    asc_issuer_id: str
    asc_key_path: Path
    p12_path: Path | None = None
    p12_password: str | None = None


@dataclass(frozen=True)
class KeychainSession:
    path: Path
    password: str
    temp_dir: Path


@dataclass(frozen=True)
class ReleaseBuildTarget:
    variant: str
    build_config: Path
    runtime_root: Path
    archive_name: str | None = None


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _validate_release_args(args)
    targets = _resolve_release_build_targets(args)
    for target in targets:
        _assemble_release_target(args=args, target=target)
    return 0


def _assemble_release_target(*, args: argparse.Namespace, target: ReleaseBuildTarget) -> None:
    ensure_supported_platform()
    uv_bin = ensure_uv_available()
    runtime_defaults = load_runtime_version_defaults(RUNTIME_VERSION_CONFIG)
    build_config = target.build_config.resolve()
    workspace_sections = _resolve_workspace_sections(build_config)
    selected_projects = flatten_workspace_projects(workspace_sections)
    section_names = {section["name"] for section in workspace_sections}
    review_enabled = "review" in section_names
    recording_enabled = "recording" in section_names
    runtime_root = target.runtime_root.resolve()
    state_path = default_state_path(project_root=ROOT_DIR, kind="release", runtime_root=runtime_root)
    previous_state = load_state(state_path)
    dependency_fingerprint = _dependency_fingerprint(
        build_config=build_config,
        projects=selected_projects,
        variant=target.variant,
    )
    runtime_recording_asset_fingerprint = (
        recording_asset_fingerprint(project_root=ROOT_DIR) if recording_enabled else "disabled"
    )
    adb_pin = load_android_platform_tools_pin(config_path=RUNTIME_VERSION_CONFIG, target_platform="macos")
    wheel_build_fingerprint = _wheel_build_fingerprint(projects=selected_projects)

    if runtime_root.exists() and args.force:
        shutil.rmtree(runtime_root)
    python_root = runtime_root / "python"
    runtime_python_exists = python_root.exists() and any((python_root / "bin").glob("python*"))
    needs_runtime_refresh = args.force or not runtime_python_exists or previous_state is None
    if needs_runtime_refresh:
        _prepare_runtime_layout(runtime_root)
        pbs_archive = resolve_pbs_archive(download_dir=args.download_dir.resolve(), defaults=runtime_defaults)
        extract_pbs_archive(archive_path=pbs_archive, python_root=python_root, cwd=ROOT_DIR)
    else:
        _prepare_runtime_layout(runtime_root)
    runtime_python = find_runtime_python(python_root)

    wheel_dir = args.wheel_dir.resolve()
    needs_wheel_build = (
        not args.skip_build
        and (
            args.force
            or previous_state is None
            or previous_state.get("wheel_build_fingerprint") != wheel_build_fingerprint
            or not _has_all_wheels(wheel_dir, projects=selected_projects)
        )
    )
    if needs_wheel_build:
        build_local_wheels(
            wheel_dir,
            runtime_python=runtime_python,
            projects=selected_projects,
            clean_projects=args.force,
            enable_cython=args.enable_cython,
        )
    wheel_paths = _collect_wheel_files(wheel_dir, projects=selected_projects)

    needs_dependency_sync = (
        args.force
        or previous_state is None
        or previous_state.get("dependency_fingerprint") != dependency_fingerprint
        or needs_runtime_refresh
    )
    if needs_dependency_sync:
        for project in selected_projects:
            sync_project_dependencies(
                uv_bin=uv_bin,
                project_dir=project.project_dir,
                runtime_python=runtime_python,
                cwd=ROOT_DIR,
            )
    if needs_dependency_sync or needs_wheel_build or needs_runtime_refresh:
        install_wheel_files(
            uv_bin=uv_bin,
            runtime_python=runtime_python,
            wheel_paths=wheel_paths,
            cwd=ROOT_DIR,
        )
        if review_enabled:
            _refresh_review_knowledge(runtime_root=runtime_root, runtime_python=runtime_python)
        run_uv_pip_check(uv_bin=uv_bin, runtime_python=runtime_python, cwd=ROOT_DIR)

    copy_adb_sidecar(
        project_root=ROOT_DIR,
        runtime_root=runtime_root,
        download_dir=args.download_dir.resolve(),
        pin=adb_pin,
    )
    recording_assets: dict[str, str] | None = None
    if recording_enabled:
        needs_recording_source_prepare = (
            args.force
            or (
                previous_state is not None
                and previous_state.get("recording_asset_fingerprint") != runtime_recording_asset_fingerprint
            )
            or not recording_source_assets_ready(project_root=ROOT_DIR)
        )
        if needs_recording_source_prepare:
            prepare_recording_source_assets(
                project_root=ROOT_DIR,
                force=(
                    args.force
                    or (
                        previous_state is not None
                        and previous_state.get("recording_asset_fingerprint") != runtime_recording_asset_fingerprint
                    )
                ),
                cwd=ROOT_DIR,
            )
        needs_recording_runtime_refresh = (
            args.force
            or needs_runtime_refresh
            or previous_state is None
            or (
                previous_state is not None
                and previous_state.get("recording_asset_fingerprint") != runtime_recording_asset_fingerprint
            )
            or not recording_runtime_assets_present(runtime_root=runtime_root)
        )
        if needs_recording_runtime_refresh:
            recording_assets = copy_recording_runtime_assets(
                project_root=ROOT_DIR,
                runtime_root=runtime_root,
                download_dir=args.download_dir.resolve(),
            )
        else:
            recording_assets = recording_runtime_asset_relpaths(runtime_root=runtime_root)
        verify_bundled_node_runtime(
            runtime_root=runtime_root,
            forbidden_prefixes=("/opt/homebrew/", "/usr/local/opt/", str(ROOT_DIR)),
        )
    launcher_path = write_launcher(runtime_root=runtime_root, runtime_python=runtime_python)
    runtime_state = inspect_runtime_state(
        runtime_python,
        selected_distributions=[project.name for project in selected_projects],
    )
    manifest_path = runtime_root / "manifest.lock"
    manifest = build_runtime_manifest(
        platform="macos",
        arch=normalized_arch(),
        variant=target.variant,
        python_version=runtime_state["python_version"],
        pbs_release_tag=runtime_defaults.release_tag,
        pbs_archive_flavor=runtime_defaults.archive_flavor,
        pbs_target_triple=pbs_target_triple(),
        python_root_relpath="python",
        python_executable_relpath=os.path.relpath(runtime_python, runtime_root),
        site_packages_relpath=os.path.relpath(Path(runtime_state["site_packages"]), runtime_root),
        installed_distributions=_build_installed_distribution_descriptors(
            runtime_state,
            selected_distributions=[project.name for project in selected_projects],
        ),
        adb_relpath="sidecars/android-adb/platform-tools/adb",
        launcher_relpath="bin/munk",
        recording_ui_relpath=recording_assets["recording_ui_relpath"] if recording_assets is not None else None,
        recording_bridge_relpath=recording_assets["recording_bridge_relpath"] if recording_assets is not None else None,
        node_relpath=recording_assets["node_relpath"] if recording_assets is not None else None,
    )
    write_runtime_manifest(manifest_path, manifest)
    release_metadata = _finalize_release_artifacts(
        runtime_root=runtime_root,
        runtime_python=runtime_python,
        adb_path=runtime_root / "sidecars" / "android-adb" / "platform-tools" / "adb",
        manifest_path=manifest_path,
        runtime_defaults=runtime_defaults,
        args=args,
        variant=target.variant,
        archive_name_override=target.archive_name,
    )
    write_state(
        state_path,
        {
            "dependency_fingerprint": dependency_fingerprint,
            "recording_asset_fingerprint": runtime_recording_asset_fingerprint,
            "wheel_build_fingerprint": wheel_build_fingerprint,
            "runtime_root": str(runtime_root),
        },
    )
    print(f"runtime assembled at: {runtime_root}")
    print(f"launcher: {launcher_path}")
    print(f"manifest: {manifest_path}")
    if release_metadata["archive_path"]:
        print(f"archive: {release_metadata['archive_path']}")
    print(f"release metadata: {release_metadata['metadata_path']}")
    print(f"signed targets: {release_metadata['signed_target_count']}")
    if release_metadata["notarization_status"]:
        print(f"notarization: {release_metadata['notarization_status']}")


def _resolve_release_build_targets(args: argparse.Namespace) -> list[ReleaseBuildTarget]:
    if not args.all:
        return [
            ReleaseBuildTarget(
                variant=args.variant,
                build_config=args.build_config.resolve(),
                runtime_root=args.runtime_root.resolve(),
                archive_name=args.archive_name,
            )
        ]
    base_runtime_root = args.runtime_root.resolve()
    archive_name = args.archive_name.strip() if isinstance(args.archive_name, str) and args.archive_name.strip() else None
    return [
        ReleaseBuildTarget(
            variant="full",
            build_config=DEFAULT_BUILD_CONFIG.resolve(),
            runtime_root=base_runtime_root,
            archive_name=f"{archive_name}-full" if archive_name is not None else None,
        ),
        ReleaseBuildTarget(
            variant="no-review",
            build_config=DEFAULT_NO_REVIEW_BUILD_CONFIG.resolve(),
            runtime_root=_variant_runtime_root(base_runtime_root, variant="no-review"),
            archive_name=f"{archive_name}-no-review" if archive_name is not None else None,
        ),
    ]


def _variant_runtime_root(runtime_root: Path, *, variant: str) -> Path:
    return runtime_root.with_name(f"{runtime_root.name}-{variant}")


def build_local_wheels(
    wheel_dir: Path,
    *,
    runtime_python: Path,
    projects: list[DependencyProject] | None = None,
    clean_projects: bool = False,
    enable_cython: bool = False,
) -> None:
    if wheel_dir.exists():
        shutil.rmtree(wheel_dir)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    selected_projects = projects or LOCAL_PROJECTS
    for project in selected_projects:
        if clean_projects:
            preserved_paths = [wheel_dir]
            if project.project_dir == ROOT_DIR:
                preserved_paths.append(RUNTIME_VERSION_CONFIG)
            clean_project_build_artifacts(project.project_dir, preserve_paths=preserved_paths)
        _prepare_project_build_artifacts(project)
        run_command(
            [
                ensure_uv_available(),
                "run",
                "--python",
                str(runtime_python),
                "--no-project",
                "--with",
                "build>=1.2.2",
                "python",
                "-m",
                "build",
                "--wheel",
                "--outdir",
                str(wheel_dir),
                ".",
            ],
            cwd=project.project_dir,
            env=_project_build_env(project=project, enable_cython=enable_cython),
        )

def _validate_release_args(args: argparse.Namespace) -> None:
    if args.all:
        if args.variant != "full":
            raise RuntimeError("--all cannot be combined with a custom --variant; keep --variant as 'full'")
        if args.build_config.resolve() != DEFAULT_BUILD_CONFIG.resolve():
            raise RuntimeError("--all cannot be combined with --build-config; use the default config set")
    if args.skip_notarize and args.skip_archive:
        return
    if not args.skip_notarize and args.skip_sign:
        raise RuntimeError("cannot notarize an unsigned runtime; remove --skip-sign or add --skip-notarize")
    if not args.skip_notarize and args.skip_archive:
        raise RuntimeError("cannot notarize without an archive; remove --skip-archive or add --skip-notarize")


def _finalize_release_artifacts(
    *,
    runtime_root: Path,
    runtime_python: Path,
    adb_path: Path,
    manifest_path: Path,
    runtime_defaults: RuntimeVersionDefaults,
    args: argparse.Namespace,
    variant: str,
    archive_name_override: str | None = None,
) -> ReleaseMetadata:
    archive_name = _resolve_archive_name(
        archive_name=archive_name_override if archive_name_override is not None else args.archive_name,
        variant=variant,
        runtime_defaults=runtime_defaults,
    )
    archive_path: Path | None = None
    keychain_session: KeychainSession | None = None
    signing_config: ReleaseSigningConfig | None = None
    signed_targets: list[Path] = []
    notarization_result: NotarizationResult | None = None
    if not args.skip_sign or not args.skip_notarize:
        signing_config = _load_release_signing_config(args.signing_env_file)
    try:
        if signing_config is not None and not args.skip_sign:
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
            )
        if signing_config is not None and not args.skip_notarize:
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
        signing_config=signing_config,
        signed_targets=signed_targets,
        notarization_result=notarization_result,
        signing_enabled=not args.skip_sign,
        notarization_enabled=not args.skip_notarize,
    )


def _resolve_archive_name(
    *,
    archive_name: str | None,
    variant: str,
    runtime_defaults: RuntimeVersionDefaults,
) -> str:
    if archive_name is not None and archive_name.strip():
        stem = archive_name.strip()
    else:
        stem = f"munk-macos-{normalized_arch()}-{variant}-{runtime_defaults.release_tag}"
    return stem[:-4] if stem.endswith(".zip") else stem


def _parse_env_file(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        payload[key] = _strip_shell_quotes(value)
    return payload


def _strip_shell_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _load_release_signing_config(signing_env_file: Path) -> ReleaseSigningConfig:
    env_payload = dict(os.environ)
    if signing_env_file.exists():
        env_payload.update(_parse_env_file(signing_env_file))
    elif not _has_release_signing_env(env_payload):
        raise RuntimeError(f"missing signing env file: {signing_env_file}")
    return _validate_signing_config(env_payload, signing_env_file)


def _has_release_signing_env(payload: dict[str, str]) -> bool:
    required = {
        "TEAM_ID",
        "BUNDLE_ID",
        "SIGNING_IDENTITY",
        "ASC_KEY_ID",
        "ASC_ISSUER_ID",
        "ASC_KEY_PATH",
    }
    return required.issubset({key for key, value in payload.items() if value})


def _validate_signing_config(payload: dict[str, str], source_path: Path) -> ReleaseSigningConfig:
    required_keys = [
        "TEAM_ID",
        "BUNDLE_ID",
        "SIGNING_IDENTITY",
        "ASC_KEY_ID",
        "ASC_ISSUER_ID",
        "ASC_KEY_PATH",
    ]
    missing = [key for key in required_keys if not payload.get(key)]
    if missing:
        raise RuntimeError(f"missing signing settings in {source_path}: {', '.join(missing)}")
    asc_key_path = Path(payload["ASC_KEY_PATH"]).expanduser().resolve()
    if not asc_key_path.exists():
        raise RuntimeError(f"ASC_KEY_PATH does not exist: {asc_key_path}")
    p12_raw = payload.get("P12_PATH")
    p12_path = Path(p12_raw).expanduser().resolve() if p12_raw else None
    if p12_path is not None and not p12_path.exists():
        raise RuntimeError(f"P12_PATH does not exist: {p12_path}")
    p12_password = payload.get("P12_PASSWORD")
    if p12_path is not None and not p12_password:
        raise RuntimeError("P12_PASSWORD is required when P12_PATH is provided")
    return ReleaseSigningConfig(
        team_id=payload["TEAM_ID"],
        bundle_id=payload["BUNDLE_ID"],
        signing_identity=payload["SIGNING_IDENTITY"],
        asc_key_id=payload["ASC_KEY_ID"],
        asc_issuer_id=payload["ASC_ISSUER_ID"],
        asc_key_path=asc_key_path,
        p12_path=p12_path,
        p12_password=p12_password,
    )


def _prepare_signing_keychain(signing_config: ReleaseSigningConfig) -> KeychainSession | None:
    if _identity_exists(signing_config.signing_identity, keychain_path=None):
        return None
    if signing_config.p12_path is None or signing_config.p12_password is None:
        raise RuntimeError(
            "signing identity is not available in the current keychains and no P12 credentials were provided"
        )
    temp_dir = Path(tempfile.mkdtemp(prefix="munk-signing-keychain-"))
    keychain_path = temp_dir / "munk-signing.keychain-db"
    keychain_password = secrets.token_urlsafe(24)
    _run_subprocess(
        ["security", "create-keychain", "-p", keychain_password, str(keychain_path)],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        ["security", "set-keychain-settings", "-lut", "21600", str(keychain_path)],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        ["security", "unlock-keychain", "-p", keychain_password, str(keychain_path)],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        [
            "security",
            "import",
            str(signing_config.p12_path),
            "-k",
            str(keychain_path),
            "-P",
            signing_config.p12_password,
            "-T",
            "/usr/bin/codesign",
            "-T",
            "/usr/bin/security",
        ],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        [
            "security",
            "set-key-partition-list",
            "-S",
            "apple-tool:,apple:,codesign:",
            "-s",
            "-k",
            keychain_password,
            str(keychain_path),
        ],
        cwd=ROOT_DIR,
    )
    if not _identity_exists(signing_config.signing_identity, keychain_path=keychain_path):
        raise RuntimeError(f"imported keychain does not expose signing identity: {signing_config.signing_identity}")
    return KeychainSession(path=keychain_path, password=keychain_password, temp_dir=temp_dir)


def _cleanup_signing_keychain(session: KeychainSession) -> None:
    try:
        _run_subprocess(["security", "delete-keychain", str(session.path)], cwd=ROOT_DIR, check=False)
    finally:
        shutil.rmtree(session.temp_dir, ignore_errors=True)


def _identity_exists(signing_identity: str, *, keychain_path: Path | None) -> bool:
    command = ["security", "find-identity", "-v", "-p", "codesigning"]
    if keychain_path is not None:
        command.append(str(keychain_path))
    completed = _run_subprocess(command, cwd=ROOT_DIR, capture_output=True, check=False)
    output = f"{completed.stdout}\n{completed.stderr}"
    return signing_identity in output


def _iter_signable_macho_paths(runtime_root: Path) -> list[Path]:
    signable_paths: list[Path] = []
    for candidate in runtime_root.rglob("*"):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        if _is_macho_file(candidate):
            signable_paths.append(candidate)
    return _sort_signing_targets(signable_paths)


def _sort_signing_targets(paths: list[Path]) -> list[Path]:
    return sorted(
        paths,
        key=lambda path: (0 if path.suffix in {".so", ".dylib"} else 1, -len(path.parts), str(path)),
    )


def _is_macho_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            header = handle.read(4)
    except OSError:
        return False
    return header in MACHO_MAGIC_NUMBERS


def _codesign_runtime(
    *,
    runtime_root: Path,
    signing_config: ReleaseSigningConfig,
    keychain_path: Path | None,
) -> list[Path]:
    signed_targets: list[Path] = []
    for target_path in _iter_signable_macho_paths(runtime_root):
        _codesign_path(
            runtime_root=runtime_root,
            target_path=target_path,
            signing_config=signing_config,
            keychain_path=keychain_path,
        )
        signed_targets.append(target_path)
    return signed_targets


def _codesign_path(
    *,
    runtime_root: Path,
    target_path: Path,
    signing_config: ReleaseSigningConfig,
    keychain_path: Path | None,
) -> None:
    _run_subprocess(
        _build_codesign_command(
            runtime_root=runtime_root,
            target_path=target_path,
            signing_config=signing_config,
            keychain_path=keychain_path,
        ),
        cwd=ROOT_DIR,
    )


def _build_codesign_command(
    *,
    runtime_root: Path,
    target_path: Path,
    signing_config: ReleaseSigningConfig,
    keychain_path: Path | None,
) -> list[str]:
    uses_node_jit_entitlements = _requires_node_jit_entitlements(runtime_root=runtime_root, target_path=target_path)
    command = [
        "codesign",
        "--force",
        "--sign",
        signing_config.signing_identity,
        "--timestamp",
        "--options",
        "runtime",
        "--identifier",
        _signing_identifier_for_path(runtime_root=runtime_root, target_path=target_path, bundle_id=signing_config.bundle_id),
    ]
    if uses_node_jit_entitlements:
        command.extend(["--entitlements", str(NODE_JIT_ENTITLEMENTS_PATH)])
    if keychain_path is not None:
        command.extend(["--keychain", str(keychain_path)])
    command.append(str(target_path))
    return command


def _requires_node_jit_entitlements(*, runtime_root: Path, target_path: Path) -> bool:
    relative = target_path.relative_to(runtime_root)
    if relative.as_posix() == "sidecars/node/bin/node":
        return True
    return relative.parts[-4:] == ("site-packages", "playwright", "driver", "node")


def _signing_identifier_for_path(*, runtime_root: Path, target_path: Path, bundle_id: str) -> str:
    relative = target_path.relative_to(runtime_root)
    sanitized_parts = [_sanitize_identifier_part(part) for part in relative.parts]
    suffix = ".".join(part for part in sanitized_parts if part)
    return bundle_id if not suffix else f"{bundle_id}.{suffix}"


def _sanitize_identifier_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", value).strip(".-")


def _verify_codesign(signed_targets: list[Path]) -> None:
    for target_path in signed_targets:
        _run_subprocess(
            ["codesign", "--verify", "--strict", "--verbose=2", str(target_path)],
            cwd=ROOT_DIR,
        )


def _verify_notarized_targets(paths: list[Path]) -> None:
    seen_paths: set[Path] = set()
    for path in paths:
        target_path = path.resolve()
        if target_path in seen_paths:
            continue
        seen_paths.add(target_path)
        _run_subprocess(
            ["codesign", "--verify", "--strict", "--check-notarization", "--verbose=2", str(target_path)],
            cwd=ROOT_DIR,
        )


def _package_runtime_archive(*, runtime_root: Path, archive_dir: Path, archive_name: str) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{archive_name}.zip"
    archive_path.unlink(missing_ok=True)
    _run_subprocess(
        ["ditto", "-c", "-k", "--keepParent", str(runtime_root), str(archive_path)],
        cwd=runtime_root.parent,
    )
    return archive_path


def _notarize_archive(*, archive_path: Path, signing_config: ReleaseSigningConfig) -> NotarizationResult:
    command = _build_notarytool_command(archive_path=archive_path, signing_config=signing_config)
    completed = _run_subprocess(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "notarytool submit failed.\n"
            f"archive: {archive_path}\n"
            f"{_format_subprocess_failure(command=command, cwd=ROOT_DIR, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)}"
        )
    payload = json.loads(completed.stdout)
    status = str(payload.get("status", "")).strip()
    submission_id = str(payload.get("id", "")).strip()
    if not status:
        raise RuntimeError(f"notarytool returned an unexpected payload: {payload}")
    if status.lower() != "accepted":
        raise RuntimeError(f"notarization failed with status={status}, submission_id={submission_id or 'unknown'}")
    return NotarizationResult(
        submission_id=submission_id,
        status=status,
        message=str(payload.get("message", "")),
        raw_payload=payload,
    )


def _build_notarytool_command(*, archive_path: Path, signing_config: ReleaseSigningConfig) -> list[str]:
    return [
        "xcrun",
        "notarytool",
        "submit",
        str(archive_path),
        "--key",
        str(signing_config.asc_key_path),
        "--key-id",
        signing_config.asc_key_id,
        "--issuer",
        signing_config.asc_issuer_id,
        "--wait",
        "--output-format",
        "json",
    ]


def _write_release_metadata(
    *,
    archive_dir: Path,
    archive_name: str,
    runtime_root: Path,
    archive_path: Path | None,
    manifest_path: Path,
    variant: str,
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
        "platform": "macos",
        "arch": normalized_arch(),
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


def _run_subprocess(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            env=env,
            check=check,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            _format_subprocess_failure(
                command=list(exc.cmd) if isinstance(exc.cmd, (list, tuple)) else [str(exc.cmd)],
                cwd=cwd,
                returncode=exc.returncode,
                stdout=exc.stdout,
                stderr=exc.stderr,
            )
        ) from exc


def _format_subprocess_failure(
    *,
    command: list[str],
    cwd: Path,
    returncode: int,
    stdout: str | None,
    stderr: str | None,
) -> str:
    parts = [
        f"command failed with exit code {returncode}",
        f"cwd: {cwd}",
        f"command: {' '.join(command)}",
    ]
    stdout_text = (stdout or "").strip()
    stderr_text = (stderr or "").strip()
    if stdout_text:
        parts.append(f"stdout:\n{stdout_text}")
    if stderr_text:
        parts.append(f"stderr:\n{stderr_text}")
    return "\n".join(parts)


def _refresh_review_knowledge(*, runtime_root: Path, runtime_python: Path) -> None:
    env = os.environ.copy()
    env["MUNK_RUNTIME_ROOT"] = str(runtime_root)
    env["MUNK_RUNTIME_DATA_ROOT"] = str(runtime_root / "data")
    completed = _run_subprocess(
        [str(runtime_python), str(BUILD_REVIEW_KNOWLEDGE_SCRIPT)],
        cwd=ROOT_DIR,
        capture_output=True,
        env=env,
    )
    payload = json.loads(completed.stdout)
    print(
        "review knowledge refreshed: "
        f"rebuilt={payload['rebuilt_cases']} "
        f"skipped={payload['skipped_cases']} "
        f"db={payload['db_path']}"
    )


def inspect_runtime_state(
    runtime_python: Path,
    *,
    selected_distributions: list[str] | None = None,
) -> RuntimeInspectionPayload:
    targets = selected_distributions or LOCAL_DISTRIBUTIONS
    command = [
        str(runtime_python),
        "-c",
        (
            "import importlib.metadata as m, json, platform, sysconfig; "
            f"targets = {json.dumps(targets)}; "
            "print(json.dumps({"
            "'python_version': platform.python_version(), "
            "'site_packages': sysconfig.get_paths()['purelib'], "
            "'installed_distributions': {name: m.version(name) for name in targets}"
            "}))"
        ),
    ]
    completed = _run_subprocess(command, cwd=ROOT_DIR, capture_output=True)
    payload = json.loads(completed.stdout)
    python_version = payload.get("python_version")
    site_packages = payload.get("site_packages")
    raw_versions_obj = payload.get("installed_distributions")
    if not isinstance(python_version, str) or not python_version:
        raise RuntimeError("invalid runtime inspection payload: missing python_version")
    if not isinstance(site_packages, str) or not site_packages:
        raise RuntimeError("invalid runtime inspection payload: missing site_packages")
    if not isinstance(raw_versions_obj, dict):
        raise RuntimeError("invalid runtime inspection payload: missing installed_distributions")
    raw_versions = cast(dict[object, object], raw_versions_obj)
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in raw_versions.items()):
        raise RuntimeError("invalid runtime inspection payload: missing installed_distributions")
    installed_distributions = cast(dict[str, str], raw_versions)
    return RuntimeInspectionPayload(
        python_version=python_version,
        site_packages=site_packages,
        installed_distributions=installed_distributions,
    )


def _build_installed_distribution_descriptors(
    runtime_state: RuntimeInspectionPayload,
    *,
    selected_distributions: list[str],
) -> list[InstalledDistributionDescriptor]:
    raw_versions = runtime_state["installed_distributions"]
    descriptors: list[InstalledDistributionDescriptor] = []
    for name in selected_distributions:
        version = raw_versions.get(name)
        if not isinstance(version, str) or not version:
            raise RuntimeError(f"missing installed distribution version for {name}")
        descriptors.append(
            InstalledDistributionDescriptor(
                name=name,
                version=version,
                layer=LOCAL_DISTRIBUTION_LAYERS[name],
            )
        )
    return descriptors


def _prepare_runtime_layout(runtime_root: Path) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "bin").mkdir(parents=True, exist_ok=True)
    for relpath in build_runtime_data_dir_relpaths():
        (runtime_root / relpath).mkdir(parents=True, exist_ok=True)
    (runtime_root / "resources" / "core").mkdir(parents=True, exist_ok=True)


def _resolve_workspace_sections(build_config: Path):
    return resolve_workspace_sections(build_config=build_config, project_root=ROOT_DIR)


def _collect_wheel_files(
    wheel_dir: Path,
    *,
    projects: list[DependencyProject] | None = None,
) -> list[Path]:
    wheel_paths: list[Path] = []
    selected_projects = projects or LOCAL_PROJECTS
    if not wheel_dir.exists():
        raise RuntimeError(f"wheel directory does not exist: {wheel_dir}")
    for project in selected_projects:
        candidates = sorted(wheel_dir.glob(f"{project.name.replace('-', '_')}-*.whl"))
        if not candidates:
            raise RuntimeError(f"missing wheel for {project.name} in {wheel_dir}")
        wheel_paths.append(candidates[-1])
    return wheel_paths


def _has_all_wheels(
    wheel_dir: Path,
    *,
    projects: list[DependencyProject] | None = None,
) -> bool:
    try:
        _collect_wheel_files(wheel_dir, projects=projects)
    except RuntimeError:
        return False
    return True


def _dependency_fingerprint(
    *,
    build_config: Path = DEFAULT_BUILD_CONFIG,
    projects: list[DependencyProject] | None = None,
    variant: str,
) -> str:
    selected_projects = projects or LOCAL_PROJECTS
    source_paths = [RUNTIME_VERSION_CONFIG, build_config]
    for project in selected_projects:
        source_paths.extend([project.project_dir / "pyproject.toml", project.project_dir / "uv.lock"])
    fingerprint = fingerprint_paths(source_paths)
    return f"{variant}:{fingerprint}"


def _wheel_build_fingerprint(*, projects: list[DependencyProject] | None = None) -> str:
    source_paths: list[Path] = []
    selected_projects = projects or LOCAL_PROJECTS
    for project in selected_projects:
        source_paths.extend(_project_source_paths(project.project_dir))
    return fingerprint_paths(source_paths)


def _project_source_paths(project_dir: Path) -> list[Path]:
    paths = [project_dir / "pyproject.toml", project_dir / "src"]
    setup_py = project_dir / "setup.py"
    if setup_py.exists():
        paths.append(setup_py)
    build_helper = project_dir / "build_helpers.py"
    if build_helper.exists():
        paths.append(build_helper)
    return paths


def _prepare_project_build_artifacts(project: DependencyProject) -> None:
    helper_path = project.project_dir / "build_helpers.py"
    if project.name != "munk-perception-full-sdk" or not helper_path.exists():
        return
    run_command(
        [
            ensure_uv_available(),
            "run",
            "--project",
            str(project.project_dir),
            "python",
            str(helper_path),
            "prepare-icon-model",
        ],
        cwd=ROOT_DIR,
    )


def _project_build_env(*, project: DependencyProject, enable_cython: bool) -> dict[str, str] | None:
    if project.name != "munk-perception-full-sdk":
        return None
    env = os.environ.copy()
    env["MUNK_ENABLE_CYTHON"] = "1" if enable_cython else "0"
    return env


if __name__ == "__main__":
    raise SystemExit(main())
