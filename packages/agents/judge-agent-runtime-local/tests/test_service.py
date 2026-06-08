from __future__ import annotations

import json
from pathlib import Path

from munk.agent_base.llm.transcript import append_transcript_entry
from munk.judging.models import (
    JudgeExecutionSummary,
    JudgeManagedPaths,
    JudgeRequest,
    JudgeRuntimeContext,
)
from munk_judge_local.agent_models import JudgeAgentOutput
from munk_judge_local.errors import OperationCancelledError
from munk_judge_local.service import JudgeRuntimeService

from tests.helpers.config import build_resolved_config


class FakeJudgeAgent:
    def __init__(self, *, model: object, output_strategy: object) -> None:  # noqa: ARG002
        self.last_prompt = "judge prompt"
        self.last_tool_calls = ["read_step_summary"]

    def judge(self, evidence_pack):  # noqa: ANN001, ANN201
        assert evidence_pack.case_id == "case-1"
        append_transcript_entry(
            kind="llm_request",
            provider="test",
            model="judge-test",
            payload={"case_id": evidence_pack.case_id},
        )
        return JudgeAgentOutput(
            verdict="passed",
            summary="judge passed",
            reason="expected state is visible",
            supporting_evidence_ids=["execution"],
        )


class RecordingProgressSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:  # noqa: ANN001
        self.events.append(event)


class CancelControllerStub:
    def __init__(self, decisions: list[bool]) -> None:
        self._decisions = list(decisions)

    def is_cancel_requested(self) -> bool:
        if self._decisions:
            return self._decisions.pop(0)
        return False


def build_request(tmp_path: Path) -> JudgeRequest:
    return JudgeRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="Case One",
        intent="Open settings",
        expected=["Settings page is visible"],
        runner_goal="Open settings page",
        execution=JudgeExecutionSummary(status="completed", steps_completed=2),
        evidence_bundle={},
    )


def build_context(tmp_path: Path, *, progress=None) -> JudgeRuntimeContext:  # noqa: ANN001
    return JudgeRuntimeContext(
        operation_id="op-1",
        managed_paths=JudgeManagedPaths(
            root_dir=tmp_path,
            judge_request_path=tmp_path / "judge_request.json",
            judge_prompt_path=tmp_path / "judge_prompt.txt",
            tool_calls_path=tmp_path / "judge_tool_calls.json",
            evidence_selection_path=tmp_path / "judge_evidence_selection.json",
            llm_transcript_path=tmp_path / "judge_llm_transcript.jsonl",
        ),
        progress=progress,
    )


def test_judge_runtime_service_writes_runtime_artifacts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("munk_judge_local.service.build_pydantic_ai_model", lambda judge_config, config: object())
    monkeypatch.setattr("munk_judge_local.service.PydanticAiJudgeAgent", FakeJudgeAgent)
    service = JudgeRuntimeService(resolved_config=build_resolved_config(tmp_path))

    output = service.judge(
        build_request(tmp_path),
        context=build_context(tmp_path),
    )

    assert output.result_data.verdict == "passed"
    assert (tmp_path / "judge_request.json").exists()
    assert (tmp_path / "judge_prompt.txt").read_text(encoding="utf-8") == "judge prompt"
    assert (tmp_path / "judge_llm_transcript.jsonl").exists()
    tool_calls_payload = json.loads((tmp_path / "judge_tool_calls.json").read_text(encoding="utf-8"))
    assert tool_calls_payload["tool_calls"] == ["read_step_summary"]


def test_judge_runtime_service_emits_minimal_lifecycle_events(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("munk_judge_local.service.build_pydantic_ai_model", lambda judge_config, config: object())
    monkeypatch.setattr("munk_judge_local.service.PydanticAiJudgeAgent", FakeJudgeAgent)
    sink = RecordingProgressSink()
    service = JudgeRuntimeService(resolved_config=build_resolved_config(tmp_path))

    output = service.judge(
        build_request(tmp_path),
        context=build_context(tmp_path, progress=sink),
    )

    assert output.result_data.verdict == "passed"
    assert [event.event_type for event in sink.events] == [
        "agent_started",
        "judge_context_loaded",
        "judge_agent_completed",
        "agent_ended",
    ]


def test_judge_runtime_service_raises_on_cooperative_cancel(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("munk_judge_local.service.build_pydantic_ai_model", lambda judge_config, config: object())
    monkeypatch.setattr("munk_judge_local.service.PydanticAiJudgeAgent", FakeJudgeAgent)
    sink = RecordingProgressSink()
    service = JudgeRuntimeService(resolved_config=build_resolved_config(tmp_path))

    try:
        service.judge(
            build_request(tmp_path),
            context=build_context(tmp_path, progress=sink),
            cancel_controller=CancelControllerStub([True]),
        )
    except OperationCancelledError as exc:
        assert str(exc) == "operation cancelled cooperatively"
    else:  # pragma: no cover - defensive
        raise AssertionError("expected cooperative cancel to raise")

    assert [event.event_type for event in sink.events] == [
        "agent_started",
        "judge_context_loaded",
        "agent_canceled",
    ]
