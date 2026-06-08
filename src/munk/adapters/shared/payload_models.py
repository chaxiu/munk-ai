from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from munk.app import AppTarget
from munk.app_assets.models import AppProfile
from munk.execution.models import CaseExecutionAttempt, ExecutionOutcome, JudgeEvidence
from munk.services.operations.models import OperationEventRecord


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
    progress: dict[str, Any] = Field(default_factory=dict)
    result: RunCaseResultData | dict[str, Any] | None = None
    artifact_manifest_path: str | None = None
    repro_dir: str | None = None
    primary_artifact_ids: list[str] = Field(default_factory=list)
    artifact_manifest_version: int | None = None
    schema_versions: dict[str, str] = Field(default_factory=dict)
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


class OperationEventsData(BaseModel):
    operation_id: str
    after_seq: int
    limit: int
    next_after_seq: int
    items: list[OperationEventRecord] = Field(default_factory=list)


class ScheduleRunSummaryData(BaseModel):
    schedule_run_id: str
    scheduled_for: str
    status: str
    operation_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    triggered_at: str | None = None
    finished_at: str | None = None


class ScheduleSummaryData(BaseModel):
    schedule_id: str
    name: str
    app_id: str
    plan_ids: list[str] = Field(default_factory=list)
    device_ref: str
    timezone: str
    cron_expr: str
    enabled: bool
    next_run_at: str | None = None
    last_run_at: str | None = None
    created_at: str
    updated_at: str


class ScheduleDetailData(ScheduleSummaryData):
    latest_operation_id: str | None = None
    active_schedule_run_id: str | None = None
    queued_run_count: int = 0
    headless: bool = False
    fail_fast: bool = False
    artifact_path: str | None = None
    assets_root: str | None = None
    runtime_overrides: dict[str, Any] = Field(default_factory=dict)
    recent_runs: list[ScheduleRunSummaryData] = Field(default_factory=list)


class ScheduleListData(BaseModel):
    items: list[ScheduleSummaryData] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


class ScheduleRunListData(BaseModel):
    schedule_id: str
    items: list[ScheduleRunSummaryData] = Field(default_factory=list)


class DeviceDescriptorData(BaseModel):
    platform: str
    device_ref: str
    display_name: str
    kind: str
    availability: str
    is_booted: bool | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class DeviceListData(BaseModel):
    items: list[DeviceDescriptorData] = Field(default_factory=list)


class AppListItemData(BaseModel):
    app_id: str
    app_name: str | None = None
    platform: str
    entry_identity: str | None = None
    introduction_exists: bool = True
    plan_count: int = 0
    case_count: int = 0


class AppListData(BaseModel):
    items: list[AppListItemData] = Field(default_factory=list)


class AppDetailData(BaseModel):
    profile: AppProfile
    introduction_markdown: str
    app_knowledge_content: str | None = None
    app_knowledge_exists: bool = False
    app_target: AppTarget
    plan_count: int = 0
    case_count: int = 0


class DashboardSummaryData(BaseModel):
    plan_count: int = 0
    case_count: int = 0
    recent_run_count: int = 0


class PlanLatestRunSummaryData(BaseModel):
    operation_id: str
    status: str
    verification_verdict: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class PlanListItemData(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    source: str
    version: str
    case_count: int = 0
    updated_at: str
    latest_run: PlanLatestRunSummaryData | None = None


class PlanListData(BaseModel):
    items: list[PlanListItemData] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


class CaseBriefData(BaseModel):
    case_id: str
    title: str
    intent: str
    is_core_case: bool
    runner_goal: str
    start_mode: str
    start_page_id: str | None = None


class PlanDetailData(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    source: str
    version: str
    case_count: int = 0
    cases: list[CaseBriefData] = Field(default_factory=list)


class LatestOptimizeOperationData(BaseModel):
    operation_id: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    summary: str | None = None
    patched_fields: list[str] = Field(default_factory=list)
    error_message: str | None = None


class CaseDetailData(BaseModel):
    app_id: str
    plan_id: str
    plan_source: str
    plan_version: str
    case_id: str
    title: str
    intent: str
    preconditions: list[str] = Field(default_factory=list)
    expected: list[str] = Field(default_factory=list)
    procedure: list[str] = Field(default_factory=list)
    post_action: list[str] = Field(default_factory=list)
    is_core_case: bool
    runner_goal: str
    start_mode: str
    start_page_id: str | None = None
    max_steps: int | None = None
    max_seconds: float | None = None
    latest_optimize: LatestOptimizeOperationData | None = None


class CaseSearchItemData(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    case_id: str
    ordinal: int
    title: str
    intent: str
    runner_goal: str
    is_core_case: bool
    start_mode: str
    start_page_id: str | None = None
    max_steps: int | None = None
    max_seconds: float | None = None


class CaseSearchData(BaseModel):
    items: list[CaseSearchItemData] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0
