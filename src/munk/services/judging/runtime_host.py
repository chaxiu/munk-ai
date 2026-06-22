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
from munk.artifacts import (
    ARTIFACT_ID_ANNOTATED_SCREENSHOTS,
    ARTIFACT_ID_ARTIFACT_MANIFEST,
    ARTIFACT_ID_DECISION_TRACE,
    ARTIFACT_ID_LLM_TRANSCRIPT,
    ARTIFACT_ID_OBSERVATION_DIFFS,
    ARTIFACT_ID_OBSERVATION_FRAMES,
    ARTIFACT_ID_OBSERVATION_TREE,
    ARTIFACT_ID_RAW_SCREENSHOTS,
    ARTIFACT_ID_RUNNER_HISTORY,
    ARTIFACT_ID_RUNNER_ISSUES,
    ARTIFACT_ID_RUNNER_MEMORY,
    ARTIFACT_ID_RUNTIME_LOGS,
)
from munk.services.events import RunEvent, serialize_run_event_payload
from munk.services.operations.runtime_event_sinks import TrackerAgentRuntimeTimelineSink


class JudgeTrackerLike(Protocol):
    @property
    def operation_id(self) -> str | None: ...

    def append_agent_runtime_event(self, event: AgentRuntimeEvent) -> None: ...

    def append_timeline_event(
        self,
        *,
        event_type: str,
        message: str | None,
        agent_role: str,
        timeline_scope: str,
        timeline_phase: str,
        summary: str | None = None,
        attempt_index: int | None = None,
        timestamp: str | None = None,
        parent_operation_id: str | None = None,
        child_operation_id: str | None = None,
        app_id: str | None = None,
        plan_id: str | None = None,
        case_id: str | None = None,
        data: dict[str, object] | None = None,
    ) -> None: ...

    def append_event(self, *, event_type: str, message: str | None, data: dict[str, object] | None = None) -> None: ...

    def update_progress(self, **progress: object) -> None: ...

    def should_cancel(self) -> bool: ...


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
                data=serialize_run_event_payload(event),
            )
            for event in events
        ],
        evidence_bundle=JudgeEvidenceBundle(
            runner_history_path=_path_or_none(artifacts.get(ARTIFACT_ID_RUNNER_HISTORY)),
            runner_memory_path=_path_or_none(artifacts.get(ARTIFACT_ID_RUNNER_MEMORY)),
            runner_issues_path=_path_or_none(artifacts.get(ARTIFACT_ID_RUNNER_ISSUES)),
            decision_trace_path=_path_or_none(artifacts.get(ARTIFACT_ID_DECISION_TRACE)),
            runtime_logs_path=_path_or_none(artifacts.get(ARTIFACT_ID_RUNTIME_LOGS)),
            observation_frames_path=_path_or_none(artifacts.get(ARTIFACT_ID_OBSERVATION_FRAMES)),
            observation_diffs_path=_path_or_none(artifacts.get(ARTIFACT_ID_OBSERVATION_DIFFS)),
            observation_tree_path=_path_or_none(artifacts.get(ARTIFACT_ID_OBSERVATION_TREE)),
            raw_screenshots_path=_path_or_none(artifacts.get(ARTIFACT_ID_RAW_SCREENSHOTS)),
            annotated_screenshots_path=_path_or_none(artifacts.get(ARTIFACT_ID_ANNOTATED_SCREENSHOTS)),
            llm_transcript_path=_path_or_none(artifacts.get(ARTIFACT_ID_LLM_TRANSCRIPT)),
            artifact_manifest_path=_path_or_none(artifacts.get(ARTIFACT_ID_ARTIFACT_MANIFEST)),
        ),
    )


def build_judge_runtime_context(
    *,
    run_dir: Path,
    tracker: JudgeTrackerLike | None,
    attempt_index: int,
) -> BuiltJudgeRuntimeContext:
    run_dir.mkdir(parents=True, exist_ok=True)
    progress = TrackerAgentRuntimeTimelineSink(tracker) if tracker is not None else None
    return BuiltJudgeRuntimeContext(
        runtime_context=JudgeRuntimeContext(
            operation_id=tracker.operation_id if tracker is not None else None,
            attempt_index=attempt_index,
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
