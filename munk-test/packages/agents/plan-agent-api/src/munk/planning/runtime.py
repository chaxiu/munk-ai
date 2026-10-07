from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol

from munk.agent_runtime.control import CancelController
from munk.agent_runtime.events import AgentEventSink
from munk.planning.errors import PlanRuntimeConflictError, PlanRuntimeUnavailableError
from munk.planning.health import PlanRuntimeHealth
from munk.shared_tools import KnowledgeToolProvider
from munk.token_usage import TokenUsage
from pydantic import BaseModel, Field

from munk.planning.models import ChangePlanInput, RequirementInput, RequirementPlan

ENTRY_POINT_GROUP = "munk.plan.runtimes"


PlanRequest = RequirementInput | ChangePlanInput


def empty_strings() -> list[str]:
    return []


class PlanRuntimeResultData(BaseModel):
    plan: RequirementPlan


class PlanRuntimeOutput(BaseModel):
    result_data: PlanRuntimeResultData
    started_at: str
    duration_ms: int
    warning_summary: list[str] = Field(default_factory=empty_strings)
    token_usage: TokenUsage | None = None


@dataclass(frozen=True)
class PlanManagedPaths:
    root_dir: Path
    request_dump_path: Path
    llm_transcript_path: Path | None


@dataclass(frozen=True)
class PlanResolvedAppContext:
    app_id: str
    platform: str
    identity_label: str
    introduction: str
    knowledge_tools: KnowledgeToolProvider


@dataclass(frozen=True)
class PlanRuntimeContext:
    operation_id: str | None
    managed_paths: PlanManagedPaths
    app_context: PlanResolvedAppContext
    progress: AgentEventSink | None = None


class PlanRuntime(Protocol):
    def plan(
        self,
        request: PlanRequest,
        *,
        context: PlanRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> PlanRuntimeOutput: ...


class PlanRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self, *, resolved_config: Any) -> PlanRuntime: ...

    def diagnose(self) -> PlanRuntimeHealth: ...


def list_plan_runtime_factories() -> dict[str, PlanRuntimeFactory]:
    factories: dict[str, PlanRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_plan_runtime_factory(runtime_name: str | None = None) -> PlanRuntimeFactory:
    factories = list_plan_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise PlanRuntimeUnavailableError(
                f"plan runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise PlanRuntimeUnavailableError(
            "no plan local runtime installed; install the plan local runtime package first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise PlanRuntimeConflictError(
            "multiple plan runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_plan_runtime(*, resolved_config: Any, runtime_name: str | None = None) -> PlanRuntime:
    factory = resolve_plan_runtime_factory(runtime_name)
    return factory.create_runtime(resolved_config=resolved_config)


def diagnose_plan_runtime(runtime_name: str | None = None) -> PlanRuntimeHealth:
    factory = resolve_plan_runtime_factory(runtime_name)
    return factory.diagnose()
