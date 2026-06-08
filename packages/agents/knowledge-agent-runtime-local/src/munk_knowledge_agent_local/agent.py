from __future__ import annotations

from typing import Any, cast

from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from munk.knowledge_agent.models import KnowledgeAgentRequest, KnowledgeAgentResult
from pydantic_ai import Agent

from munk.config.defaults import MUNK_CODE_DEFAULTS
from munk.config.schema import OutputStrategy

from .prompt import SYSTEM_PROMPT, build_knowledge_agent_prompt_payload, build_knowledge_agent_user_prompt
from .tool_models import KnowledgeToolDeps
from .tools import register_knowledge_agent_tools


class PydanticAiKnowledgeAgent:
    def __init__(
        self,
        *,
        model: Any,
        output_strategy: OutputStrategy = "auto",
        max_tokens: int = MUNK_CODE_DEFAULTS.knowledge.max_tokens,
        temperature: float = MUNK_CODE_DEFAULTS.knowledge.temperature,
    ) -> None:
        output_spec = build_structured_output_spec(KnowledgeAgentResult, output_strategy=output_strategy)
        self.last_tool_calls: list[str] = []
        self.last_prompt = ""
        self._agent = Agent(
            model=cast(Any, model),
            deps_type=KnowledgeToolDeps,
            output_type=output_spec.output_type,
            system_prompt=append_system_prompt_suffix(SYSTEM_PROMPT, output_spec.system_prompt_suffix),
            name="pydantic_knowledge_agent",
            model_settings={
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        register_knowledge_agent_tools(self._agent)

    def generate_candidates(self, request: KnowledgeAgentRequest, *, deps: KnowledgeToolDeps) -> KnowledgeAgentResult:
        prompt = build_knowledge_agent_user_prompt(request)
        self.last_prompt = build_knowledge_agent_prompt_payload(request)
        result = run_agent_sync_compatible(self._agent, user_prompt=prompt, deps=deps)
        self.last_tool_calls = list(deps.tool_calls)
        return result.output
