from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from munk.agent_base.llm import prepare_llm_transcript_path
from munk.agent_runtime import AgentRuntimeEvent, CancelController
from munk.reviewing.models import ReviewRequest
from munk.reviewing.runtime import ReviewManagedPaths, ReviewRuntimeContext
from munk.services.operations.service import OperationTracker
from munk.services.running.paths import create_unique_run_dir


class TrackerReviewProgressSink:
    def __init__(self, tracker: OperationTracker) -> None:
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
    def __init__(self, tracker: OperationTracker) -> None:
        self._tracker = tracker

    def is_cancel_requested(self) -> bool:
        return self._tracker.should_cancel()


@dataclass(frozen=True)
class ReviewHostManagedPaths:
    root_dir: Path
    review_result_path: Path
    review_orchestration_path: Path
    diagnostics_path: Path
    artifact_manifest_path: Path


@dataclass(frozen=True)
class BuiltReviewRuntimeContext:
    runtime_context: ReviewRuntimeContext
    host_paths: ReviewHostManagedPaths


def build_review_runtime_context(*, tracker: OperationTracker, request: ReviewRequest) -> BuiltReviewRuntimeContext:
    root_dir = request.artifact_path or create_unique_run_dir(prefix="review_run")
    root_dir.mkdir(parents=True, exist_ok=True)
    return BuiltReviewRuntimeContext(
        runtime_context=ReviewRuntimeContext(
            operation_id=tracker.operation_id,
            managed_paths=ReviewManagedPaths(
                root_dir=root_dir,
                review_request_path=root_dir / "review_request.json",
                retrieval_path=root_dir / "retrieval.json",
                llm_transcript_path=prepare_llm_transcript_path(root_dir),
            ),
            progress=TrackerReviewProgressSink(tracker),
        ),
        host_paths=ReviewHostManagedPaths(
            root_dir=root_dir,
            review_result_path=root_dir / "review_result.json",
            review_orchestration_path=root_dir / "review_orchestration.json",
            diagnostics_path=root_dir / "diagnostics.json",
            artifact_manifest_path=root_dir / "artifact_manifest.json",
        ),
    )


def build_review_cancel_controller(*, tracker: OperationTracker) -> CancelController:
    return TrackerCancelController(tracker)
