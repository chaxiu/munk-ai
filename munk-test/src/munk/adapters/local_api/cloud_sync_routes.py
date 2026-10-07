from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.local_api.cloud_sync_models import (
    CloudAppsData,
    CloudAppSummaryData,
    CloudLinkActiveRequest,
    CloudLinkData,
    CloudLinksData,
    CloudLinkUpsertRequest,
    CloudSyncPublishRequest,
    CloudSyncPublishResultData,
    CloudSyncPullRequest,
    CloudSyncPullResultData,
    CloudSyncPushRequest,
    CloudSyncPushResultData,
    CloudSyncStatusData,
)
from munk.adapters.local_api.response_models import ErrorResponse, SuccessResponse
from munk.adapters.local_api.route_helpers import error_response
from munk.services.cloud.auth_models import CloudBffError
from munk.services.cloud.sync_models import LocalSyncConflictError
from munk.services.cloud.sync_service import CloudSyncService

_CLOUD_SYNC_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_cloud_sync_router(
    *,
    service_factory: Callable[[], CloudSyncService] | None = None,
) -> APIRouter:
    router = APIRouter()

    def get_service() -> CloudSyncService:
        if service_factory is not None:
            return service_factory()
        return CloudSyncService()

    _register_links_routes(router, get_service)
    _register_apps_routes(router, get_service)
    _register_sync_status_routes(router, get_service)
    _register_sync_pull_routes(router, get_service)
    _register_sync_push_routes(router, get_service)
    _register_publish_routes(router, get_service)
    return router


def _register_links_routes(
    router: APIRouter,
    get_service: Callable[[], CloudSyncService],
) -> None:
    @router.get(
        "/v1/cloud/links",
        response_model=SuccessResponse[CloudLinksData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def get_cloud_links(response: Response) -> dict[str, object] | JSONResponse:
        try:
            view = get_service().list_links()
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_links_get",
                code="cloud_links_get_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_links_get",
            "data": CloudLinksData.model_validate(view.model_dump(mode="json")).model_dump(
                mode="json"
            ),
        }

    @router.put(
        "/v1/cloud/links",
        response_model=SuccessResponse[CloudLinkData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def put_cloud_link(
        request: CloudLinkUpsertRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            link = get_service().link_app(
                workspace_id=request.workspace_id,
                app_id=request.app_id,
                workspace_name=request.workspace_name,
                role=request.role,
            )
        except CloudBffError as exc:
            return error_response(
                status_code=exc.status_code,
                command="cloud_links_put",
                code=exc.code,
                message=exc.message,
            )
        except ValueError as exc:
            return error_response(
                status_code=422,
                command="cloud_links_put",
                code="invalid_link",
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_links_put",
                code="cloud_links_put_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_links_put",
            "data": CloudLinkData.model_validate(link.model_dump(mode="json")).model_dump(
                mode="json"
            ),
        }

    @router.put(
        "/v1/cloud/links/active",
        response_model=SuccessResponse[CloudLinksData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def put_cloud_link_active(
        request: CloudLinkActiveRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            view = get_service().set_active_app(app_id=request.app_id)
        except CloudBffError as exc:
            return error_response(
                status_code=exc.status_code,
                command="cloud_links_active_put",
                code=exc.code,
                message=exc.message,
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_links_active_put",
                code="cloud_links_active_put_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_links_active_put",
            "data": CloudLinksData.model_validate(view.model_dump(mode="json")).model_dump(
                mode="json"
            ),
        }

    @router.delete(
        "/v1/cloud/links/{app_id}",
        response_model=SuccessResponse[CloudLinksData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def delete_cloud_link(
        app_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            view = get_service().unlink_app(app_id=app_id)
        except ValueError as exc:
            return error_response(
                status_code=422,
                command="cloud_links_delete",
                code="invalid_link",
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_links_delete",
                code="cloud_links_delete_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_links_delete",
            "data": CloudLinksData.model_validate(view.model_dump(mode="json")).model_dump(
                mode="json"
            ),
        }


def _register_apps_routes(
    router: APIRouter,
    get_service: Callable[[], CloudSyncService],
) -> None:
    @router.get(
        "/v1/cloud/apps",
        response_model=SuccessResponse[CloudAppsData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def list_cloud_apps(
        response: Response,
        workspace_id: str = Query(..., min_length=1),
    ) -> dict[str, object] | JSONResponse:
        try:
            apps = get_service().list_apps(workspace_id=workspace_id)
        except CloudBffError as exc:
            return error_response(
                status_code=exc.status_code,
                command="cloud_apps_list",
                code=exc.code,
                message=exc.message,
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_apps_list",
                code="cloud_apps_list_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_apps_list",
            "data": CloudAppsData(
                workspace_id=workspace_id,
                apps=[CloudAppSummaryData.model_validate(item.model_dump(mode="json")) for item in apps],
            ).model_dump(mode="json"),
        }


def _register_sync_status_routes(
    router: APIRouter,
    get_service: Callable[[], CloudSyncService],
) -> None:
    @router.get(
        "/v1/cloud/sync/status",
        response_model=SuccessResponse[CloudSyncStatusData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def get_cloud_sync_status(
        response: Response,
        app_id: str | None = Query(default=None),
    ) -> dict[str, object] | JSONResponse:
        try:
            status = get_service().get_status(app_id=app_id)
        except CloudBffError as exc:
            return error_response(
                status_code=exc.status_code,
                command="cloud_sync_status",
                code=exc.code,
                message=exc.message,
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_sync_status",
                code="cloud_sync_status_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_sync_status",
            "data": CloudSyncStatusData.model_validate(status.model_dump(mode="json")).model_dump(
                mode="json"
            ),
        }


def _register_sync_pull_routes(
    router: APIRouter,
    get_service: Callable[[], CloudSyncService],
) -> None:
    @router.post(
        "/v1/cloud/sync/pull",
        response_model=SuccessResponse[CloudSyncPullResultData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def post_cloud_sync_pull(
        response: Response,
        request: CloudSyncPullRequest | None = None,
    ) -> dict[str, object] | JSONResponse:
        body = request or CloudSyncPullRequest()
        try:
            result = get_service().pull(force=body.force, app_id=body.app_id)
        except LocalSyncConflictError as exc:
            return error_response(
                status_code=409,
                command="cloud_sync_pull",
                code=exc.code,
                message=exc.message,
                details=exc.details(),
            )
        except CloudBffError as exc:
            return error_response(
                status_code=exc.status_code,
                command="cloud_sync_pull",
                code=exc.code,
                message=exc.message,
            )
        except ValueError as exc:
            return error_response(
                status_code=422,
                command="cloud_sync_pull",
                code="cloud_sync_pull_invalid",
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_sync_pull",
                code="cloud_sync_pull_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_sync_pull",
            "data": CloudSyncPullResultData.model_validate(result.model_dump(mode="json")).model_dump(
                mode="json"
            ),
        }


def _register_sync_push_routes(
    router: APIRouter,
    get_service: Callable[[], CloudSyncService],
) -> None:
    @router.post(
        "/v1/cloud/sync/push",
        response_model=SuccessResponse[CloudSyncPushResultData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def post_cloud_sync_push(
        response: Response,
        request: CloudSyncPushRequest | None = None,
    ) -> dict[str, object] | JSONResponse:
        body = request or CloudSyncPushRequest()
        try:
            result = get_service().push(force=body.force, app_id=body.app_id)
        except CloudBffError as exc:
            return error_response(
                status_code=exc.status_code,
                command="cloud_sync_push",
                code=exc.code,
                message=exc.message,
                details=_cloud_bff_error_details(exc),
            )
        except ValueError as exc:
            return error_response(
                status_code=422,
                command="cloud_sync_push",
                code="cloud_sync_push_invalid",
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_sync_push",
                code="cloud_sync_push_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_sync_push",
            "data": CloudSyncPushResultData.model_validate(result.model_dump(mode="json")).model_dump(
                mode="json"
            ),
        }


def _register_publish_routes(
    router: APIRouter,
    get_service: Callable[[], CloudSyncService],
) -> None:
    @router.post(
        "/v1/cloud/sync/publish",
        response_model=SuccessResponse[CloudSyncPublishResultData],
        responses=_CLOUD_SYNC_ERROR_RESPONSES,
    )
    def post_cloud_sync_publish(
        request: CloudSyncPublishRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = get_service().publish(
                workspace_id=request.workspace_id,
                app_id=request.app_id,
                workspace_name=request.workspace_name,
            )
        except CloudBffError as exc:
            return error_response(
                status_code=exc.status_code,
                command="cloud_sync_publish",
                code=exc.code,
                message=exc.message,
                details=_cloud_bff_error_details(exc) or _publish_error_details(exc),
            )
        except ValueError as exc:
            return error_response(
                status_code=422,
                command="cloud_sync_publish",
                code="cloud_sync_publish_invalid",
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return error_response(
                status_code=500,
                command="cloud_sync_publish",
                code="cloud_sync_publish_failed",
                message=str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_sync_publish",
            "data": CloudSyncPublishResultData.model_validate(
                result.model_dump(mode="json")
            ).model_dump(mode="json"),
        }


def _publish_error_details(exc: CloudBffError) -> dict[str, object] | None:
    raw = exc.details
    if not isinstance(raw, dict):
        return None
    details: dict[str, object] = {}
    for key in ("workspace_id", "app_id", "revision"):
        value = raw.get(key)
        if value is not None:
            details[key] = value
    return details or None


def _cloud_bff_error_details(exc: CloudBffError) -> dict[str, object] | None:
    """Normalize BFF error payloads for Local API clients (esp. revision conflicts)."""
    raw = exc.details
    if not isinstance(raw, dict):
        return None

    data = raw.get("data")
    source = data if isinstance(data, dict) else raw
    details: dict[str, object] = {}

    expected = source.get("expected_revision")
    current = source.get("current_revision")
    if isinstance(expected, int):
        details["expected_revision"] = expected
    elif isinstance(expected, float) and expected.is_integer():
        details["expected_revision"] = int(expected)
    if isinstance(current, int):
        details["current_revision"] = current
    elif isinstance(current, float) and current.is_integer():
        details["current_revision"] = int(current)

    if details:
        return details
    return None
