from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.shared.device_queries import list_devices_payload
from munk.adapters.shared.payload_models import DeviceListData

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
        except ValueError as exc:
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

    return router
