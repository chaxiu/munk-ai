from __future__ import annotations

import json
from typing import Any, cast

from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from munk.optimizing.models import OptimizeRequest
from pydantic_ai import Agent
from pydantic_ai.messages import TextContent, UserContent

from munk.config.defaults import MUNK_CODE_DEFAULTS
from munk.config.schema import OutputStrategy

from .agent_models import OptimizeAgentOutput
from .tools import OptimizeToolDeps, register_optimize_tools

SYSTEM_PROMPT = "\n".join(
    [
        "You are an optimize agent for mobile UI automation test cases.",
        "First determine whether the failure pattern is mainly a case-quality problem or a runner/runtime/tooling problem.",
        "If the evidence points to runner/runtime/tooling issues rather than case-quality issues, prefer returning no patch.",
        "Improve ai_guidance for future executions without changing the core business intent.",
        "Only update fields that have strong support from the run evidence and judge trigger.",
        "Prioritize structured evidence from artifact_payloads before exploring optional artifact tools.",
        "Prefer small, durable guidance updates over verbose rewrites.",
        "Do not duplicate existing guidance unless a clearer version is needed.",
        "Return only the structured output.",
    ]
)


class PydanticAiOptimizeAgent:
    def __init__(
        self,
        *,
        model: Any,
        output_strategy: OutputStrategy = "auto",
        max_tokens: int = MUNK_CODE_DEFAULTS.optimize.max_tokens,
        temperature: float = MUNK_CODE_DEFAULTS.optimize.temperature,
    ) -> None:
        output_spec = build_structured_output_spec(OptimizeAgentOutput, output_strategy=output_strategy)
        self.last_tool_calls: list[str] = []
        self._agent = Agent(
            model=cast(Any, model),
            deps_type=OptimizeToolDeps,
            output_type=output_spec.output_type,
            system_prompt=append_system_prompt_suffix(SYSTEM_PROMPT, output_spec.system_prompt_suffix),
            name="pydantic_case_optimize_agent",
            model_settings={
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        register_optimize_tools(self._agent)

    def optimize(self, request: OptimizeRequest, *, deps: OptimizeToolDeps) -> OptimizeAgentOutput:
        result = run_agent_sync_compatible(self._agent, user_prompt=self._build_user_prompt(request), deps=deps)
        self.last_tool_calls = list(deps.tool_calls)
        return result.output

    @staticmethod
    def _build_user_prompt(request: OptimizeRequest) -> list[UserContent]:
        guidance = request.current_ai_guidance.model_dump(mode="json") if request.current_ai_guidance is not None else {}
        payload = {
            "case": {
                "case_id": request.case_id,
                "title": request.case_title,
                "intent": request.intent,
                "runner_goal": request.runner_goal,
                "expected": list(request.expected),
            },
            "trigger": request.trigger.model_dump(mode="json"),
            "trigger_source": request.trigger.source,
            "trigger_signals": list(request.trigger.signals),
            "source_attempt_index": request.trigger.source_attempt_index,
            "execution_summary": request.execution_summary.model_dump(mode="json"),
            "current_ai_guidance": guidance,
            "structured_evidence": request.artifact_payloads,
            "available_artifacts": sorted(request.artifacts.keys()),
            "requirements": {
                "only_patch_target_fields": list(request.trigger.optimization_fields),
                "do_not_modify_core_case": True,
                "prefer_compact_lists": True,
            },
        }
        return [TextContent(content=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))]
