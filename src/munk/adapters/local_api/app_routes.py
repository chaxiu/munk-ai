from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.shared.app_queries import get_app_detail_payload, list_apps_payload
from munk.adapters.shared.payload_models import AppDetailData, AppListData
from munk.app_assets.service import AppAssetService
from munk.app_assets.storage import AppRegistry
from munk.app_knowledge import build_app_knowledge_index
from munk.services.knowledge import validate_app_knowledge_document

from .app_models import AppUpsertRequest
from .response_models import DeleteAppData, ErrorResponse, SuccessResponse

_APP_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_app_router(*, service_factory: Callable[[], AppAssetService] | None = None) -> APIRouter:
    router = APIRouter()

    def get_service() -> AppAssetService:
        if service_factory is not None:
            return service_factory()
        return AppAssetService()

    @router.get(
        "/v1/apps",
        response_model=SuccessResponse[AppListData],
        responses=_APP_ERROR_RESPONSES,
    )
    def list_apps(
        response: Response,
        platform: str | None = Query(None),
    ) -> dict[str, object] | JSONResponse:
        try:
            data = list_apps_payload(service=get_service(), platform=platform)
        except ValueError as exc:
            return _error_response(422, "apps_list", "app_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "apps_list", "apps_list_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "apps_list",
            "data": data.model_dump(mode="json"),
        }

    @router.get(
        "/v1/apps/{app_id}",
        response_model=SuccessResponse[AppDetailData],
        responses=_APP_ERROR_RESPONSES,
    )
    def get_app(app_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = get_app_detail_payload(service=get_service(), app_id=app_id)
        except FileNotFoundError:
            return _error_response(404, "apps_get", "app_not_found", f"app '{app_id}' not found")
        except ValueError as exc:
            return _error_response(422, "apps_get", "app_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "apps_get", "apps_get_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "apps_get",
            "data": data.model_dump(mode="json"),
        }

    @router.post(
        "/v1/apps",
        response_model=SuccessResponse[AppDetailData],
        responses=_APP_ERROR_RESPONSES,
    )
    def create_app(request: AppUpsertRequest, response: Response) -> dict[str, object] | JSONResponse:
        service = get_service()
        try:
            normalized_app_id = AppRegistry.normalize_app_id(request.profile.app_id)
        except ValueError as exc:
            return _error_response(422, "apps_create", "app_validation_failed", str(exc))
        if service.app_registry.exists(normalized_app_id):
            return _error_response(
                409,
                "apps_create",
                "app_already_exists",
                f"app '{normalized_app_id}' already exists",
            )
        try:
            profile = request.profile.to_profile().model_copy(update={"app_id": normalized_app_id})
            if not (request.app_knowledge_content or "").strip():
                raise ValueError("app_knowledge_content must not be empty when creating an app")
            validate_app_knowledge_document(
                request.app_knowledge_content or "",
                expected_app_id=normalized_app_id,
            )
            service.app_registry.save(profile)
            service.app_registry.save_introduction(
                normalized_app_id,
                request.introduction_markdown,
                ref=profile.app_introduction_ref,
            )
            service.app_registry.save_knowledge(
                normalized_app_id,
                request.app_knowledge_content or "",
                ref=profile.app_knowledge_ref,
            )
            build_app_knowledge_index(
                app_id=normalized_app_id,
                assets_root=service.app_registry.root_dir,
                ref=profile.app_knowledge_ref,
            )
            detail = service.build_app_detail(normalized_app_id)
        except Exception as exc:  # noqa: BLE001
            return _error_response(422, "apps_create", "app_validation_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "apps_create",
            "data": AppDetailData(
                profile=detail.profile,
                introduction_markdown=detail.introduction_markdown,
                app_knowledge_content=detail.app_knowledge_content,
                app_knowledge_exists=detail.app_knowledge_exists,
                app_target=detail.profile.to_app_target(),
                plan_count=detail.usage.plan_count,
                case_count=detail.usage.case_count,
            ).model_dump(mode="json"),
        }

    @router.put(
        "/v1/apps/{app_id}",
        response_model=SuccessResponse[AppDetailData],
        responses=_APP_ERROR_RESPONSES,
    )
    def update_app(app_id: str, request: AppUpsertRequest, response: Response) -> dict[str, object] | JSONResponse:
        service = get_service()
        try:
            normalized_path_app_id = AppRegistry.normalize_app_id(app_id)
            normalized_profile_app_id = AppRegistry.normalize_app_id(request.profile.app_id)
        except ValueError as exc:
            return _error_response(422, "apps_update", "app_validation_failed", str(exc))
        if not service.app_registry.exists(normalized_path_app_id):
            return _error_response(404, "apps_update", "app_not_found", f"app '{app_id}' not found")
        if normalized_profile_app_id != normalized_path_app_id:
            return _error_response(
                422,
                "apps_update",
                "app_validation_failed",
                "request profile app_id must match path app_id",
            )
        try:
            profile = request.profile.to_profile().model_copy(update={"app_id": normalized_profile_app_id})
            if (request.app_knowledge_content or "").strip():
                validate_app_knowledge_document(
                    request.app_knowledge_content or "",
                    expected_app_id=normalized_profile_app_id,
                )
            service.app_registry.save(profile)
            service.app_registry.save_introduction(
                normalized_profile_app_id,
                request.introduction_markdown,
                ref=profile.app_introduction_ref,
            )
            if (request.app_knowledge_content or "").strip():
                service.app_registry.save_knowledge(
                    normalized_profile_app_id,
                    request.app_knowledge_content or "",
                    ref=profile.app_knowledge_ref,
                )
                build_app_knowledge_index(
                    app_id=normalized_profile_app_id,
                    assets_root=service.app_registry.root_dir,
                    ref=profile.app_knowledge_ref,
                )
            detail = service.build_app_detail(normalized_profile_app_id)
        except Exception as exc:  # noqa: BLE001
            return _error_response(422, "apps_update", "app_validation_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "apps_update",
            "data": AppDetailData(
                profile=detail.profile,
                introduction_markdown=detail.introduction_markdown,
                app_knowledge_content=detail.app_knowledge_content,
                app_knowledge_exists=detail.app_knowledge_exists,
                app_target=detail.profile.to_app_target(),
                plan_count=detail.usage.plan_count,
                case_count=detail.usage.case_count,
            ).model_dump(mode="json"),
        }

    @router.delete(
        "/v1/apps/{app_id}",
        response_model=SuccessResponse[DeleteAppData],
        responses=_APP_ERROR_RESPONSES,
    )
    def delete_app(app_id: str, response: Response) -> dict[str, object] | JSONResponse:
        service = get_service()
        try:
            normalized_app_id = AppRegistry.normalize_app_id(app_id)
        except ValueError as exc:
            return _error_response(422, "apps_delete", "app_validation_failed", str(exc))
        if not service.app_registry.exists(normalized_app_id):
            return _error_response(404, "apps_delete", "app_not_found", f"app '{app_id}' not found")
        try:
            service.assert_app_deletable(normalized_app_id)
            service.app_registry.delete(normalized_app_id)
        except ValueError as exc:
            return _error_response(409, "apps_delete", "app_in_use", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "apps_delete", "apps_delete_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "apps_delete",
            "data": DeleteAppData(app_id=normalized_app_id).model_dump(mode="json"),
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
