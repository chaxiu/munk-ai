from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from munk.judging import JudgeOptimizationTrigger


def empty_strings() -> list[str]:
    return []


class OptimizeTriggerCandidate(BaseModel):
    trigger: JudgeOptimizationTrigger = Field(default_factory=JudgeOptimizationTrigger)
    trigger_source: str = "judge"
    trigger_signals: list[str] = Field(default_factory=empty_strings)
    source_attempt_index: int | None = None
    judge_result_path: Path | None = None


class OptimizeCaseOperationRequest(BaseModel):
    app_id: str
    plan_id: str
    case_id: str
    case_title: str | None = None
    run_dir: Path
    result_path: Path
    trigger: OptimizeTriggerCandidate = Field(default_factory=OptimizeTriggerCandidate)
    judge_result_path: Path | None = None
    parent_operation_id: str | None = None


class OptimizeCaseOperationResult(BaseModel):
    summary: str
    patched_fields: list[str]
    applied: bool = False
    skip_reason: str | None = None
    confidence: float | None = None
    result_path: Path
    request_path: Path
    diagnostics_path: Path
    field_diffs_path: Path
    field_diffs: list[dict[str, object]] = Field(default_factory=list)
    artifacts: dict[str, str]
