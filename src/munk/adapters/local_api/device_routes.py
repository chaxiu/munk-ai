from __future__ import annotations

from typing import Any, Literal, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.shared.device_control import DeviceControlService
from munk.adapters.shared.device_queries import list_devices_payload
from munk.adapters.shared.payload_models import DeviceListData, DeviceStateData, DeviceUnlockData
from munk.services.machine_contracts import InvalidMachineRequestError

from .response_models import ErrorResponse, SuccessResponse

_DEVICE_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        400: {"model": ErrorResponse},
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
        try:
            data = list_devices_payload(platform)
        except (InvalidMachineRequestError, ValueError) as exc:
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "command": "devices_list",
                    "error": {
                        "code": "device_discovery_unavailable",
                        "message": str(exc),
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "command": "devices_list",
                    "error": {
                        "code": "device_discovery_failed",
                        "message": str(exc),
                    },
                },
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "devices_list",
            "data": data.model_dump(mode="json"),
        }

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
        try:
            data = DeviceControlService().get_state(device_ref=device_ref, platform=platform)
        except InvalidMachineRequestError as exc:
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "command": "device_state",
                    "error": {
                        "code": "device_state_invalid_request",
                        "message": str(exc),
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "command": "device_state",
                    "error": {
                        "code": "device_state_failed",
                        "message": str(exc),
                    },
                },
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "device_state",
            "data": data.model_dump(mode="json"),
        }

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
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "command": "device_unlock",
                    "error": {
                        "code": "device_unlock_invalid_request",
                        "message": str(exc),
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "command": "device_unlock",
                    "error": {
                        "code": "device_unlock_failed",
                        "message": str(exc),
                    },
                },
            )
        response.status_code = 200
        return {
            "ok": True,
            "command": "device_unlock",
            "data": data.model_dump(mode="json"),
        }

    return router
