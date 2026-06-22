from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.execution.models import (
    PlanCaseExecutionItem,
    PlanExecutionRequest,
    PlanExecutionStatus,
)
from munk.services.operations.models import OperationStatus, VerificationVerdict
from munk.token_usage import TokenUsage

RunCaseBatchKind = Literal["single_plan_multi_case"]
RunPlanBatchKind = Literal["single_device_multi_plan"]
RunPlansBatchKind = Literal["single_device_multi_plan"]


class RunCaseOperationRequest(PlanExecutionRequest):
    case_id: str
    case_title: str | None = None
    batch_kind: RunCaseBatchKind | None = None


class RunPlanOperationRequest(PlanExecutionRequest):
    batch_kind: RunPlanBatchKind | None = None


class RunPlansOperationRequest(RunPlansCliRequest):
    pass


class RunPlansChildSummary(BaseModel):
    operation_id: str
    plan_id: str | None = None
    title: str
    status: OperationStatus
    verification_verdict: VerificationVerdict = None
    position_index: int | None = None
    position_label: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    token_usage: TokenUsage | None = None


class RunPlansAggregate(BaseModel):
    total_children: int
    queued_children: int
    running_children: int
    succeeded_children: int
    failed_children: int
    cancelled_children: int
    completed_children: int
    current_child_operation_id: str | None = None
    current_child_plan_id: str | None = None
    current_child_title: str | None = None
    token_usage: TokenUsage | None = None


class RunPlansProgressPayload(BaseModel):
    phase: str
    batch_kind: RunPlansBatchKind = "single_device_multi_plan"
    total_children: int
    completed_children: int
    current_child_operation_id: str | None = None
    current_child_plan_id: str | None = None
    current_child_title: str | None = None
    last_child_operation_id: str | None = None
    last_child_plan_id: str | None = None
    last_child_title: str | None = None
    verification_verdict: VerificationVerdict = None


class RunPlansResultPayload(BaseModel):
    app_id: str
    device_ref: str | None = None
    batch_kind: RunPlansBatchKind = "single_device_multi_plan"
    plan_ids: list[str]
    total_children: int
    completed_children: int
    stopped_early: bool = False
    verification_verdict: VerificationVerdict = None
    token_usage: TokenUsage | None = None
    children: list[RunPlansChildSummary]
    aggregate: RunPlansAggregate


class RunPlanOperationData(BaseModel):
    plan_id: str
    verification_status: PlanExecutionStatus
    total_cases: int
    passed_cases: int
    failed_cases: int
    inconclusive_cases: int
    stopped_early: bool
    summary_path: str
    report_path: str
    items: list[PlanCaseExecutionItem]
    token_usage: TokenUsage | None = None


class RunPlanOperationResultPayload(RunPlanOperationData):
    artifacts: dict[str, str]


class RunCaseChildSummary(BaseModel):
    operation_id: str
    plan_id: str | None = None
    case_id: str | None = None
    title: str
    status: OperationStatus
    verification_verdict: VerificationVerdict = None
    position_index: int | None = None
    position_label: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    token_usage: TokenUsage | None = None


class RunPlanProgressPayload(BaseModel):
    phase: str
    current_child_operation_id: str | None = None
    current_child_case_id: str | None = None
    current_child_title: str | None = None
    last_child_operation_id: str | None = None
    last_child_case_id: str | None = None
    last_child_title: str | None = None


class RunCaseOperationProgressPayload(BaseModel):
    orchestration_status: str | None = None
    current_attempt: int | None = None
    retry_count: int | None = None
    runner_event_type: str | None = None
    verification_verdict: VerificationVerdict = None


class RunCaseChildOperationProgressPayload(BaseModel):
    phase: str
    parent_operation_id: str
    position_label: str | None = None
    case_id: str
    case_title: str | None = None
    verification_verdict: VerificationVerdict = None


class RunPlanBatchChildStartedPayload(BaseModel):
    operation_id: str
    case_id: str
    title: str
    position_label: str | None = None


class RunCaseOperationStartedPayload(BaseModel):
    parent_operation_id: str
    case_id: str
    case_title: str | None = None
    position_label: str | None = None


class RunPlanChildOperationProgressPayload(BaseModel):
    phase: str
    parent_operation_id: str
    position_label: str | None = None
    verification_verdict: VerificationVerdict = None


class RunPlansBatchStartedPayload(BaseModel):
    app_id: str
    device_ref: str | None = None
    plan_ids: list[str]
    total_children: int


class RunPlansBatchChildStartedPayload(BaseModel):
    operation_id: str
    plan_id: str
    title: str
    parent_operation_id: str | None = None
    position_label: str | None = None


class RunPlansBatchStoppedEarlyPayload(BaseModel):
    plan_id: str
    operation_id: str


class RunPlansBatchFinishedPayload(BaseModel):
    total_children: int
    completed_children: int
    verification_verdict: VerificationVerdict = None
    stopped_early: bool = False


class PostRunChildOperationEventPayload(BaseModel):
    child_kind: str
    case_id: str
    operation_id: str | None = None
    request_path: str | None = None
    error: str | None = None
    optimization_fields: list[str] = Field(default_factory=list)
    trigger_source: str | None = None
    trigger_signals: list[str] = Field(default_factory=list)
    source_attempt_index: int | None = None
    judge_result_path: str | None = None
