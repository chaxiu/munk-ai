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
    "optimize_case",
    "knowledge_post_action",
]


def empty_artifact_ref_map() -> dict[str, "ArtifactRef"]:
    return {}


def empty_case_entries() -> list["CaseArtifactEntry"]:
    return []


def empty_reproduction_entries() -> list["ReproductionEntry"]:
    return []


def empty_summary() -> "ArtifactManifestSummary":
    return ArtifactManifestSummary()


def empty_metadata() -> dict[str, Any]:
    return {}


def empty_schema_versions() -> "ArtifactSchemaVersions":
    return ArtifactSchemaVersions()


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


class ArtifactSchemaVersions(BaseModel):
    review_result: str | None = None
    review_orchestration: str | None = None
    plan_repair_report: str | None = None
    operation_diagnostics: str | None = None

    def to_mapping(self) -> dict[str, str]:
        payload = self.model_dump(exclude_none=True)
        return {key: value for key, value in payload.items() if isinstance(value, str)}

    @classmethod
    def from_mapping(cls, versions: dict[str, str] | None = None) -> "ArtifactSchemaVersions":
        if not versions:
            return cls()
        return cls.model_validate(versions)


class ArtifactManifestSummary(BaseModel):
    case_count: int = 0


class ArtifactManifest(BaseModel):
    manifest_version: int = 2
    operation_id: str | None = None
    operation_kind: ReproductionTargetKind | None = None
    verification_verdict: str | None = None
    root_dir: Path
    primary_artifacts: dict[str, ArtifactRef] = Field(default_factory=empty_artifact_ref_map)
    case_runs: list[CaseArtifactEntry] = Field(default_factory=empty_case_entries)
    reproduction: list[ReproductionEntry] = Field(default_factory=empty_reproduction_entries)
    schema_versions: ArtifactSchemaVersions = Field(default_factory=empty_schema_versions)
    upstream_review: UpstreamReviewArtifacts | None = None
    summary: ArtifactManifestSummary = Field(default_factory=empty_summary)
