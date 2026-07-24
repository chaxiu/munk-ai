from __future__ import annotations

from typing import Any, Literal, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.shared.device_control import DeviceControlService
from munk.adapters.shared.device_queries import list_devices_payload
from munk.adapters.shared.payload_models import (
    DeviceInstallData,
    DeviceInstallRequest,
    DeviceListData,
    DeviceStateData,
    DeviceUnlockData,
)
from munk.services.device_install_service import DeviceInstallService
from munk.services.errors import DeviceConflictError
from munk.services.machine_contracts import (
    ERROR_DEVICE_CONFLICT,
    ERROR_INVALID_REQUEST,
    ERROR_RUNTIME_ERROR,
    InvalidMachineRequestError,
)

from .response_models import ErrorResponse, SuccessResponse

_DEVICE_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_device_router() -> APIRouter:
    router = APIRouter()

    @router.get(
        "/v1/devices",
        response_model=SuccessResponse[DeviceListData],
        responses=_DEVICE_ERROR_RESPONSES,
    )
    def list_devices(
        response: Response,
        platform: str | None = Query(None),
    ) -> dict[str, object] | JSONResponse:
        return _list_devices(response, platform)

    @router.post(
        "/v1/devices/install",
        response_model=SuccessResponse[DeviceInstallData],
        responses=_DEVICE_ERROR_RESPONSES,
    )
    def install_app(
        response: Response,
        body: DeviceInstallRequest,
    ) -> dict[str, object] | JSONResponse:
        return _install_app(response, body)

    @router.get(
        "/v1/device-state",
        response_model=SuccessResponse[DeviceStateData],
        responses=_DEVICE_ERROR_RESPONSES,
    )
    def get_device_state(
        response: Response,
        device_ref: str = Query(...),
        platform: str | None = Query(None),
    ) -> dict[str, object] | JSONResponse:
        return _get_device_state(response, device_ref=device_ref, platform=platform)

    @router.post(
        "/v1/device-unlock",
        response_model=SuccessResponse[DeviceUnlockData],
        responses=_DEVICE_ERROR_RESPONSES,
    )
    def unlock_device(
        response: Response,
        device_ref: str = Query(...),
        platform: str | None = Query(None),
        strategy: str = Query("swipe"),
    ) -> dict[str, object] | JSONResponse:
        return _unlock_device(response, device_ref=device_ref, platform=platform, strategy=strategy)

    return router


def _error_response(
    *, status_code: int, command: str, code: str, message: str, details: dict[str, object] | None = None
) -> JSONResponse:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "command": command, "error": error},
    )


def _list_devices(response: Response, platform: str | None) -> dict[str, object] | JSONResponse:
    try:
        data = list_devices_payload(platform)
    except (InvalidMachineRequestError, ValueError) as exc:
        return _error_response(
            status_code=422,
            command="devices_list",
            code="device_discovery_unavailable",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            status_code=500,
            command="devices_list",
            code="device_discovery_failed",
            message=str(exc),
        )
    response.status_code = 200
    return {
        "ok": True,
        "command": "devices_list",
        "data": data.model_dump(mode="json"),
    }


def _install_app(response: Response, body: DeviceInstallRequest) -> dict[str, object] | JSONResponse:
    try:
        result = DeviceInstallService().install(
            device_ref=body.device_ref,
            artifact_path=body.artifact_path,
            app_target=body.app_target,
        )
        data = DeviceInstallData(
            operation_id=result.operation_id,
            action=result.action,
            app_id=result.app_id,
            platform=result.platform,
            device_ref=result.device_ref,
            entry_identity=result.entry_identity,
            artifact_path=result.artifact_path,
        )
    except DeviceConflictError as exc:
        return _error_response(
            status_code=409,
            command="app_install",
            code=ERROR_DEVICE_CONFLICT,
            message=str(exc),
            details=cast(dict[str, object], exc.to_details()),
        )
    except InvalidMachineRequestError as exc:
        return _error_response(
            status_code=422,
            command="app_install",
            code=ERROR_INVALID_REQUEST,
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            status_code=500,
            command="app_install",
            code=ERROR_RUNTIME_ERROR,
            message=str(exc),
        )
    response.status_code = 200
    return {
        "ok": True,
        "command": "app_install",
        "data": data.model_dump(mode="json"),
    }


def _get_device_state(
    response: Response,
    *,
    device_ref: str,
    platform: str | None,
) -> dict[str, object] | JSONResponse:
    try:
        data = DeviceControlService().get_state(device_ref=device_ref, platform=platform)
    except InvalidMachineRequestError as exc:
        return _error_response(
            status_code=422,
            command="device_state",
            code="device_state_invalid_request",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            status_code=500,
            command="device_state",
            code="device_state_failed",
            message=str(exc),
        )
    response.status_code = 200
    return {
        "ok": True,
        "command": "device_state",
        "data": data.model_dump(mode="json"),
    }


def _unlock_device(
    response: Response,
    *,
    device_ref: str,
    platform: str | None,
    strategy: str,
) -> dict[str, object] | JSONResponse:
    try:
        if strategy != "swipe":
            raise InvalidMachineRequestError(f"unsupported device_unlock strategy '{strategy}'")
        result = DeviceControlService().unlock(
            device_ref=device_ref,
            platform=platform,
            strategy=cast(Literal["swipe"], "swipe"),
        )
        data = DeviceUnlockData(
            platform=result.platform,
            device_ref=result.device_ref,
            strategy=result.strategy,
            success=result.success,
            changed=result.changed,
            message=result.message,
            before=result.before,
            after=result.after,
        )
    except InvalidMachineRequestError as exc:
        return _error_response(
            status_code=422,
            command="device_unlock",
            code="device_unlock_invalid_request",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            status_code=500,
            command="device_unlock",
            code="device_unlock_failed",
            message=str(exc),
        )
    response.status_code = 200
    return {
        "ok": True,
        "command": "device_unlock",
        "data": data.model_dump(mode="json"),
    }
