from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReviewPlatform = Literal["android", "ios", "web"]
ReviewCaseType = Literal["best_practice", "bad_case", "review_checkpoint"]
ReviewFindingSeverity = Literal["low", "medium", "high", "critical"]
ReviewSuggestedCasePriority = Literal["normal", "high"]
REVIEW_RESULT_SCHEMA_VERSION = "phase7e.review_result.v1"


def empty_strings() -> list[str]:
    return []


def empty_hits() -> list["ReviewKnowledgeHit"]:
    return []


def empty_findings() -> list["ReviewFinding"]:
    return []


def empty_follow_up_cases() -> list["SuggestedFollowUpCase"]:
    return []


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str | None = None
    change_summary: str | None = None
    changed_files: list[str] = Field(default_factory=empty_strings)
    diff_text: str | None = None
    requirement_doc_path: Path | None = None
    technical_doc_path: Path | None = None
    review_query: str | None = None
    platforms: list[ReviewPlatform] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=empty_strings)
    case_types: list[ReviewCaseType] = Field(default_factory=list)
    artifact_path: Path | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "ReviewRequest":
        has_change_summary = bool(self.change_summary and self.change_summary.strip())
        has_changed_files = bool(self.changed_files)
        has_diff = bool(self.diff_text and self.diff_text.strip())
        has_query = bool(self.review_query and self.review_query.strip())
        if not any((has_change_summary, has_changed_files, has_diff, has_query)):
            raise ValueError(
                "review request requires at least one of change_summary, changed_files, diff_text, or review_query"
            )
        return self


class ReviewKnowledgeHit(BaseModel):
    case_id: str
    platform: ReviewPlatform
    domain: str
    topic: str
    case_type: ReviewCaseType
    title: str
    summary: str
    tags: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)
    code_languages: list[str] = Field(default_factory=empty_strings)
    source_dir: Path
    body_path: Path
    body_excerpt: str
    retrieval_channels: list[str] = Field(default_factory=empty_strings)
    vector_distance: float | None = None
    fts_score: float | None = None
    filter_score: float | None = None
    combined_score: float | None = None


class ReviewFinding(BaseModel):
    severity: ReviewFindingSeverity
    title: str
    summary: str
    changed_files: list[str] = Field(default_factory=empty_strings)
    knowledge_case_ids: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)


class SuggestedFollowUpCase(BaseModel):
    title: str
    intent: str
    priority: ReviewSuggestedCasePriority = "normal"
    runner_goal: str
    expected: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)
    changed_files: list[str] = Field(default_factory=empty_strings)

    @model_validator(mode="after")
    def validate_case(self) -> "SuggestedFollowUpCase":
        self.title = self.title.strip()
        self.intent = self.intent.strip()
        self.runner_goal = self.runner_goal.strip()
        self.expected = [item.strip() for item in self.expected if item.strip()]
        self.recommended_checks = [item.strip() for item in self.recommended_checks if item.strip()]
        self.changed_files = [item.strip() for item in self.changed_files if item.strip()]
        if not self.title:
            raise ValueError("suggested follow-up case title must not be empty")
        if not self.intent:
            raise ValueError("suggested follow-up case intent must not be empty")
        if not self.runner_goal:
            raise ValueError("suggested follow-up case runner_goal must not be empty")
        if not self.expected:
            raise ValueError("suggested follow-up case expected must not be empty")
        return self


class ReviewResult(BaseModel):
    schema_version: str = REVIEW_RESULT_SCHEMA_VERSION
    app_id: str | None = None
    operation_id: str | None = None
    finding_count: int = 0
    high_risk_count: int = 0
    risk_summary: str
    likely_regression_surface: list[str] = Field(default_factory=empty_strings)
    missing_verification: list[str] = Field(default_factory=empty_strings)
    suggested_follow_up_cases: list[SuggestedFollowUpCase] = Field(default_factory=empty_follow_up_cases)
    findings: list[ReviewFinding] = Field(default_factory=empty_findings)
    knowledge_hits: list[ReviewKnowledgeHit] = Field(default_factory=empty_hits)
    review_request_path: Path
    retrieval_path: Path
    review_result_path: Path
    review_orchestration_path: Path
    artifact_manifest_path: Path
    diagnostics_path: Path | None = None
    llm_transcript_path: Path | None = None
