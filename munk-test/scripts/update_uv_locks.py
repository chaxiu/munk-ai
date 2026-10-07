#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from munk.runtime_distribution import (  # noqa: E402
    DependencyProject,
    ensure_uv_available,
    flatten_workspace_projects,
    load_runtime_version_defaults,
    resolve_workspace_sections,
    run_command,
)

RUNTIME_VERSION_CONFIG = ROOT_DIR / "config" / "build" / "runtime-version.json"
DEFAULT_BUILD_CONFIG = ROOT_DIR / "config" / "build" / "build.yaml"


def _resolve_projects() -> list[DependencyProject]:
    workspace_projects = flatten_workspace_projects(
        resolve_workspace_sections(build_config=DEFAULT_BUILD_CONFIG, project_root=ROOT_DIR)
    )
    non_root_projects = [project for project in workspace_projects if project.name != "munk"]
    return [DependencyProject(name="munk", project_dir=ROOT_DIR), *non_root_projects]


PROJECTS = _resolve_projects()


def main() -> int:
    uv_bin = ensure_uv_available()
    runtime_defaults = load_runtime_version_defaults(RUNTIME_VERSION_CONFIG)
    lock_python = ".".join(runtime_defaults.python_version.split(".")[:2])
    for project in PROJECTS:
        run_command(
            [uv_bin, "lock", "--project", str(project.project_dir), "--python", lock_python],
            cwd=ROOT_DIR,
        )
        print(f"updated uv.lock: {project.project_dir / 'uv.lock'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
