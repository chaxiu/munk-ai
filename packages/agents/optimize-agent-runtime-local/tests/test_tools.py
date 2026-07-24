from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast

from munk.optimizing import OptimizeExecutionSummary, OptimizeRequest, OptimizeTrigger
from munk.testing import AiGuidance
from munk_optimize_local.agent import PydanticAiOptimizeAgent
from munk_optimize_local.service import _build_step_summaries
from munk_optimize_local.tools import OptimizeToolDeps, register_optimize_tools


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
        structured_evidence={
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


def test_optimize_agent_prompt_uses_evidence_seed_instead_of_full_structured_evidence() -> None:
    prompt = PydanticAiOptimizeAgent._build_user_prompt(_build_request())
    payload = json.loads(prompt[0].content)

    assert "structured_evidence" not in payload
    assert payload["evidence_seed"]["judge_result"]["optimization_reason"] == (
        "runner and judge both showed ambiguity"
    )
    assert payload["evidence_seed"]["attempts_overview"][0]["attempt_index"] == 0
    assert "read_tools_hint" in payload["evidence_seed"]
    assert payload["requirements"]["use_read_tools_for_detail"] is True


class _CapturingAgent:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., object]] = {}

    def tool(self, func: Callable[..., object]) -> Callable[..., object]:
        self.tools[func.__name__] = func
        return func


def test_register_optimize_tools_includes_shared_case_run_evidence_tools() -> None:
    agent = _CapturingAgent()
    register_optimize_tools(cast(Any, agent))

    assert {
        "read_judge_result",
        "read_attempts_overview",
        "read_attempt_summary",
        "read_retry_handoffs",
        "read_event_history_tail",
        "read_decision_trace_tail",
        "read_artifact_manifest",
    }.issubset(set(agent.tools))


def test_optimize_tool_deps_reads_case_run_evidence_payloads() -> None:
    deps = OptimizeToolDeps(
        request=_build_request(),
        step_summaries={},
        step_screens={},
        step_transitions={},
        step_images={},
    )
    agent = _CapturingAgent()
    register_optimize_tools(cast(Any, agent))

    overview = json.loads(
        cast(Callable[..., str], agent.tools["read_attempts_overview"])(SimpleNamespace(deps=deps))
    )
    history = json.loads(
        cast(Callable[..., str], agent.tools["read_event_history_tail"])(SimpleNamespace(deps=deps), last_n=1)
    )

    assert overview["attempts"][0]["attempt_index"] == 0
    assert history["entries"] == [{"event_type": "workflow_finished"}]
    assert deps.tool_calls == ["read_attempts_overview", "read_event_history_tail"]


def test_build_step_summaries_prefers_attempt_timeline_runner_history_shape() -> None:
    payload = _build_step_summaries(
        [
            {
                "attempt_index": 1,
                "runner_history": [
                    {"step_index": 0, "summary": "open form"},
                    {"step_index": 1, "summary": "submit form"},
                ],
            }
        ]
    )

    assert payload[0]["summary"] == "open form"
    assert payload[1]["summary"] == "submit form"
