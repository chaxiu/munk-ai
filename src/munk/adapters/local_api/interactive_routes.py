from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from munk.adapters.local_api.interactive_models import (
    CreateInteractiveSessionRequest,
    FinalizeInteractiveSessionRequest,
    InteractiveSessionAbortData,
    InteractiveSessionCreateData,
    InteractiveSessionFinalizeData,
    InteractiveSessionGetData,
    build_interactive_device_conflict_details,
    project_finalize_data,
    project_interactive_session,
)
from munk.adapters.local_api.response_models import ErrorResponse, SuccessResponse
from munk.config.runtime import require_config_context
from munk.services.errors import DeviceConflictError
from munk.services.interactive import InteractiveService
from munk.services.machine_contracts import (
    MachineCommandResponse,
    build_error_result,
    build_success_result,
)


def build_interactive_router(
    *,
    service_factory: Callable[[], InteractiveService],
    workspace_root: Callable[[], Path],
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/v1/interactive/sessions",
        response_model=SuccessResponse[InteractiveSessionCreateData],
        responses=_interactive_error_responses(400, 404, 409, 422, 500),
    )
    def create_interactive_session(
        request: CreateInteractiveSessionRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        command = "interactive_sessions_create"
        try:
            resolved_config = require_config_context(
                cli_path=Path(request.config_path) if request.config_path else None,
                workspace_root=workspace_root(),
                command_name=command,
            )
            session = service_factory().start_session(
                resolved_config=resolved_config,
                app_target=request.app_target,
                device_ref=request.device_ref,
            )
            result = build_success_result(
                command=command,
                data={"session": project_interactive_session(session).model_dump(mode="json")},
            )
        except Exception as exc:
            return _error_response(command, exc)
        return _success_response(response, result)

    @router.get(
        "/v1/interactive/sessions/{session_id}",
        response_model=SuccessResponse[InteractiveSessionGetData],
        responses=_interactive_error_responses(404, 409, 500),
    )
    def get_interactive_session(
        session_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        command = "interactive_sessions_get"
        try:
            session = service_factory().get_session(session_id)
            result = build_success_result(
                command=command,
                data={"session": project_interactive_session(session).model_dump(mode="json")},
            )
        except Exception as exc:
            return _error_response(command, exc)
        return _success_response(response, result)

    @router.post(
        "/v1/interactive/sessions/{session_id}/finalize",
        response_model=SuccessResponse[InteractiveSessionFinalizeData],
        responses=_interactive_error_responses(400, 404, 409, 422, 500),
    )
    def finalize_interactive_session(
        session_id: str,
        response: Response,
        request: FinalizeInteractiveSessionRequest = FinalizeInteractiveSessionRequest(),
    ) -> dict[str, object] | JSONResponse:
        command = "interactive_sessions_finalize"
        try:
            service = service_factory()
            finalize_result = service.finalize(session_id, request.summary)
            session = service.get_session(session_id)
            data = project_finalize_data(session=session, result=finalize_result)
            result = build_success_result(
                command=command,
                data=data.model_dump(mode="json"),
            )
        except Exception as exc:
            return _error_response(command, exc)
        return _success_response(response, result)

    @router.post(
        "/v1/interactive/sessions/{session_id}/abort",
        response_model=SuccessResponse[InteractiveSessionAbortData],
        responses=_interactive_error_responses(400, 404, 409, 500),
    )
    def abort_interactive_session(
        session_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        command = "interactive_sessions_abort"
        try:
            session = service_factory().abort(session_id)
            result = build_success_result(
                command=command,
                data={"session": project_interactive_session(session).model_dump(mode="json")},
            )
        except Exception as exc:
            return _error_response(command, exc)
        return _success_response(response, result)

    return router


def _interactive_error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {status_code: {"model": ErrorResponse} for status_code in status_codes}


def _success_response(response: Response, result: MachineCommandResponse) -> dict[str, object]:
    response.status_code = result.http_status
    return cast(dict[str, object], result.payload)


def _error_response(command: str, exc: Exception) -> JSONResponse:
    if isinstance(exc, DeviceConflictError):
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "device_conflict",
                    "message": str(exc),
                    "details": build_interactive_device_conflict_details(exc),
                },
            },
        )
    if isinstance(exc, LookupError):
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "interactive_session_not_found",
                    "message": str(exc),
                },
            },
        )
    if isinstance(exc, RuntimeError) and "interactive session already" in str(exc).lower():
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "interactive_invalid_state",
                    "message": str(exc),
                },
            },
        )
    response = build_error_result(command=command, exc=exc)
    return JSONResponse(status_code=response.http_status, content=response.payload)
