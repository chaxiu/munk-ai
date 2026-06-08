from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Protocol

from munk.agent_runtime.control import CancelController

from .errors import KnowledgeAgentRuntimeConflictError, KnowledgeAgentRuntimeUnavailableError
from .health import KnowledgeAgentRuntimeHealth
from .models import KnowledgeAgentRequest, KnowledgeAgentResult, KnowledgeAgentRuntimeContext

ENTRY_POINT_GROUP = "munk.knowledge_agent.runtimes"


class KnowledgeAgentRuntime(Protocol):
    def generate_candidates(
        self,
        request: KnowledgeAgentRequest,
        *,
        context: KnowledgeAgentRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeAgentResult: ...


class KnowledgeAgentRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self, *, resolved_config: Any) -> KnowledgeAgentRuntime: ...

    def diagnose(self) -> KnowledgeAgentRuntimeHealth: ...


def list_knowledge_agent_runtime_factories() -> dict[str, KnowledgeAgentRuntimeFactory]:
    factories: dict[str, KnowledgeAgentRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_knowledge_agent_runtime_factory(runtime_name: str | None = None) -> KnowledgeAgentRuntimeFactory:
    factories = list_knowledge_agent_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise KnowledgeAgentRuntimeUnavailableError(
                f"knowledge agent runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise KnowledgeAgentRuntimeUnavailableError(
            "no knowledge agent local runtime installed; install the knowledge agent local runtime package first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise KnowledgeAgentRuntimeConflictError(
            "multiple knowledge agent runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_knowledge_agent_runtime(
    *,
    resolved_config: Any,
    runtime_name: str | None = None,
) -> KnowledgeAgentRuntime:
    factory = resolve_knowledge_agent_runtime_factory(runtime_name)
    return factory.create_runtime(resolved_config=resolved_config)


def diagnose_knowledge_agent_runtime(runtime_name: str | None = None) -> KnowledgeAgentRuntimeHealth:
    factory = resolve_knowledge_agent_runtime_factory(runtime_name)
    return factory.diagnose()
