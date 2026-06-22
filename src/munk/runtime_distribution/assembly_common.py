from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .build_config import WorkspaceSection, flatten_workspace_projects, resolve_workspace_sections
from .build_env import (
    DependencyProject,
    RuntimeVersionDefaults,
    copy_recording_runtime_assets,
    ensure_uv_available,
    extract_pbs_archive,
    find_runtime_python,
    fingerprint_paths,
    load_knowledge_embed_model_release,
    prepare_knowledge_embed_model,
    prepare_recording_source_assets,
    recording_runtime_asset_relpaths,
    recording_runtime_assets_present,
    recording_source_assets_ready,
    resolve_pbs_archive,
    run_command,
    verify_bundled_node_runtime,
)
from .registry import build_runtime_data_dir_relpaths

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_VERSION_CONFIG = PROJECT_ROOT / "config" / "build" / "runtime-version.json"
DEFAULT_DOWNLOAD_DIR = PROJECT_ROOT / "dist" / "runtime-build" / "downloads"
BUILD_REVIEW_KNOWLEDGE_SCRIPT = PROJECT_ROOT / "scripts" / "build_review_knowledge.py"
DEFAULT_REVIEW_KNOWLEDGE_SOURCE_ROOT = (
    PROJECT_ROOT
    / "packages"
    / "agents"
    / "review-agent-runtime-local"
    / "src"
    / "munk_review_local"
    / "resources"
    / "review_knowledge"
)


@dataclass(frozen=True)
class WorkspaceSelection:
    workspace_sections: list[WorkspaceSection]
    selected_projects: list[DependencyProject]


@dataclass(frozen=True)
class RuntimePythonState:
    runtime_python: Path
    needs_runtime_refresh: bool


def prepare_runtime_layout(runtime_root: Path) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "bin").mkdir(parents=True, exist_ok=True)
    for relpath in build_runtime_data_dir_relpaths():
        (runtime_root / relpath).mkdir(parents=True, exist_ok=True)
    (runtime_root / "resources" / "core").mkdir(parents=True, exist_ok=True)


def ensure_runtime_python(
    *,
    runtime_root: Path,
    download_dir: Path,
    defaults: RuntimeVersionDefaults,
    target_platform: str,
    target_arch: str,
    previous_state: Mapping[str, object] | None,
    force: bool,
    cwd: Path = PROJECT_ROOT,
) -> RuntimePythonState:
    if runtime_root.exists() and force:
        shutil.rmtree(runtime_root)
    python_root = runtime_root / "python"
    runtime_python_exists = False
    if python_root.exists():
        try:
            find_runtime_python(python_root)
            runtime_python_exists = True
        except RuntimeError:
            runtime_python_exists = False
    needs_runtime_refresh = force or not runtime_python_exists or previous_state is None
    prepare_runtime_layout(runtime_root)
    if needs_runtime_refresh:
        pbs_archive = resolve_pbs_archive(
            download_dir=download_dir.resolve(),
            defaults=defaults,
            platform_name=target_platform,
            arch=target_arch,
        )
        extract_pbs_archive(archive_path=pbs_archive, python_root=python_root, cwd=cwd)
    runtime_python = find_runtime_python(python_root)
    return RuntimePythonState(
        runtime_python=runtime_python,
        needs_runtime_refresh=needs_runtime_refresh,
    )


def resolve_workspace_selection(
    *,
    build_config: Path,
    project_root: Path = PROJECT_ROOT,
) -> WorkspaceSelection:
    workspace_sections = resolve_workspace_sections(build_config=build_config, project_root=project_root)
    return WorkspaceSelection(
        workspace_sections=workspace_sections,
        selected_projects=flatten_workspace_projects(workspace_sections),
    )


def dependency_fingerprint(
    *,
    build_config: Path,
    projects: list[DependencyProject],
    version_config_path: Path = RUNTIME_VERSION_CONFIG,
    variant: str | None = None,
) -> str:
    source_paths = [version_config_path, build_config]
    for project in projects:
        source_paths.extend([project.project_dir / "pyproject.toml", project.project_dir / "uv.lock"])
    fingerprint = fingerprint_paths(source_paths)
    return f"{variant}:{fingerprint}" if variant is not None else fingerprint


def source_fingerprint(*, projects: list[DependencyProject]) -> str:
    source_paths: list[Path] = []
    for project in projects:
        source_paths.extend(project_source_paths(project.project_dir))
    return fingerprint_paths(source_paths)


def project_source_fingerprint(project: DependencyProject) -> str:
    return fingerprint_paths(project_source_paths(project.project_dir))


def source_fingerprints(*, projects: list[DependencyProject]) -> dict[str, str]:
    return {project.name: project_source_fingerprint(project) for project in projects}


def wheel_build_fingerprint(*, projects: list[DependencyProject]) -> str:
    source_paths: list[Path] = []
    for project in projects:
        source_paths.extend(project_source_paths(project.project_dir))
    return fingerprint_paths(source_paths)


def project_source_paths(project_dir: Path) -> list[Path]:
    paths = [project_dir / "pyproject.toml", project_dir / "src"]
    setup_py = project_dir / "setup.py"
    if setup_py.exists():
        paths.append(setup_py)
    build_helper = project_dir / "build_helpers.py"
    if build_helper.exists():
        paths.append(build_helper)
    return paths


def prepare_project_build_artifacts(
    project: DependencyProject,
    *,
    project_root: Path = PROJECT_ROOT,
    download_dir: Path = DEFAULT_DOWNLOAD_DIR,
    version_config_path: Path = RUNTIME_VERSION_CONFIG,
) -> None:
    if project.name == "munk-knowledge-runtime-local":
        prepare_knowledge_embed_model(
            project_root=project_root,
            download_dir=download_dir,
            version_config_path=version_config_path,
        )
        return
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
        cwd=project_root,
    )


def prepare_workspace_external_assets(
    *,
    projects: list[DependencyProject],
    download_dir: Path,
    force: bool,
    project_root: Path = PROJECT_ROOT,
    version_config_path: Path = RUNTIME_VERSION_CONFIG,
) -> None:
    if not any(project.name == "munk-knowledge-runtime-local" for project in projects):
        return
    release = load_knowledge_embed_model_release(config_path=version_config_path)
    prepared_dir = prepare_knowledge_embed_model(
        project_root=project_root,
        download_dir=download_dir,
        version_config_path=version_config_path,
        force=force,
    )
    print(f"knowledge embed model prepared: {release.version} -> {prepared_dir}")


def project_build_env(*, project: DependencyProject, enable_cython: bool) -> dict[str, str] | None:
    if project.name != "munk-perception-full-sdk":
        return None
    env = os.environ.copy()
    env["MUNK_ENABLE_CYTHON"] = "1" if enable_cython else "0"
    return env


def default_review_knowledge_source_root(*, project_root: Path = PROJECT_ROOT) -> Path:
    if project_root == PROJECT_ROOT:
        return DEFAULT_REVIEW_KNOWLEDGE_SOURCE_ROOT
    return (
        project_root
        / "packages"
        / "agents"
        / "review-agent-runtime-local"
        / "src"
        / "munk_review_local"
        / "resources"
        / "review_knowledge"
    )


def default_review_runtime_build_root(*, runtime_root: Path) -> Path:
    return runtime_root / "data" / "review-runtime-local"


def refresh_review_knowledge(
    *,
    runtime_root: Path,
    runtime_python: Path,
    source_root: Path | None = None,
    build_root: Path | None = None,
    clean: bool = False,
    project_root: Path = PROJECT_ROOT,
    build_review_knowledge_script: Path = BUILD_REVIEW_KNOWLEDGE_SCRIPT,
) -> None:
    env = os.environ.copy()
    env["MUNK_RUNTIME_ROOT"] = str(runtime_root)
    env["MUNK_RUNTIME_DATA_ROOT"] = str(runtime_root / "data")
    command = [str(runtime_python), str(build_review_knowledge_script)]
    if source_root is not None:
        command.extend(["--source-root", str(source_root)])
    if build_root is not None:
        command.extend(["--build-root", str(build_root)])
    if clean:
        command.append("--clean")
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=project_root,
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


def prepare_recording_runtime_assets(
    *,
    project_root: Path,
    runtime_root: Path,
    download_dir: Path,
    previous_state: Mapping[str, object] | None,
    recording_dependency_fingerprint_value: str,
    recording_web_fingerprint_value: str,
    recording_bridge_fingerprint_value: str,
    needs_runtime_refresh: bool,
    force: bool,
    target_platform: str,
    recording_enabled: bool = True,
    verify_node_runtime: bool = False,
    cwd: Path | None = None,
) -> dict[str, str] | None:
    if not recording_enabled:
        return None
    dependency_changed = (
        previous_state is not None
        and previous_state.get("recording_dependency_fingerprint") != recording_dependency_fingerprint_value
    )
    web_changed = (
        previous_state is not None and previous_state.get("recording_web_fingerprint") != recording_web_fingerprint_value
    )
    bridge_changed = (
        previous_state is not None
        and previous_state.get("recording_bridge_fingerprint") != recording_bridge_fingerprint_value
    )
    needs_recording_source_prepare = (
        force
        or dependency_changed
        or web_changed
        or bridge_changed
        or not recording_source_assets_ready(project_root=project_root)
    )
    if needs_recording_source_prepare:
        prepare_recording_source_assets(
            project_root=project_root,
            force=force,
            install=dependency_changed,
            build_web=dependency_changed or web_changed,
            build_bridge=dependency_changed or bridge_changed,
            fetch_scrcpy=dependency_changed,
            cwd=cwd or project_root,
        )
    needs_recording_runtime_refresh = (
        force
        or needs_runtime_refresh
        or previous_state is None
        or dependency_changed
        or web_changed
        or bridge_changed
        or not recording_runtime_assets_present(runtime_root=runtime_root)
    )
    if needs_recording_runtime_refresh:
        recording_assets = copy_recording_runtime_assets(
            project_root=project_root,
            runtime_root=runtime_root,
            download_dir=download_dir,
        )
    else:
        recording_assets = recording_runtime_asset_relpaths(runtime_root=runtime_root)
    if verify_node_runtime and target_platform == "macos":
        verify_bundled_node_runtime(
            runtime_root=runtime_root,
            forbidden_prefixes=("/opt/homebrew/", "/usr/local/opt/", str(project_root)),
        )
    return recording_assets
