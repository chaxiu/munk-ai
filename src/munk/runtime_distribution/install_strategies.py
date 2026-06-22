from __future__ import annotations

import shutil
from pathlib import Path

from .assembly_common import (
    DEFAULT_DOWNLOAD_DIR,
    PROJECT_ROOT,
    RUNTIME_VERSION_CONFIG,
    prepare_project_build_artifacts,
    project_build_env,
)
from .build_config import WorkspaceSection
from .build_env import (
    DependencyProject,
    clean_project_build_artifacts,
    ensure_uv_available,
    install_editable_project,
    run_command,
)


def install_workspace_editables(
    *,
    uv_bin: str,
    runtime_python: Path,
    sections: list[WorkspaceSection],
    project_root: Path = PROJECT_ROOT,
    download_dir: Path = DEFAULT_DOWNLOAD_DIR,
    version_config_path: Path = RUNTIME_VERSION_CONFIG,
    enable_cython: bool = False,
    projects_to_install: set[str] | None = None,
) -> None:
    for section in sections:
        for project in section["editable_projects"]:
            if projects_to_install is not None and project.name not in projects_to_install:
                continue
            prepare_project_build_artifacts(
                project,
                project_root=project_root,
                download_dir=download_dir,
                version_config_path=version_config_path,
            )
            install_editable_project(
                uv_bin=uv_bin,
                runtime_python=runtime_python,
                project_dir=project.project_dir,
                cwd=project_root,
                env=project_build_env(project=project, enable_cython=enable_cython),
            )


def build_project_wheels(
    *,
    wheel_dir: Path,
    runtime_python: Path,
    projects: list[DependencyProject],
    project_root: Path = PROJECT_ROOT,
    download_dir: Path = DEFAULT_DOWNLOAD_DIR,
    version_config_path: Path = RUNTIME_VERSION_CONFIG,
    clean_projects: bool = False,
    enable_cython: bool = False,
) -> None:
    if wheel_dir.exists():
        shutil.rmtree(wheel_dir)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    uv_bin = ensure_uv_available()
    for project in projects:
        if clean_projects:
            preserved_paths = [wheel_dir]
            if project.project_dir == project_root:
                preserved_paths.append(version_config_path)
            clean_project_build_artifacts(project.project_dir, preserve_paths=preserved_paths)
        prepare_project_build_artifacts(
            project,
            project_root=project_root,
            download_dir=download_dir,
            version_config_path=version_config_path,
        )
        run_command(
            [
                uv_bin,
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
            env=project_build_env(project=project, enable_cython=enable_cython),
        )
