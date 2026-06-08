from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def empty_strings() -> list[str]:
    return []


def empty_test_case_drafts() -> list["GeneratedTestCaseDraft"]:
    return []


def empty_procedure() -> list[str]:
    return []


def _strip_non_empty(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


def _strip_string_list(values: list[str], *, field_name: str) -> list[str]:
    return [_strip_non_empty(value, field_name=field_name) for value in values]


class GeneratedTestCaseDraft(BaseModel):
    title: str
    intent: str
    preconditions: list[str] = Field(default_factory=empty_strings)
    expected: list[str] = Field(min_length=1)
    procedure: list[str] = Field(default_factory=empty_procedure)
    runner_goal: str
    start_mode: Literal["reset", "resume"] = "reset"
    page_id: str | None = None

    @field_validator("title", "intent", "runner_goal")
    @classmethod
    def validate_required_text(cls, value: str, info) -> str:  # type: ignore[override]
        return _strip_non_empty(value, field_name=str(info.field_name))

    @field_validator("preconditions", "procedure")
    @classmethod
    def validate_optional_string_list(cls, value: list[str], info) -> list[str]:  # type: ignore[override]
        return _strip_string_list(value, field_name=f"{info.field_name}[]")

    @field_validator("expected")
    @classmethod
    def validate_expected(cls, value: list[str]) -> list[str]:
        normalized = _strip_string_list(value, field_name="expected[]")
        if not normalized:
            raise ValueError("expected must not be empty")
        return normalized


class GeneratedPlanSkeletonDraft(BaseModel):
    name: str
    summary: str
    target_case_count: int = Field(gt=0)

    @field_validator("name", "summary")
    @classmethod
    def validate_required_text(cls, value: str, info) -> str:  # type: ignore[override]
        return _strip_non_empty(value, field_name=str(info.field_name))


class GeneratedCaseAppendDraft(BaseModel):
    case: GeneratedTestCaseDraft


class GeneratedPlanFinalizeDraft(BaseModel):
    summary: str


class GeneratedPlanDraft(BaseModel):
    summary: str
    cases: list[GeneratedTestCaseDraft] = Field(default_factory=empty_test_case_drafts)
