from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from munk.reviewing.models import ReviewResult
from munk.reviewing.orchestration_models import REVIEW_ORCHESTRATION_SCHEMA_VERSION
from munk.services.diagnostics_models import OperationDiagnostics
from munk.services.operations.command_helpers import artifact_manifest_version, load_contract_versions


class ReviewOperationResultPayload(BaseModel):
    app_id: str | None = None
    finding_count: int
    high_risk_count: int
    risk_summary: str
    review_request_path: str
    review_result_path: str
    review_orchestration_path: str
    retrieval_path: str
    artifact_manifest_path: str
    contract_versions: dict[str, str | None] = Field(default_factory=dict)
    diagnostics_path: str | None = None
    duration_ms: int | None = None
    failure_category: str | None = None
    warning_summary: list[str] = Field(default_factory=list)
    llm_transcript_path: str | None = None
    artifact_manifest_version: int | None = None
    artifacts: dict[str, str]

    def to_command_data(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"artifacts"}, exclude_none=True)


def build_review_operation_result_payload(
    *,
    result: ReviewResult,
    diagnostics: OperationDiagnostics,
    artifacts: dict[str, str],
) -> ReviewOperationResultPayload:
    return ReviewOperationResultPayload(
        app_id=result.app_id,
        finding_count=result.finding_count,
        high_risk_count=result.high_risk_count,
        risk_summary=result.risk_summary,
        review_request_path=str(result.review_request_path),
        review_result_path=str(result.review_result_path),
        review_orchestration_path=str(result.review_orchestration_path),
        retrieval_path=str(result.retrieval_path),
        artifact_manifest_path=str(result.artifact_manifest_path),
        contract_versions=load_contract_versions(
            manifest_path=result.artifact_manifest_path,
            fallback={
                "review_result": result.schema_version,
                "review_orchestration": REVIEW_ORCHESTRATION_SCHEMA_VERSION,
            },
        ),
        diagnostics_path=str(result.diagnostics_path) if result.diagnostics_path is not None else None,
        duration_ms=diagnostics.duration_ms,
        failure_category=diagnostics.failure_category,
        warning_summary=list(diagnostics.warning_summary),
        llm_transcript_path=str(result.llm_transcript_path) if result.llm_transcript_path is not None else None,
        artifact_manifest_version=artifact_manifest_version(result.artifact_manifest_path),
        artifacts=dict(artifacts),
    )
