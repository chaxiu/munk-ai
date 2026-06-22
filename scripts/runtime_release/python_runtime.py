from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TypedDict, cast

from munk.runtime_distribution import (
    DependencyProject,
    InstalledDistributionDescriptor,
    build_distribution_layer_map,
)

LOCAL_DISTRIBUTION_LAYERS = build_distribution_layer_map()


class RuntimeInspectionPayload(TypedDict):
    python_version: str
    site_packages: str
    installed_distributions: dict[str, str]


def inspect_runtime_state(
    runtime_python: Path,
    *,
    selected_distributions: list[str],
    cwd: Path,
) -> RuntimeInspectionPayload:
    command = [
        str(runtime_python),
        "-c",
        (
            "import importlib.metadata as m, json, platform, sysconfig; "
            f"targets = {json.dumps(selected_distributions)}; "
            "print(json.dumps({"
            "'python_version': platform.python_version(), "
            "'site_packages': sysconfig.get_paths()['purelib'], "
            "'installed_distributions': {name: m.version(name) for name in targets}"
            "}))"
        ),
    ]
    completed = run_subprocess(command, cwd=cwd, capture_output=True)
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


def build_installed_distribution_descriptors(
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


def collect_wheel_files(
    wheel_dir: Path,
    *,
    projects: list[DependencyProject],
) -> list[Path]:
    wheel_paths: list[Path] = []
    if not wheel_dir.exists():
        raise RuntimeError(f"wheel directory does not exist: {wheel_dir}")
    for project in projects:
        candidates = sorted(wheel_dir.glob(f"{project.name.replace('-', '_')}-*.whl"))
        if not candidates:
            raise RuntimeError(f"missing wheel for {project.name} in {wheel_dir}")
        wheel_paths.append(candidates[-1])
    return wheel_paths


def has_all_wheels(
    wheel_dir: Path,
    *,
    projects: list[DependencyProject],
) -> bool:
    try:
        collect_wheel_files(wheel_dir, projects=projects)
    except RuntimeError:
        return False
    return True


def run_subprocess(
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
            format_subprocess_failure(
                command=list(exc.cmd) if isinstance(exc.cmd, (list, tuple)) else [str(exc.cmd)],
                cwd=cwd,
                returncode=exc.returncode,
                stdout=exc.stdout,
                stderr=exc.stderr,
            )
        ) from exc


def format_subprocess_failure(
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
