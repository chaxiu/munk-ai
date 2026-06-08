from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from munk.config.schema import MunkConfig
from munk.storage_mode import default_profile_home

_ENV_CONFIG = "MUNK_CONFIG"
_WORKSPACE_CONFIG_DIR = ".munk"
_WORKSPACE_CONFIG_NAME = "config.yaml"

ConfigSourceKind = Literal["cli", "env", "workspace", "profile"]


@dataclass(frozen=True)
class ResolvedConfigFile:
    path: Path
    source: ConfigSourceKind


@dataclass(frozen=True)
class ResolvedConfig:
    path: Path
    source: ConfigSourceKind
    config: MunkConfig


def profile_config_path() -> Path:
    return default_profile_home().resolve() / "config" / "config.yaml"


def default_config_path() -> Path:
    return profile_config_path()


def workspace_config_path(workspace_root: Path | None) -> Path | None:
    if workspace_root is None:
        return None
    return workspace_root / _WORKSPACE_CONFIG_DIR / _WORKSPACE_CONFIG_NAME


def load_config_file(path: Path) -> MunkConfig:
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return MunkConfig.model_validate(raw)


def resolve_config_file(
    cli_path: Path | None,
    *,
    workspace_root: Path | None = None,
) -> ResolvedConfigFile | None:
    if cli_path is not None:
        return ResolvedConfigFile(path=cli_path, source="cli")
    env = os.environ.get(_ENV_CONFIG)
    if env:
        return ResolvedConfigFile(path=Path(env), source="env")
    workspace = workspace_config_path(workspace_root)
    if workspace is not None and workspace.exists():
        return ResolvedConfigFile(path=workspace, source="workspace")
    profile = profile_config_path()
    if profile.exists():
        return ResolvedConfigFile(path=profile, source="profile")
    return None


def resolve_config_path(
    cli_path: Path | None,
    *,
    workspace_root: Path | None = None,
) -> Path | None:
    resolved = resolve_config_file(cli_path, workspace_root=workspace_root)
    if resolved is None:
        return None
    return resolved.path


def load_config_context(
    cli_path: Path | None,
    *,
    workspace_root: Path | None = None,
) -> ResolvedConfig | None:
    resolved_file = resolve_config_file(cli_path, workspace_root=workspace_root)
    if resolved_file is None:
        return None
    return ResolvedConfig(
        path=resolved_file.path,
        source=resolved_file.source,
        config=load_config_file(resolved_file.path),
    )


def load_resolved_config(
    cli_path: Path | None,
    *,
    workspace_root: Path | None = None,
) -> MunkConfig | None:
    resolved = load_config_context(cli_path, workspace_root=workspace_root)
    if resolved is None:
        return None
    return resolved.config
