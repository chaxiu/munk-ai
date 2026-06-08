from __future__ import annotations

from pathlib import Path
from typing import Literal

from munk.testing import AiGuidance
from pydantic import BaseModel, Field

OptimizeFieldName = Literal[
    "objective_clarifications",
    "preflight_checks",
    "interaction_hints",
    "disambiguation_rules",
    "recovery_hints",
    "judge_hints",
]


def empty_strings() -> list[str]:
    return []


def empty_paths() -> dict[str, str]:
    return {}


def empty_field_names() -> list[OptimizeFieldName]:
    return []


class OptimizeExecutionSummary(BaseModel):
    verdict: str
    summary: str | None = None
    judge_reason: str | None = None
    attempt_count: int = 0
    retry_count: int = 0


class OptimizeTrigger(BaseModel):
    needs_optimization: bool = False
    optimization_fields: list[OptimizeFieldName] = Field(default_factory=empty_field_names)
    optimization_reason: str | None = None
    optimization_confidence: float | None = None
    source: str | None = None
    signals: list[str] = Field(default_factory=empty_strings)
    source_attempt_index: int | None = None


class OptimizeRequest(BaseModel):
    app_id: str
    plan_id: str
    case_id: str
    case_title: str
    intent: str
    runner_goal: str
    expected: list[str] = Field(default_factory=empty_strings)
    current_ai_guidance: AiGuidance | None = None
    execution_summary: OptimizeExecutionSummary
    trigger: OptimizeTrigger
    artifacts: dict[str, str] = Field(default_factory=empty_paths)
    artifact_payloads: dict[str, object] = Field(default_factory=dict)
    run_dir: Path


class OptimizeFieldPatch(BaseModel):
    field_name: OptimizeFieldName
    replace_with: list[str] = Field(default_factory=empty_strings)
    reason: str | None = None


class OptimizeResult(BaseModel):
    summary: str
    patched_fields: list[OptimizeFieldPatch] = Field(default_factory=list)
    skipped_fields: list[OptimizeFieldName] = Field(default_factory=empty_field_names)
    artifacts: dict[str, str] = Field(default_factory=empty_paths)
