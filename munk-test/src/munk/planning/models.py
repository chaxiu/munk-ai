from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from munk.execution.verify_change_validation import (
    validate_acceptance_criteria,
    validate_change_planning_intake,
)
from munk.testing import TestCase


def empty_string_map() -> dict[str, str]:
    return {}


def empty_strings() -> list[str]:
    return []

def empty_test_cases() -> list[TestCase]:
    return []


def empty_paths() -> list[Path]:
    return []


class RequirementInput(BaseModel):
    app_id: str
    requirement_doc_path: Path
    technical_doc_path: Optional[Path] = None
    user_prompt: str | None = None
    artifact_path: Optional[Path] = None
    assets_root: Optional[Path] = None
    artifact_url: Optional[str] = None
    auto_run: bool = False
    source_metadata: dict[str, str] = Field(default_factory=empty_string_map)


class ChangePlanInput(BaseModel):
    app_id: str
    acceptance_criteria: list[str] = Field(default_factory=empty_strings)
    change_summary: str | None = None
    changed_files: list[str] = Field(default_factory=empty_strings)
    diff_text: str | None = None
    review_orchestration_path: Path | None = None
    requirement_doc_path: Path | None = None
    technical_doc_path: Path | None = None
    assets_root: Path | None = None

    @field_validator("acceptance_criteria", mode="before")
    @classmethod
    def normalize_acceptance_criteria(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("acceptance_criteria must be a list of strings")
        return validate_acceptance_criteria([item for item in value if isinstance(item, str)])

    @model_validator(mode="after")
    def validate_change_plan_input(self) -> "ChangePlanInput":
        validate_change_planning_intake(
            enable_plan_agent=True,
            provided_case_count=0,
            acceptance_criteria=self.acceptance_criteria,
            change_summary=self.change_summary,
            changed_files=list(self.changed_files),
            diff_text=self.diff_text,
            requirement_doc_path=self.requirement_doc_path,
        )
        return self


class RequirementPlan(BaseModel):
    plan_id: str
    name: str | None = None
    app_id: str
    source: str
    version: str
    acceptance_criteria: list[str] = Field(default_factory=empty_strings)
    cases: list[TestCase] = Field(default_factory=empty_test_cases)
    source_metadata: dict[str, str] = Field(default_factory=empty_string_map)


class PlanSnapshot(RequirementPlan):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    source_plan_id: str
    exported_at: str
    format_version: str = "phase0.v1"
