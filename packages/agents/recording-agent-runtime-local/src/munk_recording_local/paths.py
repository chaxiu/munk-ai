from __future__ import annotations

import os
import platform
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ENV_MUNK_HOME = "MUNK_HOME"


def munkai_home() -> Path:
    configured = os.environ.get(ENV_MUNK_HOME)
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_munkai_home().resolve()


def recording_assets_home() -> Path:
    return munkai_home() / "assets" / "recordings"


def ensure_recording_assets_home() -> Path:
    root = recording_assets_home()
    root.mkdir(parents=True, exist_ok=True)
    return root


def recording_app_home(app_id: str) -> Path:
    return recording_assets_home() / app_id


def ensure_recording_app_home(app_id: str) -> Path:
    root = recording_app_home(app_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def allocate_recording_dir(*, app_id: str) -> tuple[str, Path]:
    app_root = ensure_recording_app_home(app_id)
    for _attempt in range(8):
        recording_id = create_recording_id(prefix="rec")
        recording_dir = app_root / recording_id
        try:
            recording_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return recording_id, recording_dir
    raise RuntimeError(f"failed to allocate recording directory for app '{app_id}'")


def create_recording_id(*, prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{suffix}"


def _default_munkai_home() -> Path:
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
