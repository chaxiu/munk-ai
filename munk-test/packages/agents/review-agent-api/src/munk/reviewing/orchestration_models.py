from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from munk.reviewing.models import ReviewSuggestedCasePriority

REVIEW_ORCHESTRATION_SCHEMA_VERSION = "phase7e.review_orchestration.v1"


def empty_strings() -> list[str]:
    return []


def empty_required_cases() -> list["ReviewRequiredCase"]:
    return []


def empty_advisory_cases() -> list["ReviewAdvisoryCase"]:
    return []


def empty_findings() -> list["ReviewFindingHint"]:
    return []


class ReviewFindingHint(BaseModel):
    severity: str
    title: str
    summary: str
    changed_files: list[str] = Field(default_factory=empty_strings)
    knowledge_case_ids: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)


class ReviewAdvisoryCase(BaseModel):
    title: str
    intent: str
    priority: ReviewSuggestedCasePriority = "normal"
    runner_goal: str
    expected: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)
    changed_files: list[str] = Field(default_factory=empty_strings)


class ReviewCaseBudget(BaseModel):
    max_steps: int | None = Field(default=None, gt=0)
    max_seconds: float | None = Field(default=None, gt=0)


class ReviewCaseStartState(BaseModel):
    mode: Literal["reset", "resume"] = "reset"
    page_id: str | None = None


class ReviewRequiredCase(BaseModel):
    case_id: str
    title: str
    intent: str
    preconditions: list[str] = Field(default_factory=empty_strings)
    expected: list[str] = Field(default_factory=empty_strings)
    is_core_case: bool = False
    runner_goal: str
    budget: ReviewCaseBudget | None = None
    start_state: ReviewCaseStartState = Field(default_factory=ReviewCaseStartState)


class ReviewHintBlock(BaseModel):
    risk_summary: str
    likely_regression_surface: list[str] = Field(default_factory=empty_strings)
    missing_verification: list[str] = Field(default_factory=empty_strings)
    high_risk_findings: list[ReviewFindingHint] = Field(default_factory=empty_findings)
    related_changed_files: list[str] = Field(default_factory=empty_strings)
    related_knowledge_case_ids: list[str] = Field(default_factory=empty_strings)


class ReviewOrchestrationStatistics(BaseModel):
    finding_count: int = 0
    high_risk_count: int = 0
    high_priority_case_count: int = 0
    advisory_case_count: int = 0


class ReviewOrchestrationContract(BaseModel):
    schema_version: str = REVIEW_ORCHESTRATION_SCHEMA_VERSION
    app_id: str | None = None
    required_cases: list[ReviewRequiredCase] = Field(default_factory=empty_required_cases)
    advisory_cases: list[ReviewAdvisoryCase] = Field(default_factory=empty_advisory_cases)
    review_hints: ReviewHintBlock
    statistics: ReviewOrchestrationStatistics = Field(default_factory=ReviewOrchestrationStatistics)
