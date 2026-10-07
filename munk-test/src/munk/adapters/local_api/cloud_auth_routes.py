from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from munk.adapters.local_api.cloud_auth_models import (
    CloudLoginStartData,
    CloudSessionSummaryData,
    CloudWorkspacesData,
)
from munk.adapters.local_api.response_models import ErrorResponse, SuccessResponse
from munk.services.cloud.auth_models import CloudBffError
from munk.services.cloud.auth_service import CloudAuthService

_CLOUD_AUTH_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_cloud_auth_router(
    *,
    service_factory: Callable[[], CloudAuthService] | None = None,
) -> APIRouter:
    router = APIRouter()

    def get_service() -> CloudAuthService:
        if service_factory is not None:
            return service_factory()
        return CloudAuthService()

    _register_login_routes(router, get_service)
    _register_session_routes(router, get_service)
    return router


def _register_login_routes(
    router: APIRouter,
    get_service: Callable[[], CloudAuthService],
) -> None:
    @router.post(
        "/v1/cloud/auth/login",
        response_model=SuccessResponse[CloudLoginStartData],
        responses=_CLOUD_AUTH_ERROR_RESPONSES,
    )
    def start_cloud_login(request: Request, response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = get_service().start_login(local_api_base_url=_local_api_base_url(request))
        except CloudBffError as exc:
            return _error_response(exc.status_code, "cloud_auth_login", exc.code, exc.message)
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "cloud_auth_login", "cloud_auth_login_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_auth_login",
            "data": CloudLoginStartData.model_validate(data.model_dump(mode="json")).model_dump(mode="json"),
        }

    @router.get(
        "/v1/cloud/auth/callback",
        include_in_schema=False,
        response_model=None,
    )
    def cloud_auth_callback(request: Request) -> RedirectResponse | JSONResponse:
        return _handle_cloud_auth_callback(request, get_service)


def _register_session_routes(
    router: APIRouter,
    get_service: Callable[[], CloudAuthService],
) -> None:
    @router.get(
        "/v1/cloud/auth/session",
        response_model=SuccessResponse[CloudSessionSummaryData],
        responses=_CLOUD_AUTH_ERROR_RESPONSES,
    )
    def get_cloud_session(response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = get_service().get_session_summary()
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "cloud_auth_session", "cloud_auth_session_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_auth_session",
            "data": CloudSessionSummaryData.model_validate(data.model_dump(mode="json")).model_dump(mode="json"),
        }

    @router.post(
        "/v1/cloud/auth/logout",
        response_model=SuccessResponse[CloudSessionSummaryData],
        responses=_CLOUD_AUTH_ERROR_RESPONSES,
    )
    def logout_cloud_session(response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = get_service().logout()
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "cloud_auth_logout", "cloud_auth_logout_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_auth_logout",
            "data": CloudSessionSummaryData.model_validate(data.model_dump(mode="json")).model_dump(mode="json"),
        }

    @router.get(
        "/v1/cloud/auth/workspaces",
        response_model=SuccessResponse[CloudWorkspacesData],
        responses=_CLOUD_AUTH_ERROR_RESPONSES,
    )
    def list_cloud_workspaces(response: Response) -> dict[str, object] | JSONResponse:
        try:
            workspaces = get_service().list_workspaces()
        except CloudBffError as exc:
            return _error_response(exc.status_code, "cloud_auth_workspaces", exc.code, exc.message)
        except Exception as exc:  # noqa: BLE001
            return _error_response(
                500,
                "cloud_auth_workspaces",
                "cloud_auth_workspaces_failed",
                str(exc),
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "cloud_auth_workspaces",
            "data": CloudWorkspacesData(workspaces=[item.model_dump(mode="json") for item in workspaces]).model_dump(
                mode="json"
            ),
        }


def _handle_cloud_auth_callback(
    request: Request,
    get_service: Callable[[], CloudAuthService],
) -> RedirectResponse:
    handoff_code = _query_str(request, "handoff_code")
    state = _query_str(request, "state")
    error = _query_str(request, "error")
    cloud_page_base = _web_ui_cloud_url(request)

    if error:
        return RedirectResponse(
            url=_with_query(cloud_page_base, {"cloud": "error", "message": error}),
            status_code=302,
        )
    if not handoff_code or not state:
        return RedirectResponse(
            url=_with_query(
                cloud_page_base,
                {"cloud": "error", "message": "missing_handoff_or_state"},
            ),
            status_code=302,
        )

    try:
        get_service().complete_login(
            handoff_code=handoff_code,
            state=state,
            local_api_base_url=_local_api_base_url(request),
        )
    except CloudBffError as exc:
        return RedirectResponse(
            url=_with_query(
                cloud_page_base,
                {"cloud": "error", "message": exc.code},
            ),
            status_code=302,
        )
    except Exception:  # noqa: BLE001
        return RedirectResponse(
            url=_with_query(
                cloud_page_base,
                {"cloud": "error", "message": "cloud_auth_callback_failed"},
            ),
            status_code=302,
        )

    return RedirectResponse(
        url=_with_query(cloud_page_base, {"cloud": "connected"}),
        status_code=302,
    )


def _local_api_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _web_ui_cloud_url(request: Request) -> str:
    return f"{_local_api_base_url(request)}/cloud"


def _with_query(url: str, params: dict[str, str]) -> str:
    return f"{url}?{urlencode(params)}"


def _query_str(request: Request, key: str) -> str:
    value = request.query_params.get(key)
    return value.strip() if isinstance(value, str) else ""


def _error_response(status_code: int, command: str, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "command": command,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )
