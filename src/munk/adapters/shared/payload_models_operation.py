from __future__ import annotations

from typing import Any, TypeAlias, cast

from pydantic import BaseModel, Field, ValidationError, model_validator

from munk.adapters.shared._payload_model_helpers import as_dict, int_field, string_field
from munk.adapters.shared.operation_event_payloads import (
    OperationEventPayloadData,
    parse_operation_event_payload,
)
from munk.execution.models import (
    CaseExecutionAttempt,
    ExecutionOutcome,
    JudgeEvidence,
    PhasedOperationResult,
)
from munk.recording.models import RecordingAnalysisResult
from munk.services.artifact_manifest_models import ArtifactSchemaVersions
from munk.services.operations.models import OperationEventRecord
from munk.services.knowledge.operation_payloads import KnowledgePostActionOperationResultPayload
from munk.services.optimization.operation_payloads import OptimizeCaseOperationResultPayload
from munk.services.recording.operation_payloads import (
    RecordingReplayOperationResult,
    RecordingSessionTerminalResult,
)
from munk.services.reviewing.operation_payloads import ReviewOperationResultPayload
from munk.services.running.operation_payloads import RunPlanOperationResultPayload, RunPlansResultPayload
from munk.services.verify_change_operation_payloads import VerifyChangeOperationResultPayload


class RunCaseResultData(BaseModel):
    schema_version: str | None = None
    app_id: str | None = None
    plan_id: str
    case_id: str
    status: str | None = None
    current_step: str | None = None
    final_decision: dict[str, Any] | None = None
    verdict: str
    execution: ExecutionOutcome
    run_dir: str
    artifacts: dict[str, str] = Field(default_factory=dict)
    summary: str | None = None
    judge_reason: str | None = None
    failure_hypothesis: str | None = None
    confidence: float | None = None
    missing_evidence: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[JudgeEvidence] = Field(default_factory=list)
    attempt_count: int = 0
    attempts: list[CaseExecutionAttempt] = Field(default_factory=list)
    event_history: list[dict[str, Any]] = Field(default_factory=list)
    supplemental_context: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class InteractiveSessionStateData(BaseModel):
    session_id: str
    status: str
    last_active_at: str | None = None
    expires_at: str | None = None
    idle_expires_at: str | None = None


class OperationProgressData(BaseModel):
    last_event_type: str | None = None
    phase: str | None = None
    stage: str | None = None
    status: str | None = None
    batch_kind: str | None = None
    verification_verdict: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    plan_name: str | None = None
    case_id: str | None = None
    case_title: str | None = None
    case_count: int | None = None
    case_index: int | None = None
    total_cases: int | None = None
    completed_cases: int | None = None
    current_case_id: str | None = None
    last_case_id: str | None = None
    target_case_count: int | None = None
    completed_case_count: int | None = None
    total_children: int | None = None
    completed_children: int | None = None
    current_child_operation_id: str | None = None
    current_child_case_id: str | None = None
    current_child_plan_id: str | None = None
    current_child_title: str | None = None
    last_child_operation_id: str | None = None
    last_child_case_id: str | None = None
    last_child_plan_id: str | None = None
    last_child_title: str | None = None
    plan_event_type: str | None = None
    verify_change_event_type: str | None = None
    lifecycle_state: str | None = None
    agent_role: str | None = None
    event_timestamp: str | None = None
    review_hint_enabled: bool | None = None
    review_required_case_count: int | None = None
    manual_case_count: int | None = None
    planner_case_count: int | None = None
    plan_path: str | None = None
    snapshot_path: str | None = None
    recording_id: str | None = None
    latest_frame_seq: int | None = None
    latest_event_count: int | None = None
    latest_timeline_count: int | None = None
    updated_at: str | None = None
    analysis_status: str | None = None
    total_steps: int | None = None
    completed_steps: int | None = None
    current_step_seq: int | None = None
    source_recording_case_path: str | None = None
    bridge_status: str | None = None
    replay_operation_id: str | None = None
    detached_pid: int | None = None
    background_mode: str | None = None
    interactive_session: InteractiveSessionStateData | None = None


OperationDetailResultData: TypeAlias = (
    RunCaseResultData
    | PhasedOperationResult
    | RunPlanOperationResultPayload
    | RunPlansResultPayload
    | VerifyChangeOperationResultPayload
    | ReviewOperationResultPayload
    | OptimizeCaseOperationResultPayload
    | KnowledgePostActionOperationResultPayload
    | RecordingSessionTerminalResult
    | RecordingReplayOperationResult
    | RecordingAnalysisResult
)


class TokenUsageData(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    request_count: int = 0
    provider: str | None = None
    model: str | None = None


class AttemptTokenUsageData(BaseModel):
    attempt_index: int
    runner_usage: TokenUsageData | None = None
    judge_usage: TokenUsageData | None = None
    total_usage: TokenUsageData | None = None


class SceneTokenUsageSummaryData(BaseModel):
    token_usage: TokenUsageData | None = None
    planning_usage: TokenUsageData | None = None
    execution_usage: TokenUsageData | None = None
    attempt_usages: list[AttemptTokenUsageData] = Field(default_factory=list)


class OperationChildItemData(BaseModel):
    operation_id: str
    kind: str | None = None
    run_type: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    title: str | None = None
    status: str
    verification_verdict: str | None = None
    position_index: int | None = None
    position_label: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    token_usage: TokenUsageData | None = None


class BatchRunAggregateData(BaseModel):
    total_children: int = 0
    queued_children: int = 0
    running_children: int = 0
    succeeded_children: int = 0
    failed_children: int = 0
    cancelled_children: int = 0
    completed_children: int = 0
    current_child_operation_id: str | None = None
    current_child_plan_id: str | None = None
    current_child_case_id: str | None = None
    current_child_title: str | None = None
    token_usage: TokenUsageData | None = None


class OperationChildrenData(BaseModel):
    operation_id: str
    items: list[OperationChildItemData] = Field(default_factory=list)


class OperationDetailData(BaseModel):
    operation_id: str
    kind: str
    run_type: str | None = None
    title: str | None = None
    platform: str | None = None
    phase: str | None = None
    target_label: str | None = None
    source_recording_id: str | None = None
    status: str
    verification_verdict: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    parent_operation_id: str | None = None
    batch_id: str | None = None
    position_index: int | None = None
    position_label: str | None = None
    pid: int | None = None
    cancel_requested: bool = False
    device_ref: str | None = None
    resource_scope: str | None = None
    conflict_reason: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    progress: OperationProgressData | None = None
    result: OperationDetailResultData | None = None
    artifact_manifest_path: str | None = None
    repro_dir: str | None = None
    primary_artifact_ids: list[str] = Field(default_factory=list)
    artifact_manifest_version: int | None = None
    schema_versions: ArtifactSchemaVersions = Field(default_factory=ArtifactSchemaVersions)
    diagnostics_path: str | None = None
    duration_ms: int | None = None
    failure_category: str | None = None
    warning_summary: list[str] = Field(default_factory=list)
    is_batch: bool = False
    batch_kind: str | None = None
    aggregate: BatchRunAggregateData | None = None
    current_child_operation_id: str | None = None
    current_child_case_id: str | None = None
    children_preview: list[OperationChildItemData] = Field(default_factory=list)
    token_usage: TokenUsageData | None = None
    planning_usage: TokenUsageData | None = None
    execution_usage: TokenUsageData | None = None
    attempt_usages: list[AttemptTokenUsageData] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_payloads(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = cast(dict[str, Any], dict(data))
        payload["progress"] = parse_operation_progress_payload(payload.get("progress"))
        payload["result"] = parse_operation_result_payload(
            kind=string_field(payload, "kind"),
            raw_payload=payload.get("result"),
        )
        return payload


class OperationSummaryData(BaseModel):
    operation_id: str
    kind: str
    run_type: str | None = None
    title: str | None = None
    platform: str | None = None
    phase: str | None = None
    target_label: str | None = None
    source_recording_id: str | None = None
    status: str
    verification_verdict: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    parent_operation_id: str | None = None
    batch_id: str | None = None
    position_index: int | None = None
    position_label: str | None = None
    device_ref: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class OperationListData(BaseModel):
    items: list[OperationSummaryData] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


class OperationEventItemData(BaseModel):
    seq: int
    operation_id: str
    timestamp: str
    event_type: str
    message: str | None = None
    agent_role: str | None = None
    timeline_scope: str | None = None
    timeline_phase: str | None = None
    attempt_index: int | None = None
    parent_operation_id: str | None = None
    child_operation_id: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    summary: str | None = None
    data_json: OperationEventPayloadData | None = None

    @classmethod
    def from_record(cls, record: OperationEventRecord) -> OperationEventItemData:
        data = as_dict(record.data_json)
        return cls(
            seq=record.seq,
            operation_id=record.operation_id,
            timestamp=record.timestamp,
            event_type=record.event_type,
            message=record.message,
            agent_role=string_field(data, "agent_role"),
            timeline_scope=string_field(data, "timeline_scope"),
            timeline_phase=string_field(data, "timeline_phase"),
            attempt_index=int_field(data, "attempt_index"),
            parent_operation_id=string_field(data, "parent_operation_id"),
            child_operation_id=string_field(data, "child_operation_id"),
            app_id=string_field(data, "app_id"),
            plan_id=string_field(data, "plan_id"),
            case_id=string_field(data, "case_id"),
            summary=string_field(data, "summary"),
            data_json=parse_operation_event_payload(event_type=record.event_type, raw_payload=data),
        )


class OperationEventsData(BaseModel):
    operation_id: str
    after_seq: int
    limit: int
    next_after_seq: int
    items: list[OperationEventItemData] = Field(default_factory=list)


def parse_operation_progress_payload(raw_payload: object) -> OperationProgressData | None:
    if not isinstance(raw_payload, dict) or not raw_payload:
        return None
    try:
        return OperationProgressData.model_validate(raw_payload)
    except ValidationError:
        return None


def parse_operation_result_payload(
    *,
    kind: str | None,
    raw_payload: object,
) -> OperationDetailResultData | None:
    if not isinstance(raw_payload, dict) or not raw_payload:
        return None
    model_type = result_model_for(kind=kind, raw_payload=raw_payload)
    if model_type is None:
        return None
    try:
        return cast(OperationDetailResultData, model_type.model_validate(raw_payload))
    except ValidationError:
        return None


def result_model_for(
    *,
    kind: str | None,
    raw_payload: dict[str, Any],
) -> type[BaseModel] | None:
    if kind == "plan":
        return PhasedOperationResult
    if kind == "run_case":
        return RunCaseResultData
    if kind == "run_plan":
        return RunPlanOperationResultPayload
    if kind == "run_plans":
        return RunPlansResultPayload
    if kind == "verify_change":
        return VerifyChangeOperationResultPayload
    if kind == "review":
        return ReviewOperationResultPayload
    if kind == "optimize_case":
        return OptimizeCaseOperationResultPayload
    if kind == "knowledge_post_action":
        return KnowledgePostActionOperationResultPayload
    if kind == "recording_analysis":
        return RecordingAnalysisResult
    if kind == "record_case":
        if "run_dir" in raw_payload and "plan_id" in raw_payload and "execution" in raw_payload:
            return RecordingReplayOperationResult
        return RecordingSessionTerminalResult
    return None
