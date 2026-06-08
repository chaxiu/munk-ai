from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from munk.adapters.local_api.app_context import LocalApiAppContext
from munk.adapters.local_api.app_lifespan import build_local_api_lifespan
from munk.adapters.local_api.app_routes import build_app_router
from munk.adapters.local_api.config_routes import build_config_router
from munk.adapters.local_api.device_routes import build_device_router
from munk.adapters.local_api.knowledge_routes import build_knowledge_router
from munk.adapters.local_api.mcp_mount import build_local_api_mcp_servers, mount_local_api_mcp
from munk.adapters.local_api.operation_routes import build_operation_router
from munk.adapters.local_api.plan_routes import build_plan_router
from munk.adapters.local_api.recording_routes import build_recording_router
from munk.adapters.local_api.route_helpers import error_response, log_500_response, response_body_preview
from munk.adapters.local_api.schedule_routes import build_schedule_router
from munk.adapters.local_api.ui_routes import (
    build_ui_router,
    recording_ui_dist,
    recording_ui_index_response,
    recording_ui_static_response,
)
from munk.services.recording.session_service import RecordingSessionService

DEFAULT_LOCAL_API_HOST = "127.0.0.1"
DEFAULT_LOCAL_API_PORT = 16888
_logger = logging.getLogger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _recording_ui_dist() -> Path:
    return recording_ui_dist(project_root=_PROJECT_ROOT)


def _recording_ui_index_response() -> FileResponse | JSONResponse:
    return recording_ui_index_response(dist_root=_recording_ui_dist())


def _recording_ui_static_response(path: str) -> FileResponse | None:
    return recording_ui_static_response(dist_root=_recording_ui_dist(), path=path)


def create_local_api_app(
    *,
    start_recording_bridge: bool = True,
    recording_service: RecordingSessionService | None = None,
    enable_mcp: bool = True,
    mcp_host: str = DEFAULT_LOCAL_API_HOST,
    mcp_port: int = DEFAULT_LOCAL_API_PORT,
) -> FastAPI:
    context = LocalApiAppContext(
        project_root=_PROJECT_ROOT,
        workspace_root=Path.cwd(),
        start_recording_bridge=start_recording_bridge,
        recording_service=recording_service,
    )
    mcp_servers = build_local_api_mcp_servers(
        context,
        enable_mcp=enable_mcp,
        host=mcp_host,
        port=mcp_port,
    )
    app = FastAPI(
        title="Munk AI Local API",
        version="0.1.0",
        lifespan=build_local_api_lifespan(
            context=context,
            orchestration_mcp_server=mcp_servers.orchestration,
            device_mcp_server=mcp_servers.device,
        ),
    )

    @app.middleware("http")
    async def log_internal_server_errors(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if response.status_code >= 500 and not getattr(request.state, "exception_logged", False):
            log_500_response(request, response, await response_body_preview(response))
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: ANN202
        request.state.exception_logged = True
        _logger.exception(
            "local api request crashed: method=%s path=%s query=%s",
            request.method,
            request.url.path,
            request.url.query or "-",
        )
        return error_response(
            status_code=500,
            command="request_failed",
            code="internal_server_error",
            message=str(exc) or "internal server error",
        )

    app.include_router(build_app_router())
    app.include_router(build_config_router())
    app.include_router(build_device_router())
    app.include_router(build_knowledge_router())
    app.include_router(build_plan_router())
    app.include_router(build_recording_router(service_factory=context.get_recording_service))
    app.include_router(build_schedule_router())
    app.include_router(build_operation_router(context))
    if enable_mcp:
        mount_local_api_mcp(app, mcp_servers)
    app.include_router(
        build_ui_router(
            index_response_factory=_recording_ui_index_response,
            static_response_factory=_recording_ui_static_response,
        )
    )
    return app
