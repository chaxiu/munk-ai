from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Protocol

from munk.agent_runtime.control import CancelController

from .errors import RunnerRuntimeConflictError, RunnerRuntimeUnavailableError
from .health import RunnerRuntimeHealth
from .models import RunnerRequest, RunnerRuntimeContext, RunnerRuntimeOutput

ENTRY_POINT_GROUP = "munk.runner.runtimes"


class RunnerRuntime(Protocol):
    def run(
        self,
        request: RunnerRequest,
        *,
        context: RunnerRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> RunnerRuntimeOutput: ...


class RunnerRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self, *, resolved_config: Any, event_sink: Any | None = None) -> RunnerRuntime: ...

    def diagnose(self) -> RunnerRuntimeHealth: ...


def list_runner_runtime_factories() -> dict[str, RunnerRuntimeFactory]:
    factories: dict[str, RunnerRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_runner_runtime_factory(runtime_name: str | None = None) -> RunnerRuntimeFactory:
    factories = list_runner_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise RunnerRuntimeUnavailableError(
                f"runner runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise RunnerRuntimeUnavailableError(
            "no runner local runtime installed; install the runner local runtime package first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise RunnerRuntimeConflictError(
            "multiple runner runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_runner_runtime(
    *,
    resolved_config: Any,
    runtime_name: str | None = None,
    event_sink: Any | None = None,
) -> RunnerRuntime:
    factory = resolve_runner_runtime_factory(runtime_name)
    return factory.create_runtime(resolved_config=resolved_config, event_sink=event_sink)


def diagnose_runner_runtime(runtime_name: str | None = None) -> RunnerRuntimeHealth:
    factory = resolve_runner_runtime_factory(runtime_name)
    return factory.diagnose()
