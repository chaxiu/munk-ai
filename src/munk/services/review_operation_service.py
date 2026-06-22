from __future__ import annotations

from munk.config import ResolvedConfig
from munk.reviewing.models import ReviewRequest
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.services.review_runtime import resolve_review_runtime
from munk.services.reviewing.materializer import ReviewArtifactMaterializer
from munk.services.reviewing.operation_payloads import build_review_operation_result_payload
from munk.services.reviewing.runtime_host import build_review_cancel_controller, build_review_runtime_context


class ReviewOperationService:
    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: ReviewRequest,
        resolved_config: ResolvedConfig,
    ) -> OperationCommandResult:
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
        artifacts = dict(materialized.artifacts)
        payload = build_review_operation_result_payload(
            result=result,
            diagnostics=materialized.diagnostics,
            artifacts=artifacts,
        )
        return OperationCommandResult(
            data=payload.to_command_data(),
            artifacts=artifacts,
            verification_verdict=None,
            result_json=payload.model_dump(mode="json", exclude_none=True),
            status="succeeded",
        )
