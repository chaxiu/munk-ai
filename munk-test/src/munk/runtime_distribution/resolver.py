from __future__ import annotations

import os
import platform
import sys
from functools import lru_cache
from pathlib import Path

from .manifest import MANIFEST_FILE_NAME, load_runtime_manifest
from .models import ResolvedRuntimeLayout, RuntimeDistributionManifest

ENV_RUNTIME_ROOT = "MUNK_RUNTIME_ROOT"
ENV_RUNTIME_MANIFEST = "MUNK_RUNTIME_MANIFEST"
ENV_RUNTIME_DATA_ROOT = "MUNK_RUNTIME_DATA_ROOT"
ENV_ASSETS_ROOT = "MUNK_ASSETS_ROOT"
ENV_ADB_PATH = "MUNK_ADB_PATH"
ENV_ADBUTILS_ADB_PATH = "ADBUTILS_ADB_PATH"


def clear_runtime_layout_cache() -> None:
    resolve_runtime_layout.cache_clear()


@lru_cache(maxsize=1)
def resolve_runtime_layout() -> ResolvedRuntimeLayout:
    project_root = _project_root()
    runtime_root = _runtime_root_from_env()
    manifest_path = _manifest_path_from_env(runtime_root)
    if runtime_root is not None:
        return _build_distribution_layout(
            project_root=project_root,
            runtime_root=runtime_root,
            manifest_path=manifest_path,
        )

    discovered_manifest = _discover_manifest_from_executable()
    if discovered_manifest is not None:
        return _build_distribution_layout(
            project_root=project_root,
            runtime_root=discovered_manifest.parent,
            manifest_path=discovered_manifest,
        )

    return _build_development_layout(project_root=project_root)


def _build_distribution_layout(
    *,
    project_root: Path,
    runtime_root: Path,
    manifest_path: Path | None,
) -> ResolvedRuntimeLayout:
    manifest = _load_manifest_optional(manifest_path)
    python_root = runtime_root / manifest.paths.python_root if manifest is not None else runtime_root / "python"
    bin_root = runtime_root / manifest.paths.bin_root if manifest is not None else runtime_root / "bin"
    sidecars_root = (
        runtime_root / manifest.paths.sidecars_root if manifest is not None else runtime_root / "sidecars"
    )
    default_data_root = runtime_root / manifest.paths.data_root if manifest is not None else runtime_root / "data"
    data_root = Path(os.environ.get(ENV_RUNTIME_DATA_ROOT, default_data_root)).expanduser().resolve()
    core_resources_root = (
        runtime_root / manifest.paths.core_resources_root
        if manifest is not None
        else runtime_root / "resources" / "core"
    )
    adb_relpath = None
    if manifest is not None:
        adb_entry = manifest.sidecars.get("adb")
        if adb_entry is not None:
            adb_relpath = adb_entry.path
    default_adb_path = runtime_root / adb_relpath if adb_relpath else _default_distribution_adb_path(runtime_root)
    adb_path = _resolved_adb_path(default_adb_path)
    return ResolvedRuntimeLayout(
        layout_mode="distribution",
        runtime_root=runtime_root,
        manifest_path=manifest_path,
        python_root=python_root,
        bin_root=bin_root,
        sidecars_root=sidecars_root,
        data_root=data_root,
        core_resources_root=core_resources_root,
        adb_path=adb_path,
        project_root=project_root,
        manifest=manifest,
    )


def _build_development_layout(*, project_root: Path) -> ResolvedRuntimeLayout:
    data_root = Path(os.environ.get(ENV_RUNTIME_DATA_ROOT, project_root)).expanduser().resolve()
    return ResolvedRuntimeLayout(
        layout_mode="development",
        runtime_root=project_root,
        manifest_path=None,
        python_root=None,
        bin_root=project_root,
        sidecars_root=None,
        data_root=data_root,
        core_resources_root=project_root,
        adb_path=_resolved_adb_path(_default_development_adb_path(project_root)),
        project_root=project_root,
        manifest=None,
    )


def _runtime_root_from_env() -> Path | None:
    raw = os.environ.get(ENV_RUNTIME_ROOT)
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _manifest_path_from_env(runtime_root: Path | None) -> Path | None:
    raw = os.environ.get(ENV_RUNTIME_MANIFEST)
    if raw:
        return Path(raw).expanduser().resolve()
    if runtime_root is None:
        return None
    candidate = runtime_root / MANIFEST_FILE_NAME
    return candidate if candidate.exists() else None


def assets_root_from_env() -> Path | None:
    raw = os.environ.get(ENV_ASSETS_ROOT)
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _discover_manifest_from_executable() -> Path | None:
    executable = Path(sys.executable).resolve()
    search_roots = [executable.parent, executable.parent.parent, executable.parent.parent.parent]
    for root in search_roots:
        candidate = root / MANIFEST_FILE_NAME
        if candidate.exists():
            return candidate
    return None


def _load_manifest_optional(path: Path | None) -> RuntimeDistributionManifest | None:
    if path is None or not path.exists():
        return None
    return load_runtime_manifest(path)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_distribution_adb_path(runtime_root: Path) -> Path:
    suffix = "adb.exe" if platform.system() == "Windows" else "adb"
    return runtime_root / "sidecars" / "android-adb" / "platform-tools" / suffix


def _default_development_adb_path(project_root: Path) -> Path:
    system = platform.system()
    if system == "Darwin":
        return project_root / "android-adb" / "macos" / "platform-tools" / "adb"
    if system == "Linux":
        return project_root / "android-adb" / "linux" / "platform-tools" / "adb"
    return project_root / "android-adb" / "windows" / "platform-tools" / "adb.exe"


def _resolved_adb_path(default_path: Path) -> Path:
    raw = os.environ.get(ENV_ADB_PATH) or os.environ.get(ENV_ADBUTILS_ADB_PATH)
    if not raw:
        return default_path
    return Path(raw).expanduser().resolve()
