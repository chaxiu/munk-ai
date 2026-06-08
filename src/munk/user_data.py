from __future__ import annotations

import os
from pathlib import Path

from munk.storage_mode import ENV_MUNK_HOME, default_profile_home


def munkai_home() -> Path:
    configured = os.environ.get(ENV_MUNK_HOME)
    if configured:
        return Path(configured).expanduser().resolve()
    return default_profile_home().resolve()


def assets_home() -> Path:
    return munkai_home() / "assets"


def runs_home() -> Path:
    return munkai_home() / "runs"


def operations_home() -> Path:
    return munkai_home() / "operations"


def logs_home() -> Path:
    return munkai_home() / "logs"


def cache_home() -> Path:
    return munkai_home() / "cache"


def config_home() -> Path:
    return munkai_home() / "config"


def detect_repo_test_assets_root(workspace_root: Path | None) -> Path | None:
    if workspace_root is None:
        return None
    candidate = workspace_root / "test_assets"
    if candidate.exists():
        return candidate
    return None


def ensure_home_layout() -> None:
    for path in (assets_home(), runs_home(), operations_home(), logs_home(), cache_home(), config_home()):
        path.mkdir(parents=True, exist_ok=True)
