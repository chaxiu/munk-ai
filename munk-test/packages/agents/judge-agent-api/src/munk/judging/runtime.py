from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Protocol

from munk.agent_runtime.control import CancelController

from .errors import JudgeRuntimeConflictError, JudgeRuntimeUnavailableError
from .health import JudgeRuntimeHealth
from .models import JudgeRequest, JudgeRuntimeContext, JudgeRuntimeOutput

ENTRY_POINT_GROUP = "munk.judge.runtimes"


class JudgeRuntime(Protocol):
    def judge(
        self,
        request: JudgeRequest,
        *,
        context: JudgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> JudgeRuntimeOutput: ...


class JudgeRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self, *, resolved_config: Any) -> JudgeRuntime: ...

    def diagnose(self) -> JudgeRuntimeHealth: ...


def list_judge_runtime_factories() -> dict[str, JudgeRuntimeFactory]:
    factories: dict[str, JudgeRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_judge_runtime_factory(runtime_name: str | None = None) -> JudgeRuntimeFactory:
    factories = list_judge_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise JudgeRuntimeUnavailableError(
                f"judge runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise JudgeRuntimeUnavailableError(
            "no judge local runtime installed; install the judge local runtime package first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise JudgeRuntimeConflictError(
            "multiple judge runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_judge_runtime(*, resolved_config: Any, runtime_name: str | None = None) -> JudgeRuntime:
    factory = resolve_judge_runtime_factory(runtime_name)
    return factory.create_runtime(resolved_config=resolved_config)


def diagnose_judge_runtime(runtime_name: str | None = None) -> JudgeRuntimeHealth:
    factory = resolve_judge_runtime_factory(runtime_name)
    return factory.diagnose()
