from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable, cast

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
from pydantic_ai import Agent


@dataclass
class _Provider:
    tool_budget: int = 8
    tool_calls: list[str] = field(default_factory=list)
    judge_result: dict[str, object] = field(
        default_factory=lambda: {"verdict": "failed", "summary": "login failed"}
    )
    attempts: list[dict[str, object]] = field(
        default_factory=lambda: [
            {
                "attempt_index": 0,
                "verdict": "failed",
                "retry_reason": "element_not_found",
                "judge_reason": "button unresponsive",
                "execution": {"status": "failed", "stop_reason": "timeout", "error_type": "RunnerProtocolError"},
            }
        ]
    )
    retry_handoffs: list[dict[str, object]] = field(default_factory=lambda: [{"reason": "retry login"}])
    history: list[dict[str, object]] = field(
        default_factory=lambda: [{"type": "runner_step"}, {"type": "judge_completed"}]
    )
    decision_trace: list[dict[str, object]] = field(
        default_factory=lambda: [{"step": 1, "decision": "retry"}, {"step": 2, "decision": "stop"}]
    )
    manifest: dict[str, object] = field(default_factory=lambda: {"items": [{"artifact_id": "attempts"}]})
    available_artifacts: list[str] = field(default_factory=lambda: ["attempts", "history", "judge_result"])

    def consume_tool_budget(self, tool_name: str) -> bool:
        if self.tool_budget <= 0:
            return False
        self.tool_budget -= 1
        self.tool_calls.append(tool_name)
        return True

    def tool_budget_exhausted_message(self) -> str:
        return "tool budget exhausted"

    def read_judge_result(self) -> str:
        return json.dumps(self.judge_result, ensure_ascii=False, sort_keys=True)

    def read_attempts_overview(self) -> str:
        return build_attempts_overview_payload(self.attempts)

    def read_attempt_summary(self, attempt_index: int) -> str:
        return build_attempt_summary_payload(self.attempts, attempt_index)

    def read_retry_handoffs(self) -> str:
        return build_retry_handoffs_payload(self.retry_handoffs)

    def read_event_history_tail(self, last_n: int) -> str:
        return build_event_history_tail_payload(self.history, last_n=last_n)

    def read_decision_trace_tail(self, last_n: int) -> str:
        return build_decision_trace_tail_payload(self.decision_trace, last_n=last_n)

    def read_artifact_manifest(self) -> str:
        return build_artifact_manifest_payload(self.manifest, available_artifacts=self.available_artifacts)


def test_build_unavailable_payload_is_stable() -> None:
    payload = json.loads(build_unavailable_payload("attempts"))
    assert payload == {
        "artifact_id": "attempts",
        "reason": "artifact not provided",
        "status": "unavailable",
    }


def test_build_attempts_overview_payload_compacts_execution_fields() -> None:
    payload = json.loads(
        build_attempts_overview_payload(
            [
                {
                    "attempt_index": 1,
                    "verdict": "failed",
                    "retry_reason": "timeout",
                    "judge_reason": "no response",
                    "execution": {"status": "failed", "stop_reason": "timeout", "error_type": "TimeoutError"},
                }
            ]
        )
    )
    assert payload["attempts"][0]["attempt_index"] == 1
    assert payload["attempts"][0]["status"] == "failed"
    assert payload["attempts"][0]["error_type"] == "TimeoutError"


def test_build_attempt_summary_payload_returns_unknown_index() -> None:
    payload = json.loads(build_attempt_summary_payload([{"attempt_index": 0}], attempt_index=9))
    assert payload["status"] == "unavailable"
    assert "unknown attempt index" in payload["reason"]


def test_build_event_history_tail_payload_bounds_last_n() -> None:
    history = [{"index": index} for index in range(30)]
    payload = json.loads(build_event_history_tail_payload(history, last_n=100))
    assert len(payload["entries"]) == 20
    assert payload["entries"][-1]["index"] == 29


def test_build_decision_trace_tail_payload_bounds_last_n() -> None:
    entries = [{"step": index} for index in range(60)]
    payload = json.loads(build_decision_trace_tail_payload(entries, last_n=100))
    assert len(payload["entries"]) == 50
    assert payload["entries"][-1]["step"] == 59


def test_register_case_run_evidence_tools_exposes_shared_tool_names() -> None:
    agent: Agent[object, str] = Agent(model="test", output_type=str, defer_model_check=True)
    register_case_run_evidence_tools(agent, provider_getter=lambda deps: deps.provider)
    assert set(agent._function_toolset.tools) == {
        "read_judge_result",
        "read_attempts_overview",
        "read_attempt_summary",
        "read_retry_handoffs",
        "read_event_history_tail",
        "read_decision_trace_tail",
        "read_artifact_manifest",
    }


def test_register_case_run_evidence_tools_returns_provider_payloads() -> None:
    agent: Agent[object, str] = Agent(model="test", output_type=str, defer_model_check=True)
    register_case_run_evidence_tools(agent, provider_getter=lambda deps: deps.provider)
    tools = agent._function_toolset.tools
    deps = SimpleNamespace(provider=_Provider())

    read_judge_result = cast(Callable[..., str], tools["read_judge_result"].function)
    read_attempts_overview = cast(Callable[..., str], tools["read_attempts_overview"].function)
    read_attempt_summary = cast(Callable[..., str], tools["read_attempt_summary"].function)
    read_retry_handoffs = cast(Callable[..., str], tools["read_retry_handoffs"].function)
    read_event_history_tail = cast(Callable[..., str], tools["read_event_history_tail"].function)
    read_decision_trace_tail = cast(Callable[..., str], tools["read_decision_trace_tail"].function)
    read_artifact_manifest = cast(Callable[..., str], tools["read_artifact_manifest"].function)

    judge_payload = json.loads(read_judge_result(SimpleNamespace(deps=deps)))
    overview_payload = json.loads(read_attempts_overview(SimpleNamespace(deps=deps)))
    summary_payload = json.loads(read_attempt_summary(SimpleNamespace(deps=deps), attempt_index=0))
    handoffs_payload = json.loads(read_retry_handoffs(SimpleNamespace(deps=deps)))
    history_payload = json.loads(read_event_history_tail(SimpleNamespace(deps=deps), last_n=1))
    trace_payload = json.loads(read_decision_trace_tail(SimpleNamespace(deps=deps), last_n=1))
    manifest_payload = json.loads(read_artifact_manifest(SimpleNamespace(deps=deps)))

    assert judge_payload["summary"] == "login failed"
    assert overview_payload["attempts"][0]["retry_reason"] == "element_not_found"
    assert summary_payload["attempt_index"] == 0
    assert handoffs_payload["retry_handoffs"][0]["reason"] == "retry login"
    assert history_payload["entries"] == [{"type": "judge_completed"}]
    assert trace_payload["entries"] == [{"step": 2, "decision": "stop"}]
    assert manifest_payload["available_artifacts"] == ["attempts", "history", "judge_result"]


def test_register_case_run_evidence_tools_enforces_budget() -> None:
    agent: Agent[object, str] = Agent(model="test", output_type=str, defer_model_check=True)
    register_case_run_evidence_tools(agent, provider_getter=lambda deps: deps.provider)
    tools = agent._function_toolset.tools
    provider = _Provider(tool_budget=1)
    deps = SimpleNamespace(provider=provider)

    read_judge_result = cast(Callable[..., str], tools["read_judge_result"].function)
    read_retry_handoffs = cast(Callable[..., str], tools["read_retry_handoffs"].function)

    first = read_judge_result(SimpleNamespace(deps=deps))
    second = read_retry_handoffs(SimpleNamespace(deps=deps))

    assert "login failed" in first
    assert second == "tool budget exhausted"
    assert provider.tool_calls == ["read_judge_result"]
