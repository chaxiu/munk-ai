from __future__ import annotations

from typing import Any

from munk.config import ResolvedConfig
from munk.reviewing.models import ReviewRequest
from munk.reviewing.orchestration_models import REVIEW_ORCHESTRATION_SCHEMA_VERSION
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.operations.command_helpers import artifact_manifest_version, load_contract_versions
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.services.review_runtime import resolve_review_runtime
from munk.services.reviewing.materializer import ReviewArtifactMaterializer
from munk.services.reviewing.runtime_host import build_review_cancel_controller, build_review_runtime_context


class ReviewOperationService:
    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: ReviewRequest,
        resolved_config: ResolvedConfig,
    ) -> OperationCommandResult:
        diagnostics_service = OperationDiagnosticsService()
        review_runtime = resolve_review_runtime(resolved_config=resolved_config)
        built_context = build_review_runtime_context(tracker=tracker, request=request)
        context = built_context.runtime_context
        host_paths = built_context.host_paths
        cancel_controller = build_review_cancel_controller(tracker=tracker)
        materializer = ReviewArtifactMaterializer(resolved_config=resolved_config)
        try:
            runtime_output = review_runtime.review(
                request,
                context=context,
                cancel_controller=cancel_controller,
            )
        except Exception as exc:
            tracker.update_artifacts(
                materializer.materialize_failure(
                    request=request,
                    context=context,
                    host_paths=host_paths,
                    exc=exc,
                )
            )
            raise
        materialized = materializer.materialize_success(
            runtime_output=runtime_output,
            request=request,
            context=context,
            host_paths=host_paths,
        )
        result = materialized.result
        data: dict[str, Any] = {
            "app_id": result.app_id,
            "finding_count": result.finding_count,
            "high_risk_count": result.high_risk_count,
            "risk_summary": result.risk_summary,
            "review_request_path": str(result.review_request_path),
            "review_result_path": str(result.review_result_path),
            "review_orchestration_path": str(result.review_orchestration_path),
            "retrieval_path": str(result.retrieval_path),
            "artifact_manifest_path": str(result.artifact_manifest_path),
            "contract_versions": load_contract_versions(
                manifest_path=result.artifact_manifest_path,
                fallback={
                    "review_result": result.schema_version,
                    "review_orchestration": REVIEW_ORCHESTRATION_SCHEMA_VERSION,
                },
            ),
        }
        if result.diagnostics_path is not None:
            diagnostics_summary = diagnostics_service.load(result.diagnostics_path)
            data["diagnostics_path"] = str(result.diagnostics_path)
            data["duration_ms"] = diagnostics_summary.duration_ms
            data["failure_category"] = diagnostics_summary.failure_category
            data["warning_summary"] = list(diagnostics_summary.warning_summary)
        if result.llm_transcript_path is not None:
            data["llm_transcript_path"] = str(result.llm_transcript_path)
        data["artifact_manifest_version"] = artifact_manifest_version(result.artifact_manifest_path)
        artifacts = dict(materialized.artifacts)
        return OperationCommandResult(
            data=data,
            artifacts=artifacts,
            verification_verdict=None,
            result_json={**data, "artifacts": artifacts},
            status="succeeded",
        )
