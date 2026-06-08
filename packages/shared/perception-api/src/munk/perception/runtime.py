from __future__ import annotations

from importlib.metadata import entry_points

from .contracts import PerceptionProviderFactory, PerceptionRuntimeConfig
from .diagnostics import PerceptionProviderDiagnostics
from .errors import (
    PerceptionProviderConflictError,
    PerceptionProviderNotFoundError,
    PerceptionProviderUnavailableError,
)

ENTRY_POINT_GROUP = "munk.perception.providers"


def list_provider_factories() -> dict[str, PerceptionProviderFactory]:
    factories: dict[str, PerceptionProviderFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_provider_factory(provider_name: str | None = None) -> PerceptionProviderFactory:
    factories = list_provider_factories()
    if provider_name:
        factory = factories.get(provider_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise PerceptionProviderNotFoundError(
                f"perception provider '{provider_name}' not found; available providers: {available}"
            )
        return factory
    if not factories:
        raise PerceptionProviderUnavailableError("no perception provider installed")
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise PerceptionProviderConflictError(
            "multiple perception providers installed; configure `perception.provider` "
            f"to choose one: {available}"
        )
    return next(iter(factories.values()))


def create_perception_provider(
    runtime_config: PerceptionRuntimeConfig,
    *,
    max_side: int = 1600,
    icon_conf: float = 0.12,
):
    factory = resolve_provider_factory(runtime_config.provider)
    return factory.create_provider(
        max_side=max_side,
        icon_conf=icon_conf,
        cache_dir=runtime_config.cache_dir,
        options=runtime_config.extra_options,
    )


def diagnose_perception_provider(
    runtime_config: PerceptionRuntimeConfig,
) -> PerceptionProviderDiagnostics:
    factory = resolve_provider_factory(runtime_config.provider)
    return factory.diagnose(
        cache_dir=runtime_config.cache_dir,
        options=runtime_config.extra_options,
    )
