from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

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
    change_summary: str | None = None
    changed_files: list[str] = Field(default_factory=empty_strings)
    diff_text: str | None = None
    review_orchestration_path: Path | None = None
    requirement_doc_path: Path | None = None
    technical_doc_path: Path | None = None
    previous_report_path: Path | None = None
    previous_result_paths: list[Path] = Field(default_factory=empty_paths)
    assets_root: Path | None = None

class RequirementPlan(BaseModel):
    plan_id: str
    name: str | None = None
    app_id: str
    source: str
    version: str
    cases: list[TestCase] = Field(default_factory=empty_test_cases)
    source_metadata: dict[str, str] = Field(default_factory=empty_string_map)


class PlanSnapshot(RequirementPlan):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    source_plan_id: str
    exported_at: str
    format_version: str = "phase0.v1"
