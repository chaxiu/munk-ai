from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

ENV_MUNK_HOME = "MUNK_HOME"
ENV_STORAGE_MODE = "MUNK_STORAGE_MODE"
ENV_HOME_SOURCE = "MUNK_HOME_SOURCE"


class StorageMode(str, Enum):
    WORKSPACE = "workspace"
    PROFILE = "profile"


class HomeSource(str, Enum):
    ENV_OVERRIDE = "env_override"
    WORKSPACE_DEFAULT = "workspace_default"
    PROFILE_DEFAULT = "profile_default"


@dataclass(frozen=True)
class HomeResolution:
    mode: StorageMode
    home: Path
    source: HomeSource


def default_profile_home() -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        return home / "Library" / "Application Support" / "MunkAI"
    if system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data).expanduser() if local_app_data else home / "AppData" / "Local"
        return base / "MunkAI"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "munk"
    return home / ".local" / "share" / "munk"


def default_workspace_home(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".munk"


def resolve_default_home(mode: StorageMode, *, workspace_root: Path | None = None) -> Path:
    if mode == StorageMode.WORKSPACE:
        if workspace_root is None:
            raise ValueError("workspace_root is required for workspace storage mode")
        return default_workspace_home(workspace_root)
    return default_profile_home().resolve()


def apply_default_home(mode: StorageMode, *, workspace_root: Path | None = None) -> HomeResolution:
    configured = os.environ.get(ENV_MUNK_HOME)
    if configured:
        home = Path(configured).expanduser().resolve()
        source = HomeSource.ENV_OVERRIDE
    else:
        home = resolve_default_home(mode, workspace_root=workspace_root).resolve()
        os.environ[ENV_MUNK_HOME] = str(home)
        source = HomeSource.WORKSPACE_DEFAULT if mode == StorageMode.WORKSPACE else HomeSource.PROFILE_DEFAULT
    os.environ[ENV_STORAGE_MODE] = mode.value
    os.environ[ENV_HOME_SOURCE] = source.value
    return HomeResolution(mode=mode, home=home, source=source)


def current_home_resolution() -> HomeResolution | None:
    configured = os.environ.get(ENV_MUNK_HOME)
    if not configured:
        return None
    raw_mode = os.environ.get(ENV_STORAGE_MODE)
    raw_source = os.environ.get(ENV_HOME_SOURCE)
    if raw_mode is None or raw_source is None:
        return None
    return HomeResolution(
        mode=StorageMode(raw_mode),
        home=Path(configured).expanduser().resolve(),
        source=HomeSource(raw_source),
    )
