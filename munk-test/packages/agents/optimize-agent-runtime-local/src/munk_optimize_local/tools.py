from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from munk.shared_tools.ai_guidance import AiGuidanceFieldName, register_ai_guidance_tools
from munk.shared_tools.case_run_evidence import (
    build_artifact_manifest_payload,
    build_attempt_summary_payload,
    build_attempts_overview_payload,
    build_decision_trace_tail_payload,
    build_event_history_tail_payload,
    build_retry_handoffs_payload,
    build_unavailable_payload,
    register_case_run_evidence_tools,
)
from munk.shared_tools.run_evidence import register_run_evidence_tools
from pydantic_ai import Agent

from .image_payloads import load_screenshot_binary_image


@dataclass
class OptimizeToolDeps:
    request: Any
    step_summaries: dict[int, dict[str, object]]
    step_screens: dict[int, dict[str, object]]
    step_transitions: dict[int, dict[str, object]]
    step_images: dict[int, str]
    step_annotated_images: dict[int, str] = field(default_factory=dict)
    tool_budget: int = 6
    tool_calls: list[str] = field(default_factory=list)
    vl_max_side: int = 1024

    def consume_tool_budget(self, tool_name: str) -> bool:
        if self.tool_budget <= 0:
            return False
        self.tool_budget -= 1
        self.tool_calls.append(tool_name)
        return True

    def tool_budget_exhausted_message(self) -> str:
        return "tool budget exhausted; make the best optimization decision from the current context"

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
        if not self.consume_tool_budget("read_step_summary"):
            return self.tool_budget_exhausted_message()
        payload = self.step_summaries.get(step_index)
        if payload is None:
            return f"unknown step index: {step_index}"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def read_step_screen(self, step_index: int) -> str:
        if not self.consume_tool_budget("read_step_screen"):
            return self.tool_budget_exhausted_message()
        payload = self.step_screens.get(step_index)
        if payload is None:
            return f"unknown step index: {step_index}"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def read_step_transition(self, step_index: int) -> str:
        if not self.consume_tool_budget("read_step_transition"):
            return self.tool_budget_exhausted_message()
        payload = self.step_transitions.get(step_index)
        if payload is None:
            return f"unknown step index: {step_index}"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def read_step_screenshot(self, step_index: int | None = None, annotated: bool = True):  # noqa: ANN202
        from pydantic_ai.messages import ToolReturn

        if not self.consume_tool_budget("read_step_screenshot"):
            return self.tool_budget_exhausted_message()
        images = self.step_annotated_images if annotated else self.step_images
        if step_index is None:
            step_index = max(images.keys()) if images else None
        if step_index is None:
            return "no screenshots available"
        image_path = images.get(step_index)
        if image_path is None:
            return f"unknown step index: {step_index}"
        kind = "annotated" if annotated else "raw"
        image = load_screenshot_binary_image(
            image_path,
            identifier=f"optimize_step_{step_index:04d}_{kind}",
            vl_max_side=self.vl_max_side,
        )
        if image is None:
            return f"{kind} screenshot unavailable for step index: {step_index}"
        return ToolReturn(
            return_value=f"{kind} screenshot loaded for step {step_index}",
            content=[f"{kind.title()} screenshot for step={step_index}", image],
        )

    def _structured_evidence(self) -> dict[str, object]:
        structured = getattr(self.request, "structured_evidence", None)
        return dict(structured) if isinstance(structured, dict) else {}

    def read_judge_result(self) -> str:
        judge_result = self._structured_evidence().get("judge_result")
        if not isinstance(judge_result, dict):
            return build_unavailable_payload("judge_result")
        return json.dumps(judge_result, ensure_ascii=False, sort_keys=True)

    def read_attempts_overview(self) -> str:
        return build_attempts_overview_payload(self._structured_evidence().get("attempts"))

    def read_attempt_summary(self, attempt_index: int) -> str:
        return build_attempt_summary_payload(self._structured_evidence().get("attempts"), attempt_index)

    def read_retry_handoffs(self) -> str:
        return build_retry_handoffs_payload(self._structured_evidence().get("retry_handoffs"))

    def read_event_history_tail(self, last_n: int) -> str:
        return build_event_history_tail_payload(
            self._structured_evidence().get("history"),
            last_n=last_n,
        )

    def read_decision_trace_tail(self, last_n: int) -> str:
        return build_decision_trace_tail_payload(
            self._structured_evidence().get("decision_trace"),
            last_n=last_n,
        )

    def read_artifact_manifest(self) -> str:
        artifacts = getattr(self.request, "artifacts", None)
        available = sorted(artifacts.keys()) if isinstance(artifacts, dict) else []
        manifest = self._structured_evidence().get("artifact_manifest")
        return build_artifact_manifest_payload(manifest, available_artifacts=available)


def register_optimize_tools(agent: Agent[OptimizeToolDeps, object]) -> None:
    register_ai_guidance_tools(agent, provider_getter=lambda deps: deps)
    register_run_evidence_tools(agent, provider_getter=lambda deps: deps)
    register_case_run_evidence_tools(agent, provider_getter=lambda deps: deps)
