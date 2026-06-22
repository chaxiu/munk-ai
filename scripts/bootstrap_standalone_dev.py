#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from munk.runtime_distribution import (  # noqa: E402
    DEFAULT_DOWNLOAD_DIR,
    PROJECT_ROOT,
    RUNTIME_VERSION_CONFIG,
    DependencyProject,
    clean_project_build_artifacts,
    copy_adb_sidecar,
    copy_ios_bridge_runtime_assets,
    default_review_knowledge_source_root,
    default_review_runtime_build_root,
    default_state_path,
    dependency_fingerprint,
    ensure_pnpm_available,
    ensure_runtime_python,
    ensure_supported_platform,
    ensure_uv_available,
    ios_bridge_asset_fingerprint,
    ios_bridge_runtime_assets_present,
    ios_bridge_source_assets_ready,
    install_workspace_editables,
    load_android_platform_tools_pin,
    load_runtime_version_defaults,
    load_state,
    prepare_ios_bridge_source_assets,
    prepare_recording_runtime_assets,
    prepare_workspace_external_assets,
    recording_bridge_fingerprint,
    recording_dependency_fingerprint,
    recording_web_fingerprint,
    refresh_review_knowledge,
    resolve_workspace_selection,
    run_uv_pip_check,
    source_fingerprints,
    sync_project_dependencies,
    wheel_build_fingerprint,
    write_launcher,
    write_state,
)

ROOT_DIR = PROJECT_ROOT
DEFAULT_RUNTIME_ROOT = ROOT_DIR / "dist" / "runtime-dev"
DEFAULT_BUILD_CONFIG = ROOT_DIR / "config" / "build" / "build.yaml"
DEV_TEST_REQUIREMENTS = ("pytest>=8.0.0",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a PBS-based standalone dev runtime.")
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=DEFAULT_RUNTIME_ROOT,
        help="Dev runtime root. Defaults to the canonical dist/runtime-dev slot.",
    )
    parser.add_argument("--download-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--build-config", type=Path, default=DEFAULT_BUILD_CONFIG)
    parser.add_argument(
        "--enable-cython",
        action="store_true",
        help="Build perception compiled extensions (.so) instead of the default pure-Python install.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host_target = ensure_supported_platform()
    pnpm_bin = ensure_pnpm_available()
    uv_bin = ensure_uv_available()
    _generate_contracts(pnpm_bin=pnpm_bin)
    defaults = load_runtime_version_defaults(RUNTIME_VERSION_CONFIG)
    build_config = args.build_config.resolve()
    runtime_root = args.runtime_root.resolve()
    state_path = default_state_path(project_root=ROOT_DIR, kind="dev", runtime_root=runtime_root)
    previous_state = load_state(state_path)

    runtime_python_state = ensure_runtime_python(
        runtime_root=runtime_root,
        download_dir=args.download_dir.resolve(),
        defaults=defaults,
        target_platform=host_target.platform,
        target_arch=host_target.arch,
        previous_state=previous_state,
        force=args.force,
        cwd=ROOT_DIR,
    )
    runtime_python = runtime_python_state.runtime_python
    needs_runtime_refresh = runtime_python_state.needs_runtime_refresh

    adb_pin = load_android_platform_tools_pin(
        config_path=RUNTIME_VERSION_CONFIG,
        target_platform=host_target.platform,
    )
    selection = resolve_workspace_selection(build_config=build_config, project_root=ROOT_DIR)
    workspace_sections = selection.workspace_sections
    selected_projects = selection.selected_projects
    editable_projects = list({project.name: project for section in workspace_sections for project in section["editable_projects"]}.values())

    if args.force:
        _clean_force_build_artifacts(
            projects=selected_projects,
            preserve_paths=[
                runtime_root,
                args.download_dir.resolve(),
                RUNTIME_VERSION_CONFIG,
            ],
        )

    prepare_workspace_external_assets(
        projects=selected_projects,
        download_dir=args.download_dir.resolve(),
        force=args.force,
        project_root=ROOT_DIR,
        version_config_path=RUNTIME_VERSION_CONFIG,
    )
    dependency_fp = dependency_fingerprint(
        build_config=build_config,
        projects=selected_projects,
        version_config_path=RUNTIME_VERSION_CONFIG,
    )
    current_source_fingerprints = source_fingerprints(projects=editable_projects)
    previous_source_fingerprints = _load_string_mapping(previous_state, "source_fingerprints")
    changed_editable_projects = {
        project.name
        for project in editable_projects
        if previous_source_fingerprints.get(project.name) != current_source_fingerprints[project.name]
    }
    runtime_recording_dependency_fingerprint = recording_dependency_fingerprint(project_root=ROOT_DIR)
    runtime_recording_web_fingerprint = recording_web_fingerprint(project_root=ROOT_DIR)
    runtime_recording_bridge_fingerprint = recording_bridge_fingerprint(project_root=ROOT_DIR)
    runtime_ios_bridge_asset_fingerprint = ios_bridge_asset_fingerprint(project_root=ROOT_DIR)
    needs_dependency_sync = (
        args.force
        or previous_state is None
        or previous_state.get("dependency_fingerprint") != dependency_fp
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

    if needs_dependency_sync or previous_state is None or changed_editable_projects:
        install_workspace_editables(
            uv_bin=uv_bin,
            runtime_python=runtime_python,
            sections=workspace_sections,
            project_root=ROOT_DIR,
            download_dir=DEFAULT_DOWNLOAD_DIR,
            version_config_path=RUNTIME_VERSION_CONFIG,
            enable_cython=args.enable_cython,
            projects_to_install=None if needs_dependency_sync or previous_state is None else changed_editable_projects,
        )
        refresh_review_knowledge(
            runtime_root=runtime_root,
            runtime_python=runtime_python,
            source_root=default_review_knowledge_source_root(project_root=ROOT_DIR),
            build_root=default_review_runtime_build_root(runtime_root=runtime_root),
            clean=args.force,
            project_root=ROOT_DIR,
        )
        run_uv_pip_check(uv_bin=uv_bin, runtime_python=runtime_python, cwd=ROOT_DIR)

    _ensure_runtime_test_tools(uv_bin=uv_bin, runtime_python=runtime_python)
    _install_playwright_browser(runtime_python=runtime_python)
    copy_adb_sidecar(
        project_root=ROOT_DIR,
        runtime_root=runtime_root,
        download_dir=args.download_dir.resolve(),
        pin=adb_pin,
        target_platform=host_target.platform,
    )
    prepare_recording_runtime_assets(
        project_root=ROOT_DIR,
        runtime_root=runtime_root,
        download_dir=args.download_dir.resolve(),
        previous_state=previous_state,
        recording_dependency_fingerprint_value=runtime_recording_dependency_fingerprint,
        recording_web_fingerprint_value=runtime_recording_web_fingerprint,
        recording_bridge_fingerprint_value=runtime_recording_bridge_fingerprint,
        needs_runtime_refresh=needs_runtime_refresh,
        force=args.force,
        target_platform=host_target.platform,
        cwd=ROOT_DIR,
    )
    needs_ios_bridge_source_prepare = (
        args.force
        or (
            previous_state is not None
            and previous_state.get("ios_bridge_asset_fingerprint") != runtime_ios_bridge_asset_fingerprint
        )
        or not ios_bridge_source_assets_ready(project_root=ROOT_DIR)
    )
    if needs_ios_bridge_source_prepare:
        prepare_ios_bridge_source_assets(
            project_root=ROOT_DIR,
            force=(
                args.force
                or (
                    previous_state is not None
                    and previous_state.get("ios_bridge_asset_fingerprint") != runtime_ios_bridge_asset_fingerprint
                )
            ),
            cwd=ROOT_DIR,
        )
    needs_ios_bridge_runtime_refresh = (
        args.force
        or needs_runtime_refresh
        or previous_state is None
        or (
            previous_state is not None
            and previous_state.get("ios_bridge_asset_fingerprint") != runtime_ios_bridge_asset_fingerprint
        )
        or not ios_bridge_runtime_assets_present(runtime_root=runtime_root)
    )
    if needs_ios_bridge_runtime_refresh:
        copy_ios_bridge_runtime_assets(
            project_root=ROOT_DIR,
            runtime_root=runtime_root,
            download_dir=args.download_dir.resolve(),
        )

    launcher_path = write_launcher(runtime_root=runtime_root, runtime_python=runtime_python)
    write_state(
        state_path,
        {
            "dependency_fingerprint": dependency_fp,
            "ios_bridge_asset_fingerprint": runtime_ios_bridge_asset_fingerprint,
            "recording_dependency_fingerprint": runtime_recording_dependency_fingerprint,
            "recording_web_fingerprint": runtime_recording_web_fingerprint,
            "recording_bridge_fingerprint": runtime_recording_bridge_fingerprint,
            "source_fingerprints": current_source_fingerprints,
            "wheel_build_fingerprint": wheel_build_fingerprint(projects=selected_projects),
            "runtime_root": str(runtime_root),
        },
    )

    print(f"standalone dev runtime bootstrapped at: {runtime_root}")
    print(f"launcher: {launcher_path}")
    for section in workspace_sections:
        joined = ", ".join(str(project.project_dir) for project in section["editable_projects"])
        print(f"{section['name']}: {joined}")
    return 0


def _install_playwright_browser(*, runtime_python: Path) -> None:
    subprocess.run(  # noqa: S603
        [str(runtime_python), "-m", "playwright", "install", "chromium"],
        cwd=ROOT_DIR,
        check=True,
    )


def _ensure_runtime_test_tools(*, uv_bin: str, runtime_python: Path) -> None:
    if _runtime_has_supported_pytest(runtime_python=runtime_python):
        return
    print(f"installing dev test tools into runtime: {', '.join(DEV_TEST_REQUIREMENTS)}")
    subprocess.run(  # noqa: S603
        [
            uv_bin,
            "pip",
            "install",
            "--python",
            str(runtime_python),
            *DEV_TEST_REQUIREMENTS,
        ],
        cwd=ROOT_DIR,
        check=True,
    )


def _runtime_has_supported_pytest(*, runtime_python: Path) -> bool:
    completed = subprocess.run(  # noqa: S603
        [
            str(runtime_python),
            "-c",
            (
                "import importlib.metadata as m; import sys; "
                "version = m.version('pytest'); "
                "major = int(version.split('.', 1)[0]); "
                "sys.exit(0 if major >= 8 else 1)"
            ),
        ],
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _generate_contracts(*, pnpm_bin: str) -> None:
    subprocess.run(  # noqa: S603
        [pnpm_bin, "run", "generate:contracts"],
        cwd=ROOT_DIR,
        check=True,
    )


def _clean_force_build_artifacts(
    *,
    projects: list[DependencyProject],
    preserve_paths: list[Path] | None = None,
) -> None:
    for project in projects:
        project_preserve_paths = [path.resolve() for path in (preserve_paths or [])]
        clean_project_build_artifacts(project.project_dir, preserve_paths=project_preserve_paths)


def _load_string_mapping(previous_state: dict[str, object] | None, key: str) -> dict[str, str]:
    if previous_state is None:
        return {}
    raw_value = previous_state.get(key)
    if isinstance(raw_value, dict):
        result: dict[str, str] = {}
        for raw_key, raw_item in raw_value.items():
            result[str(raw_key)] = str(raw_item)
        return result
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return {str(raw_key): str(raw_item) for raw_key, raw_item in parsed.items()}
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
