from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

ArtifactKind = Literal[
    "json_file",
    "jsonl_file",
    "log_file",
    "text_file",
    "directory",
    "image_directory",
    "binary_file",
    "other_file",
]
ArtifactScope = Literal["operation", "plan_run", "case_run"]
ReproductionTargetKind = Literal[
    "plan",
    "run_case",
    "run_plan",
    "run_plans",
    "verify_change",
    "review",
]


def empty_artifact_ref_map() -> dict[str, "ArtifactRef"]:
    return {}


def empty_case_entries() -> list["CaseArtifactEntry"]:
    return []


def empty_reproduction_entries() -> list["ReproductionEntry"]:
    return []


def empty_metadata() -> dict[str, Any]:
    return {}


def empty_schema_versions() -> dict[str, str]:
    return {}


class ArtifactRef(BaseModel):
    artifact_id: str
    role: str
    kind: ArtifactKind
    scope: ArtifactScope
    path: Path
    media_type: str | None = None
    exists: bool = True
    metadata: dict[str, Any] = Field(default_factory=empty_metadata)


class CaseArtifactEntry(BaseModel):
    case_id: str
    title: str
    operation_id: str | None = None
    verdict: str
    execution_status: str
    run_dir: Path
    artifacts: dict[str, ArtifactRef] = Field(default_factory=empty_artifact_ref_map)


class ReproductionEntry(BaseModel):
    target_kind: ReproductionTargetKind
    source_operation_id: str | None = None
    command: str
    request_file: Path
    case_id: str | None = None
    reason: str | None = None


class UpstreamReviewArtifacts(BaseModel):
    review_operation_id: str | None = None
    review_result_path: Path | None = None
    review_orchestration_path: Path | None = None
    contract_version: str | None = None


class ArtifactManifest(BaseModel):
    manifest_version: int = 2
    operation_id: str | None = None
    operation_kind: ReproductionTargetKind | None = None
    verification_verdict: str | None = None
    root_dir: Path
    primary_artifacts: dict[str, ArtifactRef] = Field(default_factory=empty_artifact_ref_map)
    case_runs: list[CaseArtifactEntry] = Field(default_factory=empty_case_entries)
    reproduction: list[ReproductionEntry] = Field(default_factory=empty_reproduction_entries)
    schema_versions: dict[str, str] = Field(default_factory=empty_schema_versions)
    upstream_review: UpstreamReviewArtifacts | None = None
    metadata: dict[str, Any] = Field(default_factory=empty_metadata)
