from __future__ import annotations

from munk.reviewing.models import ReviewFindingSeverity, ReviewSuggestedCasePriority
from pydantic import BaseModel, Field, model_validator


def empty_strings() -> list[str]:
    return []


def empty_findings() -> list["ReviewFindingDraft"]:
    return []


def empty_follow_up_cases() -> list["SuggestedFollowUpCaseDraft"]:
    return []


class ReviewFindingDraft(BaseModel):
    severity: ReviewFindingSeverity
    title: str
    summary: str
    changed_files: list[str] = Field(default_factory=empty_strings)
    knowledge_case_ids: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)


class SuggestedFollowUpCaseDraft(BaseModel):
    title: str
    intent: str
    priority: ReviewSuggestedCasePriority = "normal"
    runner_goal: str
    expected: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)
    changed_files: list[str] = Field(default_factory=empty_strings)

    @model_validator(mode="after")
    def validate_case(self) -> "SuggestedFollowUpCaseDraft":
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


class ReviewResultDraft(BaseModel):
    risk_summary: str
    likely_regression_surface: list[str] = Field(default_factory=empty_strings)
    missing_verification: list[str] = Field(default_factory=empty_strings)
    suggested_follow_up_cases: list[SuggestedFollowUpCaseDraft] = Field(default_factory=empty_follow_up_cases)
    findings: list[ReviewFindingDraft] = Field(default_factory=empty_findings)
