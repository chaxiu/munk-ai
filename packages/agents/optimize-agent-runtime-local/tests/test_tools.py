from __future__ import annotations

import json
from pathlib import Path

from munk.optimizing import OptimizeExecutionSummary, OptimizeRequest, OptimizeTrigger
from munk.testing import AiGuidance
from munk_optimize_local.agent import PydanticAiOptimizeAgent
from munk_optimize_local.tools import OptimizeToolDeps


def _build_request() -> OptimizeRequest:
    return OptimizeRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="Save profile",
        intent="Save profile",
        runner_goal="Save profile",
        current_ai_guidance=AiGuidance(
            interaction_hints=["Prefer visible save button"],
            judge_hints=["Do not fail only because toast fades quickly"],
        ),
        execution_summary=OptimizeExecutionSummary(verdict="failed"),
        trigger=OptimizeTrigger(
            needs_optimization=True,
            optimization_fields=["interaction_hints", "judge_hints"],
            optimization_reason="runner and judge both showed ambiguity",
        ),
        artifact_payloads={
            "attempts": [{"attempt_index": 0, "summary": "first try"}],
            "history": [{"event_type": "workflow_finished"}],
            "retry_handoffs": [{"message": "look for save button"}],
            "judge_result": {"optimization_reason": "runner and judge both showed ambiguity"},
            "decision_trace": [{"step": 1, "decision": "retry"}],
        },
        run_dir=Path("/tmp/run"),
    )


def test_optimize_tool_deps_supports_multi_field_guidance_reads() -> None:
    deps = OptimizeToolDeps(
        request=_build_request(),
        step_summaries={0: {"step_index": 0, "summary": "tap save"}},
        step_screens={0: {"step_index": 0, "nodes": ["Save"]}},
        step_transitions={0: {"step_index": 0, "screen_changed": True}},
        step_images={},
    )

    payload = deps.read_fields(["interaction_hints", "judge_hints"])

    assert payload["interaction_hints"] == ["Prefer visible save button"]
    assert payload["judge_hints"] == ["Do not fail only because toast fades quickly"]


def test_optimize_tool_deps_reads_history_payloads() -> None:
    deps = OptimizeToolDeps(
        request=_build_request(),
        step_summaries={0: {"step_index": 0, "summary": "tap save"}},
        step_screens={0: {"step_index": 0, "nodes": ["Save"]}},
        step_transitions={0: {"step_index": 0, "screen_changed": True}},
        step_images={},
    )

    payload = json.loads(deps.read_step_summary(0))

    assert payload["summary"] == "tap save"


def test_optimize_agent_prompt_includes_structured_evidence() -> None:
    prompt = PydanticAiOptimizeAgent._build_user_prompt(_build_request())
    payload = json.loads(prompt[0].content)

    assert payload["structured_evidence"]["judge_result"]["optimization_reason"] == "runner and judge both showed ambiguity"
    assert payload["structured_evidence"]["decision_trace"][0]["decision"] == "retry"
