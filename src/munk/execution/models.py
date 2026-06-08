from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from munk.app import AppTarget
from munk.judging.models import JudgeEvidence, JudgeVerdict
from munk.planning.models import ChangePlanInput
from munk.testing import TestCase
from munk.token_usage import TokenUsage

RuntimeOverrideValue = str | int | float | bool
ExecutionStatus = Literal["completed", "failed", "incomplete"]
PlanExecutionStatus = Literal["passed", "failed", "inconclusive", "stopped"]
OperationPhase = Literal["planned", "executed"]
CASE_EXECUTION_RESULT_SCHEMA_VERSION = "phase8.orchestrated_case_execution_result.v1"
WorkflowStatus = Literal[
    "pending",
    "ready",
    "running",
    "needs_retry",
    "escalated",
    "finished",
]


class CaseExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    case: TestCase
    app_id: str
    app_target: AppTarget
    device_ref: Optional[str] = None
    artifact_path: Optional[Path] = None
    assets_root: Optional[Path] = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=dict)


class ExecutionOutcome(BaseModel):
    status: ExecutionStatus
    stop_reason: Optional[str] = None
    steps_completed: int = 0
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    last_action_summary: Optional[str] = None
    # Historical field name kept for compatibility; semantics are target/app identity.
    last_target_identity: Optional[str] = None
    # Page/surface-level identity for the last observed screen.
    last_surface_identity: Optional[str] = None


def empty_strings() -> list[str]:
    return []


def empty_evidence() -> list[JudgeEvidence]:
    return []


def empty_artifacts() -> dict[str, str]:
    return {}


def empty_event_history() -> list[dict[str, object]]:
    return []


def empty_attempts() -> list["CaseExecutionAttempt"]:
    return []


def empty_metadata() -> dict[str, object]:
    return {}


class CaseExecutionAttempt(BaseModel):
    attempt_index: int
    runner_run_dir: Path
    execution: ExecutionOutcome
    verdict: JudgeVerdict
    summary: Optional[str] = None
    judge_reason: Optional[str] = None
    failure_hypothesis: Optional[str] = None
    confidence: Optional[float] = None
    missing_evidence: list[str] = Field(default_factory=empty_strings)
    supporting_evidence_ids: list[str] = Field(default_factory=empty_strings)
    evidence: list[JudgeEvidence] = Field(default_factory=empty_evidence)
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    retry_reason: Optional[str] = None
    retry_handoff_message: Optional[str] = None
    decision: dict[str, object] | None = None
    artifacts: dict[str, str] = Field(default_factory=empty_artifacts)
    runner_usage: TokenUsage | None = None
    judge_usage: TokenUsage | None = None
    total_usage: TokenUsage | None = None


class CaseExecutionResult(BaseModel):
    schema_version: str = CASE_EXECUTION_RESULT_SCHEMA_VERSION
    app_id: str | None = None
    plan_id: str
    case_id: str
    run_dir: Path
    status: WorkflowStatus = "finished"
    current_step: str | None = None
    final_decision: dict[str, object] | None = None
    execution: ExecutionOutcome
    verdict: JudgeVerdict
    summary: Optional[str] = None
    judge_reason: Optional[str] = None
    failure_hypothesis: Optional[str] = None
    confidence: Optional[float] = None
    missing_evidence: list[str] = Field(default_factory=empty_strings)
    supporting_evidence_ids: list[str] = Field(default_factory=empty_strings)
    evidence: list[JudgeEvidence] = Field(default_factory=empty_evidence)
    attempt_count: int = 0
    attempts: list[CaseExecutionAttempt] = Field(default_factory=empty_attempts)
    event_history: list[dict[str, object]] = Field(default_factory=empty_event_history)
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    metadata: dict[str, object] = Field(default_factory=empty_metadata)
    artifacts: dict[str, str] = Field(default_factory=empty_artifacts)
    token_usage: TokenUsage | None = None


class CaseRunRecord(BaseModel):
    request: CaseExecutionRequest
    result: CaseExecutionResult


def empty_plan_items() -> list["PlanCaseExecutionItem"]:
    return []


def empty_warning_summary() -> list[str]:
    return []


def empty_contract_versions() -> dict[str, str | None]:
    return {}


class PlanExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    plan_id: str
    app_target: AppTarget
    device_ref: Optional[str] = None
    artifact_path: Optional[Path] = None
    assets_root: Optional[Path] = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=dict)
    fail_fast: bool = False


class ChangeVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    provided_cases: list[TestCase] = Field(default_factory=list)
    enable_plan_agent: bool = False
    auto_run: bool = False
    change_summary: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    diff_text: str | None = None
    review_orchestration_path: Path | None = None
    requirement_doc_path: Path | None = None
    technical_doc_path: Path | None = None
    previous_report_path: Path | None = None
    previous_result_paths: list[Path] = Field(default_factory=list)
    app_target: AppTarget | None = None
    device_ref: Optional[str] = None
    artifact_path: Optional[Path] = None
    assets_root: Optional[Path] = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request(self) -> "ChangeVerificationRequest":
        if not self.provided_cases and not self.enable_plan_agent and self.review_orchestration_path is None:
            raise ValueError("provided_cases must not be empty when enable_plan_agent is false")
        if self.auto_run and self.app_target is None:
            raise ValueError("app_target must not be empty when auto_run is true")
        return self

    def to_change_plan_input(self) -> ChangePlanInput:
        return ChangePlanInput(
            app_id=self.app_id,
            change_summary=self.change_summary,
            changed_files=list(self.changed_files),
            diff_text=self.diff_text,
            review_orchestration_path=self.review_orchestration_path,
            requirement_doc_path=self.requirement_doc_path,
            technical_doc_path=self.technical_doc_path,
            previous_report_path=self.previous_report_path,
            previous_result_paths=list(self.previous_result_paths),
            assets_root=self.assets_root,
        )


class PlanCaseExecutionItem(BaseModel):
    case_id: str
    title: str
    operation_id: str | None = None
    status: str | None = None
    verdict: JudgeVerdict
    execution_status: ExecutionStatus
    judge_summary: Optional[str] = None
    stop_reason: Optional[str] = None
    run_dir: Path
    error_message: Optional[str] = None
    token_usage: TokenUsage | None = None


class PlanExecutionResult(BaseModel):
    app_id: str
    plan_id: str
    status: PlanExecutionStatus
    total_cases: int
    passed_cases: int
    failed_cases: int
    inconclusive_cases: int = 0
    stopped_early: bool = False
    items: list[PlanCaseExecutionItem] = Field(default_factory=empty_plan_items)
    summary_path: Path
    report_path: Path
    diagnostics_path: Path | None = None
    token_usage: TokenUsage | None = None


class GeneratedPlanResult(BaseModel):
    plan_name: str | None = None
    case_count: int
    plan_path: Path
    snapshot_path: Path
    planning_usage: TokenUsage | None = None


class ExecutedPlanResult(BaseModel):
    verification_status: PlanExecutionStatus
    total_cases: int
    passed_cases: int
    failed_cases: int
    inconclusive_cases: int = 0
    stopped_early: bool = False
    items: list[PlanCaseExecutionItem] = Field(default_factory=empty_plan_items)
    summary_path: Path
    report_path: Path
    diagnostics_path: Path | None = None
    duration_ms: int | None = None
    failure_category: str | None = None
    warning_summary: list[str] = Field(default_factory=empty_warning_summary)
    upstream_review_enabled: bool = False
    upstream_review_result_path: Path | None = None
    upstream_review_orchestration_path: Path | None = None
    contract_versions: dict[str, str | None] = Field(default_factory=empty_contract_versions)
    artifact_manifest_version: int | None = None
    token_usage: TokenUsage | None = None


class PhasedOperationResult(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    phase: OperationPhase
    plan_result: GeneratedPlanResult
    execution_result: ExecutedPlanResult | None = None
    planning_usage: TokenUsage | None = None
    execution_usage: TokenUsage | None = None
    total_usage: TokenUsage | None = None
