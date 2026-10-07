from __future__ import annotations

import json
from typing import Any, cast

from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from munk.optimizing.models import OptimizeRequest
from munk.shared_tools.prompt_seed import (
    build_post_run_prompt_seed,
    build_prompt_size_diagnostics,
    maybe_degrade_prompt_seed,
)
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
        "Start from the compact evidence_seed. Use read tools when you need attempt detail, history tails, or decision-trace detail.",
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
        self.last_prompt: str = ""
        self.last_prompt_diagnostics: dict[str, object] = {}
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
        user_prompt = self._build_user_prompt(request)
        if user_prompt and isinstance(user_prompt[0], TextContent):
            self.last_prompt = user_prompt[0].content
            degraded = False
            try:
                payload = json.loads(self.last_prompt)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                degraded = bool(payload.get("prompt_degraded"))
                seed = payload.get("evidence_seed")
                if isinstance(seed, dict) and seed.get("degraded"):
                    degraded = True
            self.last_prompt_diagnostics = build_prompt_size_diagnostics(self.last_prompt, degraded=degraded)
        result = run_agent_sync_compatible(self._agent, user_prompt=user_prompt, deps=deps)
        self.last_tool_calls = list(deps.tool_calls)
        return result.output

    @staticmethod
    def _build_user_prompt(request: OptimizeRequest) -> list[UserContent]:
        guidance = request.current_ai_guidance.model_dump(mode="json") if request.current_ai_guidance is not None else {}
        evidence_seed = build_post_run_prompt_seed(
            request.structured_evidence if isinstance(request.structured_evidence, dict) else {},
            include_tails=True,
        )
        evidence_seed, degraded = maybe_degrade_prompt_seed(evidence_seed)
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
            "evidence_seed": evidence_seed,
            "available_artifacts": sorted(request.artifacts.keys()),
            "requirements": {
                "only_patch_target_fields": list(request.trigger.optimization_fields),
                "do_not_modify_core_case": True,
                "prefer_compact_lists": True,
                "use_read_tools_for_detail": True,
            },
        }
        if degraded:
            payload["prompt_degraded"] = True
        return [TextContent(content=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))]
