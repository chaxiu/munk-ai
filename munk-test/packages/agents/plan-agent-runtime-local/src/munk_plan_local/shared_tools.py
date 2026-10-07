from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from munk.shared_tools import KnowledgeToolProvider, register_knowledge_tools
from pydantic_ai import Agent


@dataclass(frozen=True)
class PlanAppKnowledgeDeps:
    app_id: str
    knowledge_tools: KnowledgeToolProvider


def register_plan_app_knowledge_tools(agent: Agent[PlanAppKnowledgeDeps, Any]) -> None:
    register_knowledge_tools(
        agent,
        provider_getter=lambda deps: deps.knowledge_tools,
        include_submit_candidate=False,
    )
