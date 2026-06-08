from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Protocol

from .errors import OptimizeRuntimeConflictError, OptimizeRuntimeUnavailableError
from .health import OptimizeRuntimeHealth
from .models import OptimizeRequest, OptimizeResult

ENTRY_POINT_GROUP = "munk.optimize.runtimes"


class OptimizeRuntime(Protocol):
    def optimize(self, request: OptimizeRequest) -> OptimizeResult: ...


class OptimizeRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self, *, resolved_config: Any) -> OptimizeRuntime: ...

    def diagnose(self) -> OptimizeRuntimeHealth: ...


def list_optimize_runtime_factories() -> dict[str, OptimizeRuntimeFactory]:
    factories: dict[str, OptimizeRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_optimize_runtime_factory(runtime_name: str | None = None) -> OptimizeRuntimeFactory:
    factories = list_optimize_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise OptimizeRuntimeUnavailableError(
                f"optimize runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise OptimizeRuntimeUnavailableError(
            "no optimize local runtime installed; install the optimize local runtime package first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise OptimizeRuntimeConflictError(
            "multiple optimize runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_optimize_runtime(*, resolved_config: Any, runtime_name: str | None = None) -> OptimizeRuntime:
    factory = resolve_optimize_runtime_factory(runtime_name)
    return factory.create_runtime(resolved_config=resolved_config)


def diagnose_optimize_runtime(runtime_name: str | None = None) -> OptimizeRuntimeHealth:
    factory = resolve_optimize_runtime_factory(runtime_name)
    return factory.diagnose()
