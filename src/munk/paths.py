import os
from pathlib import Path

from munk.runtime_distribution import resolve_runtime_layout
from munk.runtime_distribution.resolver import (
    ENV_ADB_PATH,
    ENV_ADBUTILS_ADB_PATH,
    assets_root_from_env,
)
from munk.user_data import assets_home, munkai_home


def project_root() -> Path:
    return resolve_runtime_layout().project_root


def resource_path(relative_path: str) -> Path:
    return resource_root() / relative_path


def resource_root() -> Path:
    return resolve_runtime_layout().core_resources_root


def runtime_root() -> Path:
    return resolve_runtime_layout().runtime_root


def runtime_data_root() -> Path:
    return munkai_home()


def assets_root() -> Path:
    explicit_root = assets_root_from_env()
    if explicit_root is not None:
        return explicit_root
    return assets_home()


def test_assets_root() -> Path:
    return assets_root()


def adb_path() -> Path:
    return resolve_runtime_layout().adb_path


def export_adb_env() -> Path:
    resolved = adb_path()
    resolved_str = str(resolved)
    os.environ[ENV_ADB_PATH] = resolved_str
    os.environ[ENV_ADBUTILS_ADB_PATH] = resolved_str
    return resolved
