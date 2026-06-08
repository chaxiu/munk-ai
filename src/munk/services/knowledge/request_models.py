from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


def empty_strings() -> list[str]:
    return []


def empty_paths() -> dict[str, Path]:
    return {}


class KnowledgePostActionRequest(BaseModel):
    app_id: str
    plan_id: str
    case_id: str
    case_title: str | None = None
    assets_root: Path
    run_dir: Path
    judge_result_path: Path | None = None
    artifact_paths: dict[str, Path] = Field(default_factory=empty_paths)
    parent_operation_id: str | None = None


class KnowledgePostActionResult(BaseModel):
    summary: str
    submitted: bool = False
    skip_reason: str | None = None
    candidate_id: str | None = None
    result_path: Path
    request_path: Path
    diagnostics_path: Path
    artifacts: dict[str, str]
