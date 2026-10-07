from __future__ import annotations

import os
from pathlib import Path

from munk.config.defaults import MUNK_CODE_DEFAULTS

from .models import ResolvedTelemetryConfig, TelemetryProvider


def _read_bool_env(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean string")


def _read_float_env(name: str) -> float | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return float(value)


def _read_provider_env(name: str) -> TelemetryProvider | None:
    value = os.environ.get(name)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "posthog":
        return "posthog"
    raise ValueError(f"{name} must be one of: posthog")


def resolve_telemetry_config(
    *,
    cli_path: Path | None = None,
    workspace_root: Path | None = None,
) -> ResolvedTelemetryConfig:
    """Resolve telemetry config from process env, falling back to code defaults.

    `.env` or other env files should be loaded before process start; telemetry
    config does not scan the filesystem for config files on its own.
    """

    del cli_path, workspace_root
    defaults = MUNK_CODE_DEFAULTS.telemetry
    enabled = _read_bool_env("MUNK_TELEMETRY_ENABLED")
    provider = _read_provider_env("MUNK_TELEMETRY_PROVIDER")
    posthog_host = os.environ.get("MUNK_TELEMETRY_POSTHOG_HOST")
    posthog_api_key = os.environ.get("MUNK_TELEMETRY_POSTHOG_API_KEY")
    timeout_sec = _read_float_env("MUNK_TELEMETRY_TIMEOUT_SEC")
    return ResolvedTelemetryConfig(
        enabled=defaults.enabled if enabled is None else enabled,
        provider="posthog" if provider is None else provider,
        posthog_host=defaults.posthog_host if posthog_host is None else posthog_host,
        posthog_api_key=defaults.posthog_api_key if posthog_api_key is None else posthog_api_key,
        timeout_sec=defaults.timeout_sec if timeout_sec is None else timeout_sec,
        distinct_id_file=None,
    )
