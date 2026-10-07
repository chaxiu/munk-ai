from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from munk.execution.models import CaseExecutionResult, JudgeVerdict
from munk.recording import RecordingSession
from munk.services.operations.models import now_iso


class RecordingSessionOperationRequest(BaseModel):
    recording_id: str
    app_id: str
    entry_identity: str | None = None
    device_ref: str | None = None


class RecordingAnalysisOperationRequest(BaseModel):
    recording_id: str
    app_id: str
    case_id: str | None = None


class RecordingSessionProgress(BaseModel):
    recording_id: str
    status: str
    latest_frame_seq: int | None = None
    latest_event_count: int = 0
    latest_timeline_count: int = 0
    updated_at: str


class RecordingAnalysisProgress(BaseModel):
    recording_id: str
    phase: str
    analysis_status: str
    total_steps: int = 0
    completed_steps: int = 0
    current_step_seq: int | None = None
    updated_at: str


class RecordingSessionTerminalResult(BaseModel):
    recording_id: str
    status: str


class RecordingReplayOperationRequest(BaseModel):
    recording_id: str
    app_id: str
    case_id: str
    device_ref: str | None = None
    entry_identity: str | None = None
    test_case_path: str


class RecordingReplayProgress(BaseModel):
    recording_id: str
    status: str
    case_id: str
    source_recording_case_path: str | None = None
    verification_verdict: JudgeVerdict = None


class RecordingReplayOperationResult(CaseExecutionResult):
    recording_id: str


def build_recording_session_operation_request_payload(session: RecordingSession) -> dict[str, Any]:
    payload = {
        "recording_id": session.recording_id,
        "app_id": session.app_id,
        "entry_identity": session.app_target.entry_identity,
        "device_ref": session.device_ref,
    }
    RecordingSessionOperationRequest.model_validate(payload)
    return payload


def build_recording_analysis_operation_request_payload(
    *,
    recording_id: str,
    app_id: str,
    case_id: str | None,
) -> dict[str, Any]:
    payload = {
        "recording_id": recording_id,
        "app_id": app_id,
        "case_id": case_id,
    }
    RecordingAnalysisOperationRequest.model_validate(payload)
    return payload


def build_recording_session_progress_payload(
    *,
    session: RecordingSession,
    latest_event_count: int,
    latest_timeline_count: int,
    updated_at: str | None = None,
) -> dict[str, Any]:
    payload = RecordingSessionProgress(
        recording_id=session.recording_id,
        status=session.status,
        latest_frame_seq=session.latest_frame_seq,
        latest_event_count=latest_event_count,
        latest_timeline_count=latest_timeline_count,
        updated_at=updated_at or now_iso(),
    )
    return payload.model_dump(mode="json")


def build_recording_analysis_progress_payload(
    *,
    recording_id: str,
    phase: str,
    analysis_status: str,
    total_steps: int = 0,
    completed_steps: int = 0,
    current_step_seq: int | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    payload = RecordingAnalysisProgress(
        recording_id=recording_id,
        phase=phase,
        analysis_status=analysis_status,
        total_steps=total_steps,
        completed_steps=completed_steps,
        current_step_seq=current_step_seq,
        updated_at=updated_at or now_iso(),
    )
    return payload.model_dump(mode="json")


def build_recording_session_terminal_result_payload(*, recording_id: str, status: str) -> dict[str, Any]:
    payload = RecordingSessionTerminalResult(recording_id=recording_id, status=status)
    return payload.model_dump(mode="json")


def build_recording_replay_operation_request_payload(
    *,
    recording_id: str,
    session: RecordingSession,
    case_id: str,
    test_case_path: Path,
) -> dict[str, Any]:
    payload = {
        "recording_id": recording_id,
        "app_id": session.app_id,
        "case_id": case_id,
        "device_ref": session.device_ref,
        "entry_identity": session.app_target.entry_identity,
        "test_case_path": str(test_case_path),
    }
    RecordingReplayOperationRequest.model_validate(payload)
    return payload


def build_recording_replay_progress_payload(
    *,
    recording_id: str,
    status: str,
    case_id: str,
    source_recording_case_path: Path | None = None,
    verification_verdict: JudgeVerdict = None,
) -> dict[str, Any]:
    payload = RecordingReplayProgress(
        recording_id=recording_id,
        status=status,
        case_id=case_id,
        source_recording_case_path=str(source_recording_case_path) if source_recording_case_path is not None else None,
        verification_verdict=verification_verdict,
    )
    return payload.model_dump(mode="json")


def build_recording_replay_operation_result_payload(
    *,
    recording_id: str,
    result: CaseExecutionResult,
) -> dict[str, Any]:
    payload = RecordingReplayOperationResult(recording_id=recording_id, **result.model_dump(mode="json"))
    return payload.model_dump(mode="json")


def source_recording_id_from_payloads(*payloads: object) -> str | None:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        raw_recording_id = payload.get("recording_id")
        if isinstance(raw_recording_id, str) and raw_recording_id.strip():
            return raw_recording_id
    return None
