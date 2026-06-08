from __future__ import annotations

import mimetypes
from typing import Any, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse, JSONResponse

from munk.adapters.local_api.app_context import LocalApiAppContext
from munk.adapters.local_api.artifact_readers import (
    ArtifactNotFoundError,
    build_operation_artifacts_data,
    list_artifact_children,
    resolve_artifact_child_path,
    resolve_artifact_content,
    resolve_artifact_ref,
)
from munk.adapters.local_api.response_models import (
    CancelOperationData,
    ErrorResponse,
    OperationArtifactsData,
    OperationSubmissionData,
    ReproduceOperationData,
    RunArtifactChildrenData,
    RunArtifactContentData,
    SuccessResponse,
)
from munk.adapters.shared.dashboard_queries import build_dashboard_summary_payload
from munk.adapters.shared.machine_requests import (
    PlanCliRequest,
    ReviewCliRequest,
    RunCaseCliRequest,
    RunPlanCliRequest,
    RunPlansCliRequest,
    VerifyChangeCliRequest,
)
from munk.adapters.shared.payload_models import (
    DashboardSummaryData,
    OperationChildrenData,
    OperationDetailData,
    OperationEventsData,
    OperationListData,
)
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.operations.models import OperationKind, OperationStatus
from munk.services.operations.registry import OperationRegistry

from .route_helpers import (
    artifact_error_response,
    build_submit_argv,
    error_response,
    machine_route_response,
    operation_summary_payload,
)

_SUBMIT_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
_RUN_QUERY_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_operation_router(context: LocalApiAppContext) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @router.get(
        "/v1/dashboard/summary",
        response_model=SuccessResponse[DashboardSummaryData],
        responses={500: {"model": ErrorResponse}},
    )
    def dashboard_summary(response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = build_dashboard_summary_payload()
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="dashboard_summary",
                code="dashboard_summary_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "dashboard_summary",
            "data": data.model_dump(mode="json"),
        }

    @router.post(
        "/v1/plan",
        response_model=SuccessResponse[OperationSubmissionData],
        responses=_SUBMIT_ERROR_RESPONSES,
    )
    def plan(
        request: PlanCliRequest,
        response: Response,
        wait: bool = Query(True),
        detach: bool = Query(False),
    ) -> dict[str, object] | JSONResponse:
        command_response = context.get_machine_service().submit_plan(
            request=request.to_requirement_input(),
            plan_execution_request=request.to_plan_execution_request() if request.auto_run else None,
            wait=wait,
            detach=detach,
            detached_argv=build_submit_argv("plan", request.model_dump(mode="json")) if detach else None,
            background_submitter=context.background_operation_supervisor.submit if not wait and not detach else None,
        )
        return machine_route_response(response, command_response)

    @router.post(
        "/v1/run/case",
        response_model=SuccessResponse[OperationSubmissionData],
        responses=_SUBMIT_ERROR_RESPONSES,
    )
    def run_case(
        request: RunCaseCliRequest,
        response: Response,
        wait: bool = Query(True),
        detach: bool = Query(False),
    ) -> dict[str, object] | JSONResponse:
        command_response = context.get_machine_service().submit_run_case(
            request=request.to_plan_execution_request(),
            case_id=request.case_id,
            wait=wait,
            detach=detach,
            detached_argv=build_submit_argv("run_case", request.model_dump(mode="json")) if detach else None,
            background_submitter=context.background_operation_supervisor.submit if not wait and not detach else None,
        )
        return machine_route_response(response, command_response)

    @router.post(
        "/v1/run/plan",
        response_model=SuccessResponse[OperationSubmissionData],
        responses=_SUBMIT_ERROR_RESPONSES,
    )
    def run_plan(
        request: RunPlanCliRequest,
        response: Response,
        wait: bool = Query(True),
        detach: bool = Query(False),
    ) -> dict[str, object] | JSONResponse:
        command_response = context.get_machine_service().submit_run_plan(
            request=request.to_plan_execution_request(),
            wait=wait,
            detach=detach,
            detached_argv=build_submit_argv("run_plan", request.model_dump(mode="json")) if detach else None,
            background_submitter=context.background_operation_supervisor.submit if not wait and not detach else None,
        )
        return machine_route_response(response, command_response)

    @router.post(
        "/v1/run/plans",
        response_model=SuccessResponse[OperationSubmissionData],
        responses=_SUBMIT_ERROR_RESPONSES,
    )
    def run_plans(
        request: RunPlansCliRequest,
        response: Response,
        wait: bool = Query(True),
        detach: bool = Query(False),
    ) -> dict[str, object] | JSONResponse:
        command_response = context.get_machine_service().submit_run_plans(
            request=request,
            wait=wait,
            detach=detach,
            detached_argv=build_submit_argv("run_plans", request.model_dump(mode="json")) if detach else None,
            background_submitter=context.background_operation_supervisor.submit if not wait and not detach else None,
        )
        return machine_route_response(response, command_response)

    @router.post(
        "/v1/verify/change",
        response_model=SuccessResponse[OperationSubmissionData],
        responses=_SUBMIT_ERROR_RESPONSES,
    )
    def verify_change(
        request: VerifyChangeCliRequest,
        response: Response,
        wait: bool = Query(True),
        detach: bool = Query(False),
    ) -> dict[str, object] | JSONResponse:
        command_response = context.get_machine_service().submit_verify_change(
            request=request,
            wait=wait,
            detach=detach,
            detached_argv=build_submit_argv("verify_change", request.model_dump(mode="json")) if detach else None,
            background_submitter=context.background_operation_supervisor.submit if not wait and not detach else None,
        )
        return machine_route_response(response, command_response)

    @router.post(
        "/v1/review",
        response_model=SuccessResponse[OperationSubmissionData],
        responses=_SUBMIT_ERROR_RESPONSES,
    )
    def review(
        request: ReviewCliRequest,
        response: Response,
        wait: bool = Query(True),
        detach: bool = Query(False),
    ) -> dict[str, object] | JSONResponse:
        command_response = context.get_machine_service().submit_review(
            request=request,
            wait=wait,
            detach=detach,
            detached_argv=build_submit_argv("review", request.model_dump(mode="json")) if detach else None,
            background_submitter=context.background_operation_supervisor.submit if not wait and not detach else None,
        )
        return machine_route_response(response, command_response)

    @router.get(
        "/v1/runs",
        response_model=SuccessResponse[OperationListData],
        responses={500: {"model": ErrorResponse}},
    )
    def runs_list(
        response: Response,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        status: OperationStatus | None = Query(None),
        kind: OperationKind | None = Query(None),
        device_ref: str | None = Query(None),
        surface: str | None = Query(None),
        verification_verdict: str | None = Query(None),
        platform: str | None = Query(None),
        query: str | None = Query(None),
        run_type: str | None = Query(None),
    ) -> dict[str, object] | JSONResponse:
        try:
            items, total = OperationRegistry().list_operations_page(
                limit=limit,
                offset=offset,
                status=status,
                kind=kind,
                device_ref=device_ref,
                surface=surface,
                verification_verdict=verification_verdict,
                platform=platform,
                query=query,
                run_type=run_type,
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="runs_list",
                code="runs_list_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "runs_list",
            "data": {
                "items": [operation_summary_payload(item).model_dump(mode="json") for item in items],
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        }

    @router.get(
        "/v1/runs/{operation_id}",
        response_model=SuccessResponse[OperationDetailData],
        responses=_RUN_QUERY_ERROR_RESPONSES,
    )
    def runs_get(operation_id: str, response: Response) -> dict[str, object] | JSONResponse:
        return machine_route_response(
            response,
            context.get_machine_service().get_operation(operation_id=operation_id),
        )

    @router.get(
        "/v1/runs/{operation_id}/events",
        response_model=SuccessResponse[OperationEventsData],
        responses=_RUN_QUERY_ERROR_RESPONSES,
    )
    def runs_events(
        operation_id: str,
        response: Response,
        after_seq: int = Query(0),
        limit: int = Query(100),
    ) -> dict[str, object] | JSONResponse:
        command_response = context.get_machine_service().list_operation_events(
            operation_id=operation_id,
            after_seq=after_seq,
            limit=limit,
        )
        return machine_route_response(response, command_response)

    @router.get(
        "/v1/runs/{operation_id}/children",
        response_model=SuccessResponse[OperationChildrenData],
        responses=_RUN_QUERY_ERROR_RESPONSES,
    )
    def runs_children(operation_id: str, response: Response) -> dict[str, object] | JSONResponse:
        return machine_route_response(
            response,
            context.get_machine_service().get_operation_children(operation_id=operation_id),
        )

    @router.get(
        "/v1/runs/{operation_id}/artifacts",
        response_model=SuccessResponse[OperationArtifactsData],
        responses=_RUN_QUERY_ERROR_RESPONSES,
    )
    def runs_artifacts(operation_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            record = OperationRegistry().get_operation(operation_id)
            data = build_operation_artifacts_data(
                record,
                manifest_service=ArtifactManifestService(),
                content_url_for=lambda artifact_id: (
                    f"/v1/runs/{operation_id}/artifacts/{artifact_id}/content"
                ),
                download_url_for=lambda artifact_id: (
                    f"/v1/runs/{operation_id}/artifacts/{artifact_id}/download"
                ),
                artifact_summary=context.get_machine_service()._query_service.artifact_summary(record),  # noqa: SLF001
            )
        except Exception as exc:  # noqa: BLE001
            return artifact_error_response(command="runs_artifacts", exc=cast(Exception, exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "runs_artifacts",
            "data": data.model_dump(mode="json"),
            "artifacts": record.artifacts_json,
        }

    @router.get(
        "/v1/runs/{operation_id}/artifacts/{artifact_id}/children",
        response_model=SuccessResponse[RunArtifactChildrenData],
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def runs_artifact_children(
        operation_id: str,
        artifact_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            record = OperationRegistry().get_operation(operation_id)
            data = list_artifact_children(
                record,
                artifact_id=artifact_id,
                manifest_service=ArtifactManifestService(),
                content_url_for=lambda child_id: (
                    f"/v1/runs/{operation_id}/artifacts/{artifact_id}/children/{child_id}/content"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return artifact_error_response(command="runs_artifact_children", exc=cast(Exception, exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "runs_artifact_children",
            "data": data.model_dump(mode="json"),
        }

    @router.get(
        "/v1/runs/{operation_id}/artifacts/{artifact_id}/children/{child_id}/content",
        response_model=None,
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def runs_artifact_child_content(
        operation_id: str,
        artifact_id: str,
        child_id: str,
    ) -> Response:
        try:
            record = OperationRegistry().get_operation(operation_id)
            child_path = resolve_artifact_child_path(
                record,
                artifact_id=artifact_id,
                child_id=child_id,
                manifest_service=ArtifactManifestService(),
            )
        except Exception as exc:  # noqa: BLE001
            return artifact_error_response(command="runs_artifact_child_content", exc=cast(Exception, exc))
        return FileResponse(
            path=child_path,
            media_type=mimetypes.guess_type(str(child_path))[0] or "application/octet-stream",
            filename=child_path.name,
        )

    @router.get(
        "/v1/runs/{operation_id}/artifacts/{artifact_id}/content",
        response_model=SuccessResponse[RunArtifactContentData],
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def runs_artifact_content(
        operation_id: str,
        artifact_id: str,
        response: Response,
        max_bytes: int = Query(100_000, ge=1, le=1_000_000),
    ) -> dict[str, object] | JSONResponse:
        try:
            record = OperationRegistry().get_operation(operation_id)
            content = resolve_artifact_content(
                record,
                artifact_id=artifact_id,
                manifest_service=ArtifactManifestService(),
                max_bytes=max_bytes,
            )
        except Exception as exc:  # noqa: BLE001
            return artifact_error_response(command="runs_artifact_content", exc=cast(Exception, exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "runs_artifact_content",
            "data": content.model_dump(mode="json"),
        }

    @router.get(
        "/v1/runs/{operation_id}/artifacts/{artifact_id}/download",
        response_model=None,
        responses={
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def runs_artifact_download(
        operation_id: str,
        artifact_id: str,
    ) -> Response:
        try:
            record = OperationRegistry().get_operation(operation_id)
            ref = resolve_artifact_ref(
                record,
                artifact_id=artifact_id,
                manifest_service=ArtifactManifestService(),
            )
        except Exception as exc:  # noqa: BLE001
            return artifact_error_response(command="runs_artifact_download", exc=cast(Exception, exc))
        if not ref.exists:
            return artifact_error_response(
                command="runs_artifact_download",
                exc=ArtifactNotFoundError(f"artifact not found: {artifact_id}"),
            )
        return FileResponse(
            path=ref.path,
            media_type=ref.media_type or "application/octet-stream",
            filename=ref.path.name,
        )

    @router.post(
        "/v1/runs/{operation_id}/cancel",
        response_model=SuccessResponse[CancelOperationData],
        responses=_RUN_QUERY_ERROR_RESPONSES,
    )
    def runs_cancel(operation_id: str, response: Response) -> dict[str, object] | JSONResponse:
        return machine_route_response(
            response,
            context.get_machine_service().cancel_operation(operation_id=operation_id),
        )

    @router.post(
        "/v1/runs/{operation_id}/reproduce",
        response_model=SuccessResponse[ReproduceOperationData],
        responses=_RUN_QUERY_ERROR_RESPONSES,
    )
    def runs_reproduce(operation_id: str, response: Response) -> dict[str, object] | JSONResponse:
        return machine_route_response(
            response,
            context.get_machine_service().reproduce_operation(operation_id=operation_id),
        )

    return router
