from __future__ import annotations

import json
from typing import Any, Protocol

from munk.agent_base.llm import llm_transcript_scope
from munk.agent_base.output_strategy import resolve_output_strategy
from munk.agent_base.pydantic_model_factory import build_pydantic_ai_model
from munk.knowledge_agent import KnowledgeAgentRequest, KnowledgeAgentResult, KnowledgeAgentRuntimeContext

from munk.config import resolve_role_model_config

from .agent import PydanticAiKnowledgeAgent
from .tool_models import KnowledgeToolDeps


class KnowledgeAgentLike(Protocol):
    last_tool_calls: list[str]
    last_prompt: str

    def generate_candidates(self, request: KnowledgeAgentRequest, *, deps: KnowledgeToolDeps) -> KnowledgeAgentResult: ...


class KnowledgeAgentRuntimeService:
    def __init__(self, *, resolved_config: Any, agent: KnowledgeAgentLike | None = None) -> None:
        self._resolved_config = resolved_config
        self._agent = agent or self._build_agent(resolved_config)

    def generate_candidates(
        self,
        request: KnowledgeAgentRequest,
        *,
        context: KnowledgeAgentRuntimeContext,
        cancel_controller=None,  # noqa: ANN001
    ) -> KnowledgeAgentResult:
        del cancel_controller
        judge_result = request.evidence_bundle.judge_result
        artifacts = _build_artifacts(context)
        if judge_result.verdict == "passed":
            _write_json(context.managed_paths.tool_calls_path, {"tool_calls": []})
            context.managed_paths.prompt_path.write_text("knowledge agent skipped: verdict=passed\n", encoding="utf-8")
            return KnowledgeAgentResult(
                summary="knowledge agent skipped: passed case",
                skip_reason="verdict_passed",
                tool_calls=[],
                artifacts=artifacts,
            )
        deps = KnowledgeToolDeps(request=request)
        with llm_transcript_scope(context.managed_paths.llm_transcript_path):
            agent_output = self._agent.generate_candidates(request, deps=deps)
        tool_calls = list(self._agent.last_tool_calls)
        _write_json(context.managed_paths.tool_calls_path, {"tool_calls": tool_calls})
        context.managed_paths.prompt_path.write_text(self._agent.last_prompt, encoding="utf-8")
        return agent_output.model_copy(
            update={
                "tool_calls": tool_calls,
                "artifacts": artifacts,
            }
        )

    def _build_agent(self, resolved_config: Any) -> KnowledgeAgentLike:
        model_config = _resolve_knowledge_model_config(resolved_config)
        if model_config is None:
            raise ValueError("config must include a valid knowledge model configuration")
        model = build_pydantic_ai_model(model_config, config=resolved_config.config)
        return PydanticAiKnowledgeAgent(
            model=model,
            output_strategy=resolve_output_strategy(model_config),
        )


def _build_artifacts(context: KnowledgeAgentRuntimeContext) -> dict[str, str]:
    artifacts = {
        "knowledge_agent_prompt": str(context.managed_paths.prompt_path),
        "knowledge_agent_tool_calls": str(context.managed_paths.tool_calls_path),
    }
    if context.managed_paths.llm_transcript_path is not None:
        artifacts["knowledge_agent_llm_transcript"] = str(context.managed_paths.llm_transcript_path)
    return artifacts


def _resolve_knowledge_model_config(resolved_config: Any):  # noqa: ANN001
    if resolved_config is None:
        return None
    config = resolved_config.config
    agents = getattr(config, "agents", None)
    for role in ("knowledge", "review", "judge"):
        if role != "knowledge" and (agents is None or getattr(agents, role) is None):
            continue
        resolved = resolve_role_model_config(config, role=role)
        if resolved is not None:
            return resolved
    return resolve_role_model_config(config, role="knowledge")


def _write_json(path, payload: dict[str, object]) -> None:  # noqa: ANN001
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
