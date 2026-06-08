from __future__ import annotations

from dataclasses import dataclass

from munk.config import ResolvedConfig
from munk.reviewing.models import ReviewRequest, ReviewResult
from munk.reviewing.orchestration_models import REVIEW_ORCHESTRATION_SCHEMA_VERSION
from munk.reviewing.runtime import ReviewRuntimeContext, ReviewRuntimeOutput
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.diagnostics_models import (
    OPERATION_DIAGNOSTICS_SCHEMA_VERSION,
    DiagnosticsFailureCategory,
    OperationDiagnostics,
)
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.reviewing.runtime_host import ReviewHostManagedPaths

REVIEW_RUNTIME_DIAGNOSTICS_STAGE = "review_runtime"


@dataclass(frozen=True)
class MaterializedReviewArtifacts:
    result: ReviewResult
    diagnostics: OperationDiagnostics

    @property
    def artifacts(self) -> dict[str, str]:
        artifacts = {
            "review_request": str(self.result.review_request_path),
            "retrieval": str(self.result.retrieval_path),
            "review_result": str(self.result.review_result_path),
            "review_orchestration": str(self.result.review_orchestration_path),
            "artifact_manifest": str(self.result.artifact_manifest_path),
        }
        if self.result.diagnostics_path is not None:
            artifacts["diagnostics"] = str(self.result.diagnostics_path)
        if self.result.llm_transcript_path is not None:
            artifacts["llm_transcript"] = str(self.result.llm_transcript_path)
        return artifacts


class ReviewArtifactMaterializer:
    def __init__(self, *, resolved_config: ResolvedConfig) -> None:
        self._resolved_config = resolved_config
        self._diagnostics_service = OperationDiagnosticsService()
        self._manifest_service = ArtifactManifestService()

    def materialize_success(
        self,
        *,
        runtime_output: ReviewRuntimeOutput,
        request: ReviewRequest,
        context: ReviewRuntimeContext,
        host_paths: ReviewHostManagedPaths,
    ) -> MaterializedReviewArtifacts:
        result = self._build_review_result(
            request=request,
            context=context,
            host_paths=host_paths,
            runtime_output=runtime_output,
        )
        host_paths.review_result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        host_paths.review_orchestration_path.write_text(
            runtime_output.review_orchestration.model_dump_json(indent=2),
            encoding="utf-8",
        )
        diagnostics = self._build_diagnostics(
            request=request,
            result=result,
            started_at=runtime_output.started_at,
            duration_ms=runtime_output.duration_ms,
            warning_summary=list(runtime_output.warning_summary),
            prompt_hit_count=len(runtime_output.prompt_hits),
            failure_category=None,
            failure_message=None,
            status="succeeded",
        )
        self._diagnostics_service.write(host_paths.diagnostics_path, diagnostics)
        self._write_manifest(result=result)
        return MaterializedReviewArtifacts(result=result, diagnostics=diagnostics)

    def materialize_failure(
        self,
        *,
        request: ReviewRequest,
        context: ReviewRuntimeContext,
        host_paths: ReviewHostManagedPaths,
        exc: Exception,
    ) -> dict[str, str]:
        result = ReviewResult(
            app_id=request.app_id,
            operation_id=context.operation_id,
            finding_count=0,
            high_risk_count=0,
            risk_summary="review failed before producing a result",
            review_request_path=context.managed_paths.review_request_path,
            retrieval_path=context.managed_paths.retrieval_path,
            review_result_path=host_paths.review_result_path,
            review_orchestration_path=host_paths.review_orchestration_path,
            artifact_manifest_path=host_paths.artifact_manifest_path,
            diagnostics_path=host_paths.diagnostics_path,
            llm_transcript_path=context.managed_paths.llm_transcript_path,
        )
        diagnostics = self._build_diagnostics(
            request=request,
            result=result,
            started_at=self._diagnostics_service.now_iso(),
            duration_ms=0,
            warning_summary=[],
            prompt_hit_count=0,
            failure_category=self._diagnostics_service.classify_exception(exc),
            failure_message=str(exc),
            status="failed",
        )
        self._diagnostics_service.write(host_paths.diagnostics_path, diagnostics)
        self._write_manifest(result=result)
        artifacts = {
            "artifact_manifest": str(host_paths.artifact_manifest_path),
            "diagnostics": str(host_paths.diagnostics_path),
        }
        if context.managed_paths.review_request_path.exists():
            artifacts["review_request"] = str(context.managed_paths.review_request_path)
        if context.managed_paths.retrieval_path.exists():
            artifacts["retrieval"] = str(context.managed_paths.retrieval_path)
        if context.managed_paths.llm_transcript_path is not None and context.managed_paths.llm_transcript_path.exists():
            artifacts["llm_transcript"] = str(context.managed_paths.llm_transcript_path)
        return artifacts

    def _build_review_result(
        self,
        *,
        request: ReviewRequest,
        context: ReviewRuntimeContext,
        host_paths: ReviewHostManagedPaths,
        runtime_output: ReviewRuntimeOutput,
    ) -> ReviewResult:
        result_data = runtime_output.result_data
        return ReviewResult(
            app_id=result_data.app_id or request.app_id,
            operation_id=context.operation_id,
            finding_count=result_data.finding_count,
            high_risk_count=result_data.high_risk_count,
            risk_summary=result_data.risk_summary,
            likely_regression_surface=list(result_data.likely_regression_surface),
            missing_verification=list(result_data.missing_verification),
            suggested_follow_up_cases=list(result_data.suggested_follow_up_cases),
            findings=list(result_data.findings),
            knowledge_hits=list(result_data.knowledge_hits),
            review_request_path=context.managed_paths.review_request_path,
            retrieval_path=context.managed_paths.retrieval_path,
            review_result_path=host_paths.review_result_path,
            review_orchestration_path=host_paths.review_orchestration_path,
            artifact_manifest_path=host_paths.artifact_manifest_path,
            diagnostics_path=host_paths.diagnostics_path,
            llm_transcript_path=context.managed_paths.llm_transcript_path,
        )

    def _write_manifest(self, *, result: ReviewResult) -> None:
        manifest = self._manifest_service.build_operation_manifest(
            root_dir=result.review_result_path.parent,
            artifacts=self._artifacts_for_manifest(result),
            operation_id=result.operation_id,
            operation_kind="review",
            verification_verdict=None,
            metadata={},
        ).model_copy(
            update={
                "schema_versions": {
                    "review_result": result.schema_version,
                    "review_orchestration": REVIEW_ORCHESTRATION_SCHEMA_VERSION,
                    "operation_diagnostics": OPERATION_DIAGNOSTICS_SCHEMA_VERSION,
                }
            }
        )
        self._manifest_service.write_manifest(result.artifact_manifest_path, manifest)

    def _build_diagnostics(
        self,
        *,
        request: ReviewRequest,
        result: ReviewResult,
        started_at: str,
        duration_ms: int,
        warning_summary: list[str],
        prompt_hit_count: int,
        failure_category: DiagnosticsFailureCategory | None,
        failure_message: str | None,
        status: str,
    ) -> OperationDiagnostics:
        normalized_warnings = list(warning_summary)
        if len(result.knowledge_hits) == 0 and "no knowledge hits were retrieved" not in normalized_warnings:
            normalized_warnings.append("no knowledge hits were retrieved")
        if prompt_hit_count == 0 and result.knowledge_hits and "no prompt hits passed the retrieval gate" not in normalized_warnings:
            normalized_warnings.append("no prompt hits passed the retrieval gate")
        provider, model, role_models, config_fingerprint = self._diagnostics_service.resolve_provider_model(
            resolved_config=self._resolved_config,
            roles=("review",),
        )
        artifact_checks = [
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="review_request",
                path=result.review_request_path,
                required_fields=("changed_files",),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="retrieval",
                path=result.retrieval_path,
                required_fields=("knowledge_hits",),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="review_result",
                path=result.review_result_path,
                required_fields=("risk_summary", "findings"),
                expected_schema_version=result.schema_version,
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="review_orchestration",
                path=result.review_orchestration_path,
                required_fields=("review_hints", "required_cases"),
                expected_schema_version=REVIEW_ORCHESTRATION_SCHEMA_VERSION,
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="artifact_manifest",
                path=result.artifact_manifest_path,
                required_fields=("manifest_version", "primary_artifacts"),
            ),
        ]
        if result.llm_transcript_path is not None:
            artifact_checks.append(
                self._diagnostics_service.build_path_artifact_check(
                    artifact_id="llm_transcript",
                    path=result.llm_transcript_path,
                    required=False,
                )
            )
        return OperationDiagnostics(
            operation_id=result.operation_id,
            operation_kind="review",
            app_id=request.app_id,
            status="succeeded" if status == "succeeded" else "failed",
            verification_verdict=None,
            started_at=started_at,
            finished_at=self._diagnostics_service.now_iso(),
            duration_ms=duration_ms,
            provider=provider,
            model=model,
            role_models=role_models,
            config_fingerprint=config_fingerprint,
            warning_summary=normalized_warnings,
            retry_count=0,
            fallback_count=0,
            failure_category=failure_category,
            failure_stage=REVIEW_RUNTIME_DIAGNOSTICS_STAGE if failure_category is not None else None,
            failure_message=failure_message,
            artifact_checks=artifact_checks,
            contract_versions={
                "review_result": result.schema_version,
                "review_orchestration": REVIEW_ORCHESTRATION_SCHEMA_VERSION,
                "operation_diagnostics": OPERATION_DIAGNOSTICS_SCHEMA_VERSION,
            },
            linked_operation_ids={},
        )

    @staticmethod
    def _artifacts_for_manifest(result: ReviewResult) -> dict[str, str]:
        artifacts = {
            "review_request": str(result.review_request_path),
            "retrieval": str(result.retrieval_path),
            "review_result": str(result.review_result_path),
            "review_orchestration": str(result.review_orchestration_path),
            "artifact_manifest": str(result.artifact_manifest_path),
        }
        if result.diagnostics_path is not None:
            artifacts["diagnostics"] = str(result.diagnostics_path)
        if result.llm_transcript_path is not None:
            artifacts["llm_transcript"] = str(result.llm_transcript_path)
        return artifacts
