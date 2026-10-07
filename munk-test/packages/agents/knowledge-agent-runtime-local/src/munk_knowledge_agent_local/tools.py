from __future__ import annotations

from munk.shared_tools.case_run_evidence import register_case_run_evidence_tools
from pydantic_ai import Agent

from .tool_models import KnowledgeToolDeps


def register_knowledge_agent_tools(agent: Agent[KnowledgeToolDeps, object]) -> None:
    register_case_run_evidence_tools(agent, provider_getter=lambda deps: deps)
