#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from munk.runtime_distribution import (  # noqa: E402
    DependencyProject,
    WorkspaceSection,
    build_runtime_data_dir_relpaths,
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
    install_editable_project,
    load_android_platform_tools_pin,
    load_runtime_version_defaults,
    load_state,
    prepare_recording_source_assets,
    recording_asset_fingerprint,
    recording_runtime_assets_present,
    recording_source_assets_ready,
    resolve_pbs_archive,
    resolve_workspace_sections,
    run_uv_pip_check,
    sync_project_dependencies,
    write_launcher,
    write_state,
)

RUNTIME_VERSION_CONFIG = ROOT_DIR / "config" / "build" / "runtime-version.json"
DEFAULT_RUNTIME_ROOT = ROOT_DIR / "dist" / "runtime-dev"
DEFAULT_DOWNLOAD_DIR = ROOT_DIR / "dist" / "runtime-build" / "downloads"
DEFAULT_BUILD_CONFIG = ROOT_DIR / "config" / "build" / "build.yaml"
BUILD_REVIEW_KNOWLEDGE_SCRIPT = ROOT_DIR / "scripts" / "build_review_knowledge.py"


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
    ensure_supported_platform()
    uv_bin = ensure_uv_available()
    defaults = load_runtime_version_defaults(RUNTIME_VERSION_CONFIG)
    build_config = args.build_config.resolve()
    runtime_root = args.runtime_root.resolve()
    state_path = default_state_path(project_root=ROOT_DIR, kind="dev", runtime_root=runtime_root)
    previous_state = load_state(state_path)
    if runtime_root.exists() and args.force:
        shutil.rmtree(runtime_root)
    _prepare_runtime_layout(runtime_root)
    python_root = runtime_root / "python"
    runtime_python_exists = python_root.exists() and any((python_root / "bin").glob("python*"))
    needs_runtime_refresh = args.force or not runtime_python_exists or previous_state is None
    if needs_runtime_refresh:
        pbs_archive = resolve_pbs_archive(download_dir=args.download_dir.resolve(), defaults=defaults)
        extract_pbs_archive(archive_path=pbs_archive, python_root=python_root, cwd=ROOT_DIR)
    runtime_python = find_runtime_python(python_root)
    adb_pin = load_android_platform_tools_pin(config_path=RUNTIME_VERSION_CONFIG, target_platform="macos")
    workspace_sections = _resolve_workspace_sections(build_config)
    selected_projects = flatten_workspace_projects(workspace_sections)
    if args.force:
        _clean_force_build_artifacts(
            projects=selected_projects,
            preserve_paths=[
                runtime_root,
                args.download_dir.resolve(),
                RUNTIME_VERSION_CONFIG,
            ],
        )
    dependency_fingerprint = _dependency_fingerprint(build_config=build_config, projects=selected_projects)
    source_fingerprint = _source_fingerprint(projects=selected_projects)
    runtime_recording_asset_fingerprint = recording_asset_fingerprint(project_root=ROOT_DIR)
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
    if needs_dependency_sync or previous_state is None or previous_state.get("source_fingerprint") != source_fingerprint:
        _install_workspace_editables(
            uv_bin=uv_bin,
            runtime_python=runtime_python,
            sections=workspace_sections,
            enable_cython=args.enable_cython,
        )
        _refresh_review_knowledge(runtime_root=runtime_root, runtime_python=runtime_python)
        run_uv_pip_check(uv_bin=uv_bin, runtime_python=runtime_python, cwd=ROOT_DIR)
    _install_playwright_browser(runtime_python=runtime_python)
    copy_adb_sidecar(
        project_root=ROOT_DIR,
        runtime_root=runtime_root,
        download_dir=args.download_dir.resolve(),
        pin=adb_pin,
    )
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
        copy_recording_runtime_assets(
            project_root=ROOT_DIR,
            runtime_root=runtime_root,
            download_dir=args.download_dir.resolve(),
        )
    launcher_path = write_launcher(runtime_root=runtime_root, runtime_python=runtime_python)
    write_state(
        state_path,
        {
            "dependency_fingerprint": dependency_fingerprint,
            "recording_asset_fingerprint": runtime_recording_asset_fingerprint,
            "source_fingerprint": source_fingerprint,
            "runtime_root": str(runtime_root),
        },
    )

    print(f"standalone dev runtime bootstrapped at: {runtime_root}")
    print(f"launcher: {launcher_path}")
    for section in workspace_sections:
        joined = ", ".join(str(project.project_dir) for project in section["editable_projects"])
        print(f"{section['name']}: {joined}")
    return 0


def _resolve_workspace_sections(build_config: Path) -> list[WorkspaceSection]:
    return resolve_workspace_sections(build_config=build_config, project_root=ROOT_DIR)


def _install_workspace_editables(
    *,
    uv_bin: str,
    runtime_python: Path,
    sections: list[WorkspaceSection],
    enable_cython: bool,
) -> None:
    for section in sections:
        for project in section["editable_projects"]:
            _prepare_project_build_artifacts(uv_bin=uv_bin, project=project)
            install_editable_project(
                uv_bin=uv_bin,
                runtime_python=runtime_python,
                project_dir=project.project_dir,
                cwd=ROOT_DIR,
                env=_project_build_env(project=project, enable_cython=enable_cython),
            )


def _refresh_review_knowledge(*, runtime_root: Path, runtime_python: Path) -> None:
    env = os.environ.copy()
    env["MUNK_RUNTIME_ROOT"] = str(runtime_root)
    env["MUNK_RUNTIME_DATA_ROOT"] = str(runtime_root / "data")
    completed = subprocess.run(  # noqa: S603
        [str(runtime_python), str(BUILD_REVIEW_KNOWLEDGE_SCRIPT)],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads(completed.stdout)
    print(
        "review knowledge refreshed: "
        f"rebuilt={payload['rebuilt_cases']} "
        f"skipped={payload['skipped_cases']} "
        f"db={payload['db_path']}"
    )


def _install_playwright_browser(*, runtime_python: Path) -> None:
    subprocess.run(  # noqa: S603
        [str(runtime_python), "-m", "playwright", "install", "chromium"],
        cwd=ROOT_DIR,
        check=True,
    )


def _prepare_runtime_layout(runtime_root: Path) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "bin").mkdir(parents=True, exist_ok=True)
    for relpath in build_runtime_data_dir_relpaths():
        (runtime_root / relpath).mkdir(parents=True, exist_ok=True)
    (runtime_root / "resources" / "core").mkdir(parents=True, exist_ok=True)


def _dependency_fingerprint(*, build_config: Path, projects: list[DependencyProject]) -> str:
    source_paths = [RUNTIME_VERSION_CONFIG, build_config]
    for project in projects:
        source_paths.extend([project.project_dir / "pyproject.toml", project.project_dir / "uv.lock"])
    return fingerprint_paths(source_paths)


def _source_fingerprint(*, projects: list[DependencyProject]) -> str:
    source_paths: list[Path] = []
    for project in projects:
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


def _prepare_project_build_artifacts(*, uv_bin: str, project: DependencyProject) -> None:
    helper_path = project.project_dir / "build_helpers.py"
    if project.name != "munk-perception-full-sdk" or not helper_path.exists():
        return
    subprocess.run(  # noqa: S603
        [
            uv_bin,
            "run",
            "--project",
            str(project.project_dir),
            "python",
            str(helper_path),
            "prepare-icon-model",
        ],
        cwd=ROOT_DIR,
        check=True,
    )


def _project_build_env(*, project: DependencyProject, enable_cython: bool) -> dict[str, str] | None:
    if project.name != "munk-perception-full-sdk":
        return None
    env = os.environ.copy()
    env["MUNK_ENABLE_CYTHON"] = "1" if enable_cython else "0"
    return env


def _clean_force_build_artifacts(
    *,
    projects: list[DependencyProject],
    preserve_paths: list[Path] | None = None,
) -> None:
    for project in projects:
        project_preserve_paths = [path.resolve() for path in (preserve_paths or [])]
        clean_project_build_artifacts(project.project_dir, preserve_paths=project_preserve_paths)


if __name__ == "__main__":
    raise SystemExit(main())
