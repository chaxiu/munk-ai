from __future__ import annotations

from typing import Any

from munk.knowledge_agent import KnowledgeAgentRuntimeHealth

from .service import KnowledgeAgentRuntimeService


class LocalKnowledgeAgentRuntime:
    runtime_id = "local"

    def __init__(self, *, resolved_config: Any) -> None:
        self._service = KnowledgeAgentRuntimeService(resolved_config=resolved_config)

    def generate_candidates(self, request, *, context, cancel_controller=None):  # noqa: ANN001
        return self._service.generate_candidates(
            request,
            context=context,
            cancel_controller=cancel_controller,
        )


class LocalKnowledgeAgentRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config: Any) -> LocalKnowledgeAgentRuntime:
        return LocalKnowledgeAgentRuntime(resolved_config=resolved_config)

    def diagnose(self) -> KnowledgeAgentRuntimeHealth:
        return KnowledgeAgentRuntimeHealth(
            runtime_id=self.runtime_id,
            status="ok",
            message="knowledge agent local runtime is available",
        )


def build_knowledge_agent_runtime_factory() -> LocalKnowledgeAgentRuntimeFactory:
    return LocalKnowledgeAgentRuntimeFactory()
