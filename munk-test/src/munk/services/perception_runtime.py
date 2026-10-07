from __future__ import annotations

from pathlib import Path

from munk.config.schema import MunkConfig
from munk.perception import (
    PerceptionRuntimeConfig,
    create_perception_provider,
    diagnose_perception_provider,
)
from munk.services.errors import MissingResourceError


def build_runtime_config(config: MunkConfig) -> PerceptionRuntimeConfig:
    section = config.perception
    cache_dir = None
    extra_options: dict[str, str] = {}
    provider = None
    if section is not None:
        provider = section.provider
        cache_dir = Path(section.cache_dir).expanduser() if section.cache_dir else None
        extra_options = dict(section.extra_options)
    return PerceptionRuntimeConfig(
        provider=provider,
        cache_dir=cache_dir,
        extra_options=extra_options,
    )


def build_perception_provider_for_runtime(
    config: MunkConfig,
    *,
    max_side: int,
    icon_conf: float,
):
    runtime_config = build_runtime_config(config)
    try:
        return create_perception_provider(
            runtime_config,
            max_side=max_side,
            icon_conf=icon_conf,
        )
    except LookupError as exc:
        raise MissingResourceError(str(exc)) from exc


def diagnose_perception_runtime(config: MunkConfig):
    runtime_config = build_runtime_config(config)
    try:
        return diagnose_perception_provider(runtime_config)
    except LookupError as exc:
        raise MissingResourceError(str(exc)) from exc
