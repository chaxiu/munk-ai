from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class KnowledgePostActionOperationRequest(BaseModel):
    app_id: str
    plan_id: str
    case_id: str
    case_title: str | None = None
    run_dir: Path
    result_path: Path
    assets_root: Path
    judge_result_path: Path | None = None
    source_attempt_index: int | None = None
    parent_operation_id: str | None = None


KnowledgePostActionRequest = KnowledgePostActionOperationRequest


class KnowledgePostActionResult(BaseModel):
    summary: str
    submitted: bool = False
    skip_reason: str | None = None
    candidate_id: str | None = None
    result_path: Path
    request_path: Path
    diagnostics_path: Path
    artifacts: dict[str, str]
