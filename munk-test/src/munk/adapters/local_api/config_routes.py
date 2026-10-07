from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from munk.config.profile_config_service import ProfileConfigService

from .config_models import SettingsConfigUpsertRequest
from .response_models import ErrorResponse, SettingsConfigData, SuccessResponse

_CONFIG_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_config_router(*, service_factory: Callable[[], ProfileConfigService] | None = None) -> APIRouter:
    router = APIRouter()

    def get_service() -> ProfileConfigService:
        if service_factory is not None:
            return service_factory()
        return ProfileConfigService(workspace_root=Path.cwd())

    @router.get(
        "/v1/settings/config",
        response_model=SuccessResponse[SettingsConfigData],
        responses=_CONFIG_ERROR_RESPONSES,
    )
    def get_settings_config(response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = get_service().load_editor_state()
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "settings_config_get", "settings_config_get_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "settings_config_get",
            "data": SettingsConfigData.model_validate(data).model_dump(mode="json"),
        }

    @router.put(
        "/v1/settings/config",
        response_model=SuccessResponse[SettingsConfigData],
        responses=_CONFIG_ERROR_RESPONSES,
    )
    def update_settings_config(
        request: SettingsConfigUpsertRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            data = get_service().save_editor_state(request)
        except ValueError as exc:
            return _error_response(422, "settings_config_update", "settings_config_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "settings_config_update", "settings_config_update_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "settings_config_update",
            "data": SettingsConfigData.model_validate(data).model_dump(mode="json"),
        }

    return router


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
