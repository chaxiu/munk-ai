from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class RecordingIdEventPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recording_id: str


class RecordingStartedEventPayload(RecordingIdEventPayload):
    bridge_ws_url: str


class RecordingTapObservedEventPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str
    kind: str
    payload: dict[str, Any]


class RecordingInteractionRecordedEventPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entry_id: str
    kind: str
    forwarding_event_id: str | None = None
    recording_event_id: str | None = None
    before_observation_id: str | None = None
    after_observation_id: str | None = None
    after_stabilized: bool | None = None


class RecordingCaseExportedEventPayload(RecordingIdEventPayload):
    case_id: str
    case_path: str
    plan_id: str | None = None
    plan_path: str | None = None


class RecordingReplayLinkedEventPayload(RecordingIdEventPayload):
    operation_id: str
    verdict: str | None = None


class RecordingReplayStartedEventPayload(RecordingIdEventPayload):
    case_id: str


class RecordingReplayCompletedEventPayload(RecordingReplayStartedEventPayload):
    verdict: str | None = None
    run_dir: str


class RecordingBridgeCleanupFailedEventPayload(RecordingIdEventPayload):
    error: str
    status: str


class RecordingAnalysisStatusEventPayload(RecordingIdEventPayload):
    analysis_status: str | None = None


class RecordingAnalysisBundleLoadedEventPayload(RecordingIdEventPayload):
    total_steps: int


class RecordingAnalysisStepEventPayload(RecordingIdEventPayload):
    current_step_seq: int | None = None
    completed_steps: int | None = None
    total_steps: int | None = None
