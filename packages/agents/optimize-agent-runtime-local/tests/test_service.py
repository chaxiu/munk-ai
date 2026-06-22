from __future__ import annotations

import json
from pathlib import Path

from munk.optimizing import (
    OptimizeExecutionSummary,
    OptimizeManagedPaths,
    OptimizeRequest,
    OptimizeRuntimeContext,
    OptimizeTrigger,
)
from munk.testing import AiGuidance
from munk_optimize_local.agent_models import OptimizeAgentOutput, OptimizeFieldPatchOutput
from munk_optimize_local.service import OptimizeRuntimeService


class RecordingProgressSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:  # noqa: ANN001
        self.events.append(event)


class _FakeOptimizeAgent:
    def __init__(self) -> None:
        self.last_tool_calls = ["read_attempts_overview", "read_step_summary"]
        self.last_prompt = "optimize prompt"

    def optimize(self, request: OptimizeRequest, *, deps) -> OptimizeAgentOutput:  # noqa: ANN001
        assert request.case_id == "case-1"
        assert 1 in deps.step_summaries
        deps.tool_calls.extend(["read_attempts_overview", "read_step_summary"])
        return OptimizeAgentOutput(
            summary="optimize result ready",
            patched_fields=[
                OptimizeFieldPatchOutput(
                    field_name="judge_hints",
                    replace_with=["Clarify end-state wording"],
                    reason="judge wording was ambiguous",
                )
            ],
        )


def test_optimize_runtime_service_emits_canonical_timeline_events_and_writes_artifacts(tmp_path: Path) -> None:
    service = OptimizeRuntimeService(resolved_config=None, agent=_FakeOptimizeAgent())
    request = _build_request(tmp_path)
    sink = RecordingProgressSink()
    context = OptimizeRuntimeContext(
        operation_id="op-1",
        attempt_index=2,
        managed_paths=OptimizeManagedPaths(
            root_dir=tmp_path / "optimize",
            prompt_path=tmp_path / "optimize" / "optimize_prompt.txt",
            tool_calls_path=tmp_path / "optimize" / "optimize_tool_calls.json",
            llm_transcript_path=tmp_path / "optimize" / "optimize_llm_transcript.jsonl",
        ),
        progress=sink,
    )
    context.managed_paths.root_dir.mkdir(parents=True, exist_ok=True)

    result = service.optimize(request, context=context)

    assert result.summary == "optimize result ready"
    assert result.patched_fields[0].field_name == "judge_hints"
    assert json.loads(result.artifacts["tool_calls"]) == [
        "read_attempts_overview",
        "read_step_summary",
    ]
    assert [event.event_type for event in sink.events] == [
        "optimize_started",
        "optimize_evidence_ready",
        "optimize_tool_called",
        "optimize_tool_called",
        "optimize_tool_calls_completed",
        "optimize_result_generated",
        "optimize_result_ready",
        "optimize_completed",
    ]
    for event in sink.events:
        assert event.agent_role == "optimize"
        assert event.timeline_scope == "child_operation"
        assert event.attempt_index == 2
        assert event.app_id == "app-1"
        assert event.plan_id == "plan-1"
        assert event.case_id == "case-1"
    assert context.managed_paths.prompt_path.read_text(encoding="utf-8") == "optimize prompt"
    tool_calls_payload = json.loads(context.managed_paths.tool_calls_path.read_text(encoding="utf-8"))
    assert tool_calls_payload["tool_calls"] == ["read_attempts_overview", "read_step_summary"]


def _build_request(tmp_path: Path) -> OptimizeRequest:
    return OptimizeRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="Save profile",
        intent="Save profile",
        runner_goal="Save profile",
        current_ai_guidance=AiGuidance(judge_hints=["Prefer stable end state wording"]),
        execution_summary=OptimizeExecutionSummary(verdict="failed"),
        trigger=OptimizeTrigger(
            needs_optimization=True,
            optimization_fields=["judge_hints"],
            optimization_reason="judge wording unclear",
            source="judge",
            signals=["retried_terminal_failure"],
            source_attempt_index=2,
        ),
        structured_evidence={
            "attempts": [
                {
                    "attempt_index": 2,
                    "artifacts": {
                        "runner_history": str(
                            _write_json(
                                tmp_path / "runner_history.json",
                                [
                                    {"step_index": 0, "summary": "open form"},
                                    {"step_index": 1, "summary": "submit form"},
                                ],
                            )
                        )
                    },
                }
            ]
        },
        artifacts={
            "observation_frames": str(_write_json(tmp_path / "frames.json", [{"step_index": 1, "nodes": ["Save"]}])),
            "observation_diffs": str(
                _write_json(tmp_path / "diffs.json", [{"step_index": 1, "screen_changed": True}])
            ),
        },
        run_dir=tmp_path / "run",
    )


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
