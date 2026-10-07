from __future__ import annotations

from pathlib import Path

from munk.config.load import ResolvedConfig, load_config_context
from munk.services.errors import ConfigValidationError

CONFIG_DISCOVERY_HELP = (
    "pass --config, set MUNK_CONFIG, create <workspace>/.munk/config.yaml, "
    "or create <Munk AI profile home>/config/config.yaml"
)


def require_config_context(
    *,
    cli_path: Path | None,
    workspace_root: Path,
    command_name: str,
) -> ResolvedConfig:
    resolved = load_config_context(cli_path, workspace_root=workspace_root)
    if resolved is None:
        raise ConfigValidationError(f"{command_name} requires a config file: {CONFIG_DISCOVERY_HELP}")
    return resolved
