from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from munk.agent_runtime import AgentRuntimeEvent, CancelController
from munk.execution.models import CaseExecutionRequest, ExecutionOutcome
from munk.judging.models import (
    JudgeEventRecord,
    JudgeEvidenceBundle,
    JudgeExecutionSummary,
    JudgeManagedPaths,
    JudgeRequest,
    JudgeRuntimeContext,
)
from munk.services.events import RunEvent


class JudgeTrackerLike(Protocol):
    @property
    def operation_id(self) -> str | None: ...

    def append_event(self, *, event_type: str, message: str | None, data: dict[str, object] | None = None) -> None: ...

    def update_progress(self, **progress: object) -> None: ...

    def should_cancel(self) -> bool: ...


class TrackerJudgeProgressSink:
    def __init__(self, tracker: JudgeTrackerLike) -> None:
        self._tracker = tracker

    def emit(self, event: AgentRuntimeEvent) -> None:
        data = dict(event.data)
        data["lifecycle_state"] = event.lifecycle_state
        data["agent_role"] = event.agent_role
        data["timestamp"] = event.timestamp
        self._tracker.append_event(event_type=event.event_type, message=event.message, data=data)
        self._tracker.update_progress(
            lifecycle_state=event.lifecycle_state,
            agent_role=event.agent_role,
            event_timestamp=event.timestamp,
        )


class TrackerCancelController(CancelController):
    def __init__(self, tracker: JudgeTrackerLike) -> None:
        self._tracker = tracker

    def is_cancel_requested(self) -> bool:
        return self._tracker.should_cancel()


@dataclass(frozen=True)
class JudgeHostManagedPaths:
    root_dir: Path
    judge_result_path: Path
    diagnostics_path: Path


@dataclass(frozen=True)
class BuiltJudgeRuntimeContext:
    runtime_context: JudgeRuntimeContext
    host_paths: JudgeHostManagedPaths


def build_judge_request(
    *,
    request: CaseExecutionRequest,
    execution: ExecutionOutcome,
    events: list[RunEvent],
    artifacts: dict[str, str],
) -> JudgeRequest:
    return JudgeRequest(
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=request.case.case_id,
        case_title=request.case.title,
        intent=request.case.intent,
        preconditions=list(request.case.preconditions),
        expected=list(request.case.expected),
        runner_goal=request.case.runner_goal,
        ai_guidance=request.case.ai_guidance.model_copy(deep=True) if request.case.ai_guidance is not None else None,
        execution=JudgeExecutionSummary.model_validate(execution.model_dump(mode="json")),
        events=[
            JudgeEventRecord(
                event_type=event.type.value,
                timestamp=event.timestamp,
                message=event.message,
                data=dict(event.data),
            )
            for event in events
        ],
        evidence_bundle=JudgeEvidenceBundle(
            runner_history_path=_path_or_none(artifacts.get("runner_history")),
            runner_memory_path=_path_or_none(artifacts.get("runner_memory")),
            decision_trace_path=_path_or_none(artifacts.get("decision_trace")),
            runtime_logs_path=_path_or_none(artifacts.get("runtime_logs")),
            observation_frames_path=_path_or_none(artifacts.get("observation_frames")),
            observation_diffs_path=_path_or_none(artifacts.get("observation_diffs")),
            observation_tree_path=_path_or_none(artifacts.get("observation_tree")),
            raw_screenshots_path=_path_or_none(artifacts.get("raw_screenshots")),
            annotated_screenshots_path=_path_or_none(artifacts.get("annotated_screenshots")),
            llm_transcript_path=_path_or_none(artifacts.get("llm_transcript")),
            artifact_manifest_path=_path_or_none(artifacts.get("artifact_manifest")),
        ),
    )


def build_judge_runtime_context(
    *,
    run_dir: Path,
    tracker: JudgeTrackerLike | None,
) -> BuiltJudgeRuntimeContext:
    run_dir.mkdir(parents=True, exist_ok=True)
    progress = TrackerJudgeProgressSink(tracker) if tracker is not None else None
    return BuiltJudgeRuntimeContext(
        runtime_context=JudgeRuntimeContext(
            operation_id=tracker.operation_id if tracker is not None else None,
            managed_paths=JudgeManagedPaths(
                root_dir=run_dir,
                judge_request_path=run_dir / "judge_request.json",
                judge_prompt_path=run_dir / "judge_prompt.txt",
                tool_calls_path=run_dir / "judge_tool_calls.json",
                evidence_selection_path=run_dir / "judge_evidence_selection.json",
                llm_transcript_path=run_dir / "judge_llm_transcript.jsonl",
            ),
            progress=progress,
        ),
        host_paths=JudgeHostManagedPaths(
            root_dir=run_dir,
            judge_result_path=run_dir / "judge_result.json",
            diagnostics_path=run_dir / "diagnostics.json",
        ),
    )


def build_judge_cancel_controller(*, tracker: JudgeTrackerLike | None) -> CancelController | None:
    if tracker is None:
        return None
    return TrackerCancelController(tracker)


def _path_or_none(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value)
