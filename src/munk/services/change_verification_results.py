from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from munk.execution.models import ExecutedPlanResult, PlanExecutionResult
from munk.reporting.models import PLAN_REPAIR_REPORT_SCHEMA_VERSION, PlanRepairReport, UpstreamReviewLink
from munk.reviewing.models import REVIEW_RESULT_SCHEMA_VERSION, ReviewResult
from munk.reviewing.orchestration_models import (
    REVIEW_ORCHESTRATION_SCHEMA_VERSION,
    ReviewOrchestrationContract,
)
from munk.services.artifact_manifest_models import ArtifactSchemaVersions, UpstreamReviewArtifacts
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.diagnostics_service import OperationDiagnosticsService


@dataclass(frozen=True)
class LoadedUpstreamReview:
    contract: ReviewOrchestrationContract
    review_result: ReviewResult
    review_orchestration_path: Path

    @property
    def review_result_path(self) -> Path:
        return self.review_result.review_result_path


def load_upstream_review(review_orchestration_path: Path | None) -> LoadedUpstreamReview | None:
    if review_orchestration_path is None:
        return None
    contract = ReviewOrchestrationContract.model_validate_json(
        review_orchestration_path.read_text(encoding="utf-8")
    )
    review_result_path = review_orchestration_path.parent / "review_result.json"
    review_result = ReviewResult.model_validate_json(review_result_path.read_text(encoding="utf-8"))
    return LoadedUpstreamReview(
        contract=contract,
        review_result=review_result,
        review_orchestration_path=review_orchestration_path,
    )


class ChangeVerificationResultService:
    def __init__(
        self,
        *,
        artifact_manifest_service: ArtifactManifestService | None = None,
        diagnostics_service: OperationDiagnosticsService | None = None,
    ) -> None:
        self._artifact_manifest_service = artifact_manifest_service or ArtifactManifestService()
        self._diagnostics_service = diagnostics_service or OperationDiagnosticsService()

    def attach_upstream_review_outputs(
        self,
        *,
        result: PlanExecutionResult,
        upstream_review: LoadedUpstreamReview,
    ) -> None:
        plan_run_dir = result.summary_path.parent
        upstream_review_path = plan_run_dir / "upstream_review_result.json"
        upstream_orchestration_path = plan_run_dir / "review_orchestration.json"
        shutil.copyfile(upstream_review.review_result_path, upstream_review_path)
        upstream_orchestration_path.write_text(
            upstream_review.contract.model_dump_json(indent=2),
            encoding="utf-8",
        )
        report = PlanRepairReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))
        report = report.model_copy(
            update={
                "upstream_review": _build_upstream_review_link(
                    upstream_review=upstream_review,
                    upstream_review_path=upstream_review_path,
                    upstream_orchestration_path=upstream_orchestration_path,
                )
            }
        )
        result.report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        manifest_path = plan_run_dir / "artifact_manifest.json"
        manifest = self._artifact_manifest_service.load_manifest(manifest_path)
        updated_manifest = self._artifact_manifest_service.augment_manifest(
            manifest,
            primary_artifacts={
                "upstream_review_result": str(upstream_review_path),
                "review_orchestration": str(upstream_orchestration_path),
            },
            schema_versions=ArtifactSchemaVersions(
                review_result=REVIEW_RESULT_SCHEMA_VERSION,
                review_orchestration=upstream_review.contract.schema_version,
                plan_repair_report=report.schema_version,
            ),
            upstream_review=UpstreamReviewArtifacts(
                review_operation_id=upstream_review.review_result.operation_id,
                review_result_path=upstream_review_path,
                review_orchestration_path=upstream_orchestration_path,
                contract_version=upstream_review.contract.schema_version,
            ),
        )
        self._artifact_manifest_service.write_manifest(manifest_path, updated_manifest)

    def build_executed_plan_result(
        self,
        *,
        result: PlanExecutionResult,
        upstream_review: LoadedUpstreamReview | None,
    ) -> ExecutedPlanResult:
        plan_run_dir = result.summary_path.parent
        upstream_review_result_path = plan_run_dir / "upstream_review_result.json"
        upstream_review_orchestration_path = plan_run_dir / "review_orchestration.json"
        duration_ms = None
        failure_category = None
        warning_summary: list[str] = []
        contract_versions: dict[str, str | None] = {}
        artifact_manifest_version = None

        if result.diagnostics_path is not None:
            diagnostics = self._diagnostics_service.load(result.diagnostics_path)
            duration_ms = diagnostics.duration_ms
            failure_category = diagnostics.failure_category
            warning_summary = list(diagnostics.warning_summary)

        manifest_path = plan_run_dir / "artifact_manifest.json"
        if manifest_path.exists():
            try:
                manifest = self._artifact_manifest_service.load_manifest(manifest_path)
            except Exception:
                pass
            else:
                contract_versions = {
                    key: value
                    for key, value in manifest.schema_versions.to_mapping().items()
                }
                artifact_manifest_version = manifest.manifest_version
        if upstream_review is not None and "review_orchestration" not in contract_versions:
            contract_versions["review_orchestration"] = upstream_review.contract.schema_version

        return ExecutedPlanResult(
            verification_status=result.status,
            total_cases=result.total_cases,
            passed_cases=result.passed_cases,
            failed_cases=result.failed_cases,
            inconclusive_cases=result.inconclusive_cases,
            stopped_early=result.stopped_early,
            items=list(result.items),
            summary_path=result.summary_path,
            report_path=result.report_path,
            diagnostics_path=result.diagnostics_path,
            duration_ms=duration_ms,
            failure_category=failure_category,
            warning_summary=warning_summary,
            upstream_review_enabled=upstream_review_result_path.exists(),
            upstream_review_result_path=upstream_review_result_path if upstream_review_result_path.exists() else None,
            upstream_review_orchestration_path=(
                upstream_review_orchestration_path if upstream_review_orchestration_path.exists() else None
            ),
            contract_versions=contract_versions,
            artifact_manifest_version=artifact_manifest_version,
            token_usage=result.token_usage,
        )


def _build_upstream_review_link(
    *,
    upstream_review: LoadedUpstreamReview,
    upstream_review_path: Path,
    upstream_orchestration_path: Path,
) -> UpstreamReviewLink:
    return UpstreamReviewLink(
        review_operation_id=upstream_review.review_result.operation_id,
        review_orchestration_path=upstream_orchestration_path,
        review_result_path=upstream_review_path,
        risk_summary=upstream_review.contract.review_hints.risk_summary,
        high_risk_count=upstream_review.contract.statistics.high_risk_count,
        finding_titles=[item.title for item in upstream_review.contract.review_hints.high_risk_findings],
        required_case_ids=[item.case_id for item in upstream_review.contract.required_cases],
        advisory_case_titles=[item.title for item in upstream_review.contract.advisory_cases],
        contract_version=upstream_review.contract.schema_version or REVIEW_ORCHESTRATION_SCHEMA_VERSION,
    )
