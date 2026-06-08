from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from munk.execution.models import ExecutionStatus, JudgeVerdict

ReportOverallVerdict = Literal["passed", "failed", "inconclusive"]
PLAN_REPAIR_REPORT_SCHEMA_VERSION = "phase7e.plan_repair_report.v1"


def empty_strings() -> list[str]:
    return []


def empty_str_map() -> dict[str, str]:
    return {}


def empty_case_reports() -> list["CaseRepairReport"]:
    return []


def empty_metadata() -> dict[str, object]:
    return {}


class UpstreamReviewLink(BaseModel):
    review_operation_id: str | None = None
    review_orchestration_path: Path
    review_result_path: Path
    risk_summary: str
    high_risk_count: int = 0
    finding_titles: list[str] = Field(default_factory=empty_strings)
    required_case_ids: list[str] = Field(default_factory=empty_strings)
    advisory_case_titles: list[str] = Field(default_factory=empty_strings)
    contract_version: str


class CaseRepairReport(BaseModel):
    case_id: str
    title: str
    is_core_case: bool = False
    verdict: JudgeVerdict
    execution_status: ExecutionStatus
    expected_summary: str
    observed_summary: str
    mismatch_step: str
    judge_reason: str | None = None
    failure_hypothesis: str | None = None
    missing_evidence: list[str] = Field(default_factory=empty_strings)
    recommended_artifacts: dict[str, str] = Field(default_factory=empty_str_map)
    recommended_evidence_ids: list[str] = Field(default_factory=empty_strings)
    run_dir: Path


class PlanRepairTotals(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    inconclusive_cases: int
    core_total_cases: int
    core_failed_cases: int
    core_inconclusive_cases: int


class PlanRepairReport(BaseModel):
    schema_version: str = PLAN_REPAIR_REPORT_SCHEMA_VERSION
    app_id: str
    plan_id: str
    generated_at: str
    overall_verdict: ReportOverallVerdict
    summary: str
    core_case_summary: str
    totals: PlanRepairTotals
    key_failures: list[str] = Field(default_factory=empty_strings)
    key_inconclusive: list[str] = Field(default_factory=empty_strings)
    case_reports: list[CaseRepairReport] = Field(default_factory=empty_case_reports)
    artifacts: dict[str, str] = Field(default_factory=empty_str_map)
    upstream_review: UpstreamReviewLink | None = None
    metadata: dict[str, object] = Field(default_factory=empty_metadata)
