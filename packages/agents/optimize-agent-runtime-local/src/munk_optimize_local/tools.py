from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from munk.shared_tools.ai_guidance import AiGuidanceFieldName, register_ai_guidance_tools
from munk.shared_tools.run_evidence import register_run_evidence_tools
from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

from .image_payloads import load_screenshot_binary_image


@dataclass
class OptimizeToolDeps:
    request: Any
    step_summaries: dict[int, dict[str, object]]
    step_screens: dict[int, dict[str, object]]
    step_transitions: dict[int, dict[str, object]]
    step_images: dict[int, str]
    tool_budget: int = 6
    tool_calls: list[str] = field(default_factory=list)
    vl_max_side: int = 1024

    def non_empty_fields(self) -> list[AiGuidanceFieldName]:
        guidance = self.request.current_ai_guidance
        if guidance is None:
            return []
        field_names: tuple[AiGuidanceFieldName, ...] = (
            "objective_clarifications",
            "preflight_checks",
            "interaction_hints",
            "disambiguation_rules",
            "recovery_hints",
            "judge_hints",
        )
        return [field_name for field_name in field_names if getattr(guidance, field_name)]

    def read_fields(self, fields: list[AiGuidanceFieldName]) -> dict[str, list[str]]:
        guidance = self.request.current_ai_guidance
        if guidance is None:
            return {}
        return {field_name: list(getattr(guidance, field_name)) for field_name in fields}

    def read_all(self) -> dict[str, list[str]]:
        return self.read_fields(self.non_empty_fields())

    def read_step_summary(self, step_index: int) -> str:
        if not _consume_budget(self, "read_step_summary"):
            return _budget_exhausted()
        payload = self.step_summaries.get(step_index)
        if payload is None:
            return f"unknown step index: {step_index}"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def read_step_screen(self, step_index: int) -> str:
        if not _consume_budget(self, "read_step_screen"):
            return _budget_exhausted()
        payload = self.step_screens.get(step_index)
        if payload is None:
            return f"unknown step index: {step_index}"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def read_step_transition(self, step_index: int) -> str:
        if not _consume_budget(self, "read_step_transition"):
            return _budget_exhausted()
        payload = self.step_transitions.get(step_index)
        if payload is None:
            return f"unknown step index: {step_index}"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def read_step_screen_raw_image(self, step_index: int):  # noqa: ANN202
        from pydantic_ai.messages import ToolReturn

        if not _consume_budget(self, "read_step_screen_raw_image"):
            return _budget_exhausted()
        image_path = self.step_images.get(step_index)
        if image_path is None:
            return f"unknown step index: {step_index}"
        image = load_screenshot_binary_image(
            image_path,
            identifier=f"optimize_step_{step_index:04d}_raw",
            vl_max_side=self.vl_max_side,
        )
        if image is None:
            return f"raw screenshot unavailable for step index: {step_index}"
        return ToolReturn(
            return_value=f"raw screenshot loaded for step {step_index}",
            content=[f"Raw screenshot for step={step_index}", image],
        )


def register_optimize_tools(agent: Agent[OptimizeToolDeps, object]) -> None:
    register_ai_guidance_tools(agent, provider_getter=lambda deps: deps)
    register_run_evidence_tools(agent, provider_getter=lambda deps: deps)

    @agent.tool
    def read_attempt_summary(ctx: PydanticRunContext[OptimizeToolDeps], attempt_index: int) -> str:
        """Read one attempt summary by index."""
        if not _consume_budget(ctx.deps, "read_attempt_summary"):
            return _budget_exhausted()
        attempts = ctx.deps.request.artifact_payloads.get("attempts", [])
        if not isinstance(attempts, list) or attempt_index < 0 or attempt_index >= len(attempts):
            return f"unknown attempt index: {attempt_index}"
        return json.dumps(attempts[attempt_index], ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_event_history_tail(ctx: PydanticRunContext[OptimizeToolDeps], last_n: int = 8) -> str:
        """Read the most recent event history entries."""
        if not _consume_budget(ctx.deps, "read_event_history_tail"):
            return _budget_exhausted()
        history = ctx.deps.request.artifact_payloads.get("history", [])
        if not isinstance(history, list):
            history = []
        bounded_last_n = max(1, min(last_n, 20))
        return json.dumps({"entries": history[-bounded_last_n:]}, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_retry_handoffs(ctx: PydanticRunContext[OptimizeToolDeps]) -> str:
        """Read retry handoff messages captured for the case."""
        if not _consume_budget(ctx.deps, "read_retry_handoffs"):
            return _budget_exhausted()
        handoffs = ctx.deps.request.artifact_payloads.get("retry_handoffs", [])
        return json.dumps({"retry_handoffs": handoffs}, ensure_ascii=False, sort_keys=True)


def _consume_budget(deps: OptimizeToolDeps, tool_name: str) -> bool:
    if deps.tool_budget <= 0:
        return False
    deps.tool_budget -= 1
    deps.tool_calls.append(tool_name)
    return True


def _budget_exhausted() -> str:
    return "tool budget exhausted; make the best optimization decision from the current context"
