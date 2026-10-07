from __future__ import annotations

from munk.knowledge_agent import (
    KnowledgeAgentRuntimeUnavailableError,
    create_knowledge_agent_runtime,
    diagnose_knowledge_agent_runtime,
)


def resolve_knowledge_agent_runtime(*, resolved_config: object | None = None):
    try:
        return create_knowledge_agent_runtime(resolved_config=resolved_config)
    except LookupError as exc:
        raise KnowledgeAgentRuntimeUnavailableError(str(exc)) from exc


def knowledge_agent_runtime_health():
    return diagnose_knowledge_agent_runtime()
