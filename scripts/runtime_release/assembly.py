from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from munk.runtime_distribution import (
    AndroidPlatformToolsPin,
    DEFAULT_DOWNLOAD_DIR,
    PROJECT_ROOT,
    RUNTIME_VERSION_CONFIG,
    DependencyProject,
    RuntimeBuildTarget,
    RuntimeVersionDefaults,
    build_project_wheels,
    build_runtime_manifest,
    copy_adb_sidecar,
    copy_ios_bridge_runtime_assets,
    default_review_knowledge_source_root,
    default_review_runtime_build_root,
    default_state_path,
    dependency_fingerprint,
    ensure_runtime_python,
    ensure_uv_available,
    install_wheel_files,
    ios_bridge_asset_fingerprint,
    load_android_platform_tools_pin,
    load_runtime_version_defaults,
    load_state,
    pbs_target_triple,
    prepare_ios_bridge_source_assets,
    prepare_recording_runtime_assets,
    prepare_workspace_external_assets,
    recording_bridge_fingerprint,
    recording_dependency_fingerprint,
    recording_web_fingerprint,
    refresh_review_knowledge,
    resolve_workspace_selection,
    run_uv_pip_check,
    sync_project_dependencies,
    wheel_build_fingerprint,
    write_launcher,
    write_runtime_manifest,
    write_state,
)

from runtime_release.archive import _finalize_release_artifacts
from runtime_release.python_runtime import (
    RuntimeInspectionPayload,
    build_installed_distribution_descriptors as _build_installed_distribution_descriptors,
    collect_wheel_files as _collect_wheel_files,
    format_subprocess_failure,
    has_all_wheels as _has_all_wheels,
    inspect_runtime_state as _inspect_runtime_state,
    run_subprocess,
)

ROOT_DIR = PROJECT_ROOT
DEFAULT_RUNTIME_ROOT = ROOT_DIR / "dist" / "runtime-release"
DEFAULT_WHEEL_BUILD_DIR = ROOT_DIR / "dist" / "runtime-build" / "wheels"
DEFAULT_RELEASE_ARTIFACT_DIR = ROOT_DIR / "dist" / "runtime-build" / "release-artifacts"
DEFAULT_BUILD_CONFIG = ROOT_DIR / "config" / "build" / "build.yaml"
DEFAULT_NO_REVIEW_BUILD_CONFIG = ROOT_DIR / "config" / "build" / "build.no-review.yaml"
DEFAULT_SIGNING_ENV_FILE = Path("/Users/zhutao/.munk-release/secrets.env")
_run_subprocess = run_subprocess
_format_subprocess_failure = format_subprocess_failure


@dataclass(frozen=True)
class ReleaseBuildTarget:
    variant: str
    build_config: Path
    runtime_root: Path
    archive_name: str | None = None


@dataclass(frozen=True)
class ReleaseAssemblyContext:
    args: argparse.Namespace
    target: ReleaseBuildTarget
    runtime_defaults: RuntimeVersionDefaults
    build_config: Path
    selected_projects: list[DependencyProject]
    ios_bridge_enabled: bool
    review_enabled: bool
    recording_enabled: bool
    runtime_root: Path
    state_path: Path
    previous_state: dict[str, object] | None
    dependency_fingerprint: str
    runtime_ios_bridge_asset_fingerprint: str
    runtime_recording_dependency_fingerprint: str
    runtime_recording_web_fingerprint: str
    runtime_recording_bridge_fingerprint: str
    target_platform: str
    target_arch: str
    adb_pin: AndroidPlatformToolsPin
    wheel_build_fingerprint: str


@dataclass(frozen=True)
class ReleaseRuntimeState:
    runtime_python: Path
    needs_runtime_refresh: bool
    needs_wheel_build: bool
    wheel_paths: list[Path]
    needs_dependency_sync: bool


def _validate_release_args(args: argparse.Namespace, *, platform_name: str) -> None:
    if args.all:
        if args.variant != "full":
            raise RuntimeError("--all cannot be combined with a custom --variant; keep --variant as 'full'")
        if args.build_config.resolve() != DEFAULT_BUILD_CONFIG.resolve():
            raise RuntimeError("--all cannot be combined with --build-config; use the default config set")
    if platform_name != "macos":
        return
    if args.skip_notarize and args.skip_archive:
        return
    if not args.skip_notarize and args.skip_sign:
        raise RuntimeError("cannot notarize an unsigned runtime; remove --skip-sign or add --skip-notarize")
    if not args.skip_notarize and args.skip_archive:
        raise RuntimeError("cannot notarize without an archive; remove --skip-archive or add --skip-notarize")


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


def _assemble_release_target(
    *,
    args: argparse.Namespace,
    target: ReleaseBuildTarget,
    host_target: RuntimeBuildTarget,
) -> None:
    uv_bin = ensure_uv_available()
    context = _build_release_assembly_context(args=args, target=target, host_target=host_target)
    runtime_state = _prepare_release_runtime_state(context=context)
    _sync_release_python_environment(context=context, runtime_state=runtime_state, uv_bin=uv_bin)
    copy_adb_sidecar(
        project_root=ROOT_DIR,
        runtime_root=context.runtime_root,
        download_dir=context.args.download_dir.resolve(),
        pin=context.adb_pin,
        target_platform=context.target_platform,
    )
    recording_assets = prepare_recording_runtime_assets(
        project_root=ROOT_DIR,
        runtime_root=context.runtime_root,
        download_dir=context.args.download_dir.resolve(),
        previous_state=context.previous_state,
        recording_dependency_fingerprint_value=context.runtime_recording_dependency_fingerprint,
        recording_web_fingerprint_value=context.runtime_recording_web_fingerprint,
        recording_bridge_fingerprint_value=context.runtime_recording_bridge_fingerprint,
        needs_runtime_refresh=runtime_state.needs_runtime_refresh,
        force=context.args.force,
        target_platform=context.target_platform,
        recording_enabled=context.recording_enabled,
        verify_node_runtime=True,
        cwd=ROOT_DIR,
    )
    ios_bridge_assets = _prepare_release_ios_bridge_assets(context=context, runtime_state=runtime_state)
    manifest_path, launcher_path = _write_release_manifest_for_target(
        context=context,
        runtime_state=runtime_state,
        recording_assets=recording_assets,
        ios_bridge_assets=ios_bridge_assets,
    )
    release_metadata = _finalize_release_artifacts(
        runtime_root=context.runtime_root,
        runtime_python=runtime_state.runtime_python,
        adb_path=context.runtime_root / _release_adb_relpath(context.target_platform),
        manifest_path=manifest_path,
        runtime_defaults=context.runtime_defaults,
        args=args,
        variant=target.variant,
        target_platform=context.target_platform,
        target_arch=context.target_arch,
        archive_name_override=target.archive_name,
    )
    write_state(
        context.state_path,
        {
            "dependency_fingerprint": context.dependency_fingerprint,
            "ios_bridge_asset_fingerprint": context.runtime_ios_bridge_asset_fingerprint,
            "recording_dependency_fingerprint": context.runtime_recording_dependency_fingerprint,
            "recording_web_fingerprint": context.runtime_recording_web_fingerprint,
            "recording_bridge_fingerprint": context.runtime_recording_bridge_fingerprint,
            "wheel_build_fingerprint": context.wheel_build_fingerprint,
            "runtime_root": str(context.runtime_root),
        },
    )
    print(f"runtime assembled at: {context.runtime_root}")
    print(f"launcher: {launcher_path}")
    print(f"manifest: {manifest_path}")
    if release_metadata["archive_path"]:
        print(f"archive: {release_metadata['archive_path']}")
    print(f"release metadata: {release_metadata['metadata_path']}")
    print(f"signed targets: {release_metadata['signed_target_count']}")
    if release_metadata["notarization_status"]:
        print(f"notarization: {release_metadata['notarization_status']}")


def _build_release_assembly_context(
    *,
    args: argparse.Namespace,
    target: ReleaseBuildTarget,
    host_target: RuntimeBuildTarget,
) -> ReleaseAssemblyContext:
    runtime_defaults = load_runtime_version_defaults(RUNTIME_VERSION_CONFIG)
    build_config = target.build_config.resolve()
    selection = resolve_workspace_selection(build_config=build_config, project_root=ROOT_DIR)
    section_names = {section["name"] for section in selection.workspace_sections}
    selected_project_names = {project.name for project in selection.selected_projects}
    ios_bridge_enabled = "munk-device-ios-runtime" in selected_project_names
    review_enabled = "review" in section_names
    recording_enabled = "recording" in section_names
    runtime_root = target.runtime_root.resolve()
    state_path = default_state_path(project_root=ROOT_DIR, kind="release", runtime_root=runtime_root)
    previous_state = load_state(state_path)
    dependency_fp = dependency_fingerprint(
        build_config=build_config,
        projects=selection.selected_projects,
        version_config_path=RUNTIME_VERSION_CONFIG,
        variant=target.variant,
    )
    prepare_workspace_external_assets(
        projects=selection.selected_projects,
        download_dir=args.download_dir.resolve(),
        force=args.force,
        project_root=ROOT_DIR,
        version_config_path=RUNTIME_VERSION_CONFIG,
    )
    runtime_recording_dependency_fingerprint = (
        recording_dependency_fingerprint(project_root=ROOT_DIR) if recording_enabled else "disabled"
    )
    runtime_recording_web_fingerprint = (
        recording_web_fingerprint(project_root=ROOT_DIR) if recording_enabled else "disabled"
    )
    runtime_recording_bridge_fingerprint = (
        recording_bridge_fingerprint(project_root=ROOT_DIR) if recording_enabled else "disabled"
    )
    runtime_ios_bridge_asset_fingerprint = (
        ios_bridge_asset_fingerprint(project_root=ROOT_DIR) if ios_bridge_enabled else "disabled"
    )
    target_platform = host_target.platform
    target_arch = host_target.arch
    adb_pin = load_android_platform_tools_pin(config_path=RUNTIME_VERSION_CONFIG, target_platform=target_platform)
    wheel_fp = wheel_build_fingerprint(projects=selection.selected_projects)
    return ReleaseAssemblyContext(
        args=args,
        target=target,
        runtime_defaults=runtime_defaults,
        build_config=build_config,
        selected_projects=selection.selected_projects,
        ios_bridge_enabled=ios_bridge_enabled,
        review_enabled=review_enabled,
        recording_enabled=recording_enabled,
        runtime_root=runtime_root,
        state_path=state_path,
        previous_state=previous_state,
        dependency_fingerprint=dependency_fp,
        runtime_ios_bridge_asset_fingerprint=runtime_ios_bridge_asset_fingerprint,
        runtime_recording_dependency_fingerprint=runtime_recording_dependency_fingerprint,
        runtime_recording_web_fingerprint=runtime_recording_web_fingerprint,
        runtime_recording_bridge_fingerprint=runtime_recording_bridge_fingerprint,
        target_platform=target_platform,
        target_arch=target_arch,
        adb_pin=adb_pin,
        wheel_build_fingerprint=wheel_fp,
    )


def _prepare_release_runtime_state(*, context: ReleaseAssemblyContext) -> ReleaseRuntimeState:
    runtime_python_state = ensure_runtime_python(
        runtime_root=context.runtime_root,
        download_dir=context.args.download_dir.resolve(),
        defaults=context.runtime_defaults,
        target_platform=context.target_platform,
        target_arch=context.target_arch,
        previous_state=context.previous_state,
        force=context.args.force,
        cwd=ROOT_DIR,
    )
    runtime_python = runtime_python_state.runtime_python
    needs_runtime_refresh = runtime_python_state.needs_runtime_refresh
    wheel_dir = context.args.wheel_dir.resolve()
    needs_wheel_build = (
        not context.args.skip_build
        and (
            context.args.force
            or context.previous_state is None
            or context.previous_state.get("wheel_build_fingerprint") != context.wheel_build_fingerprint
            or not _has_all_wheels(wheel_dir, projects=context.selected_projects)
        )
    )
    if needs_wheel_build:
        build_project_wheels(
            wheel_dir=wheel_dir,
            runtime_python=runtime_python,
            projects=context.selected_projects,
            project_root=ROOT_DIR,
            download_dir=DEFAULT_DOWNLOAD_DIR,
            version_config_path=RUNTIME_VERSION_CONFIG,
            clean_projects=context.args.force,
            enable_cython=context.args.enable_cython,
        )
    wheel_paths = _collect_wheel_files(wheel_dir, projects=context.selected_projects)
    needs_dependency_sync = (
        context.args.force
        or context.previous_state is None
        or context.previous_state.get("dependency_fingerprint") != context.dependency_fingerprint
        or needs_runtime_refresh
    )
    return ReleaseRuntimeState(
        runtime_python=runtime_python,
        needs_runtime_refresh=needs_runtime_refresh,
        needs_wheel_build=needs_wheel_build,
        wheel_paths=wheel_paths,
        needs_dependency_sync=needs_dependency_sync,
    )


def _sync_release_python_environment(
    *,
    context: ReleaseAssemblyContext,
    runtime_state: ReleaseRuntimeState,
    uv_bin: str,
) -> None:
    if runtime_state.needs_dependency_sync:
        for project in context.selected_projects:
            sync_project_dependencies(
                uv_bin=uv_bin,
                project_dir=project.project_dir,
                runtime_python=runtime_state.runtime_python,
                cwd=ROOT_DIR,
            )
    if (
        runtime_state.needs_dependency_sync
        or runtime_state.needs_wheel_build
        or runtime_state.needs_runtime_refresh
    ):
        install_wheel_files(
            uv_bin=uv_bin,
            runtime_python=runtime_state.runtime_python,
            wheel_paths=runtime_state.wheel_paths,
            cwd=ROOT_DIR,
        )
        if context.review_enabled:
            refresh_review_knowledge(
                runtime_root=context.runtime_root,
                runtime_python=runtime_state.runtime_python,
                source_root=default_review_knowledge_source_root(project_root=ROOT_DIR),
                build_root=default_review_runtime_build_root(runtime_root=context.runtime_root),
                clean=context.args.force,
                project_root=ROOT_DIR,
            )
        run_uv_pip_check(uv_bin=uv_bin, runtime_python=runtime_state.runtime_python, cwd=ROOT_DIR)


def _write_release_manifest_for_target(
    *,
    context: ReleaseAssemblyContext,
    runtime_state: ReleaseRuntimeState,
    recording_assets: dict[str, str] | None,
    ios_bridge_assets: dict[str, str] | None,
) -> tuple[Path, Path]:
    launcher_path = write_launcher(runtime_root=context.runtime_root, runtime_python=runtime_state.runtime_python)
    inspected_runtime = inspect_runtime_state(
        runtime_state.runtime_python,
        selected_distributions=[project.name for project in context.selected_projects],
    )
    manifest_path = context.runtime_root / "manifest.lock"
    manifest = build_runtime_manifest(
        platform=context.target_platform,
        arch=context.target_arch,
        variant=context.target.variant,
        python_version=inspected_runtime["python_version"],
        pbs_release_tag=context.runtime_defaults.release_tag,
        pbs_archive_flavor=context.runtime_defaults.archive_flavor,
        pbs_target_triple=pbs_target_triple(platform_name=context.target_platform, arch=context.target_arch),
        python_root_relpath="python",
        python_executable_relpath=os.path.relpath(runtime_state.runtime_python, context.runtime_root),
        site_packages_relpath=os.path.relpath(Path(inspected_runtime["site_packages"]), context.runtime_root),
        installed_distributions=_build_installed_distribution_descriptors(
            inspected_runtime,
            selected_distributions=[project.name for project in context.selected_projects],
        ),
        adb_relpath=_release_adb_relpath(context.target_platform),
        launcher_relpath=_release_launcher_relpath(context.target_platform),
        ios_bridge_relpath=ios_bridge_assets["ios_bridge_relpath"] if ios_bridge_assets is not None else None,
        recording_ui_relpath=recording_assets["recording_ui_relpath"] if recording_assets is not None else None,
        recording_bridge_relpath=(
            recording_assets["recording_bridge_relpath"] if recording_assets is not None else None
        ),
        node_relpath=(
            recording_assets["node_relpath"]
            if recording_assets is not None
            else (ios_bridge_assets["node_relpath"] if ios_bridge_assets is not None else None)
        ),
    )
    write_runtime_manifest(manifest_path, manifest)
    return manifest_path, launcher_path


def _prepare_release_ios_bridge_assets(
    *,
    context: ReleaseAssemblyContext,
    runtime_state: ReleaseRuntimeState,
) -> dict[str, str] | None:
    if not context.ios_bridge_enabled:
        return None
    needs_source_prepare = (
        context.args.force
        or (
            context.previous_state is not None
            and context.previous_state.get("ios_bridge_asset_fingerprint")
            != context.runtime_ios_bridge_asset_fingerprint
        )
    )
    prepare_ios_bridge_source_assets(
        project_root=ROOT_DIR,
        force=needs_source_prepare,
        cwd=ROOT_DIR,
    )
    needs_runtime_refresh = (
        context.args.force
        or runtime_state.needs_runtime_refresh
        or context.previous_state is None
        or (
            context.previous_state is not None
            and context.previous_state.get("ios_bridge_asset_fingerprint")
            != context.runtime_ios_bridge_asset_fingerprint
        )
    )
    if needs_runtime_refresh:
        return copy_ios_bridge_runtime_assets(
            project_root=ROOT_DIR,
            runtime_root=context.runtime_root,
            download_dir=context.args.download_dir.resolve(),
        )
    return {"ios_bridge_relpath": "sidecars/ios-device-bridge", "node_relpath": _release_node_relpath(context.target_platform)}


def _release_launcher_relpath(platform_name: str) -> str:
    return "bin/munk.cmd" if platform_name == "windows" else "bin/munk"


def _release_adb_relpath(platform_name: str) -> str:
    if platform_name == "windows":
        return "sidecars/android-adb/platform-tools/adb.exe"
    return "sidecars/android-adb/platform-tools/adb"


def _release_node_relpath(platform_name: str) -> str:
    if platform_name == "windows":
        return "sidecars/node/node.exe"
    return "sidecars/node/bin/node"


def inspect_runtime_state(
    runtime_python: Path,
    *,
    selected_distributions: list[str],
) -> RuntimeInspectionPayload:
    return _inspect_runtime_state(
        runtime_python,
        selected_distributions=selected_distributions,
        cwd=ROOT_DIR,
    )
