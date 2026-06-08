from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.shared.payload_models import (
    ScheduleDetailData,
    ScheduleListData,
    ScheduleRunListData,
    ScheduleSummaryData,
)
from munk.app_assets.storage import AppRegistry
from munk.planning.storage import PlanStore
from munk.scheduling.query_service import ScheduleQueryService
from munk.scheduling.registry import ScheduleRegistry
from munk.scheduling.service import ScheduleService
from munk.services.machine_contracts import build_error_result

from .response_models import ErrorResponse, SuccessResponse
from .schedule_models import ScheduleUpsertRequest

_SCHEDULE_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_schedule_router(
    *,
    registry_factory: Callable[[], ScheduleRegistry] | None = None,
    schedule_service_factory: Callable[[], ScheduleService] | None = None,
    query_service_factory: Callable[[], ScheduleQueryService] | None = None,
) -> APIRouter:
    router = APIRouter()

    def get_registry() -> ScheduleRegistry:
        if registry_factory is not None:
            return registry_factory()
        return ScheduleRegistry()

    def get_schedule_service() -> ScheduleService:
        if schedule_service_factory is not None:
            return schedule_service_factory()
        plan_store = PlanStore()
        return ScheduleService(
            registry=get_registry(),
            plan_store=plan_store,
            app_registry=AppRegistry(plan_store.root_dir),
        )

    def get_query_service() -> ScheduleQueryService:
        if query_service_factory is not None:
            return query_service_factory()
        return ScheduleQueryService(registry=get_registry())

    @router.get(
        "/v1/schedules",
        response_model=SuccessResponse[ScheduleListData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def list_schedules(
        response: Response,
        enabled: bool | None = Query(None),
        app_id: str | None = Query(None),
        keyword: str | None = Query(None),
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> dict[str, object] | JSONResponse:
        return _machine_route_response(
            response,
            get_query_service().list_schedules(
                enabled=enabled,
                app_id=app_id,
                keyword=keyword,
                limit=limit,
                offset=offset,
            ),
        )

    @router.post(
        "/v1/schedules",
        response_model=SuccessResponse[ScheduleDetailData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def create_schedule(request: ScheduleUpsertRequest, response: Response) -> dict[str, object] | JSONResponse:
        try:
            record = get_schedule_service().create_schedule_record(
                name=request.name,
                app_id=request.app_id,
                plan_ids=request.plan_ids,
                device_ref=request.device_ref,
                timezone_name=request.timezone,
                cron_expr=request.cron_expr,
                headless=request.headless,
                fail_fast=request.fail_fast,
                artifact_path=request.artifact_path,
                assets_root=request.assets_root,
                runtime_overrides=request.runtime_overrides,
                enabled=request.enabled,
            )
            data = get_query_service().get_schedule(schedule_id=record.schedule_id)
            return _machine_route_response(response, data)
        except Exception as exc:  # noqa: BLE001
            return _route_error_response(command="schedules_create", exc=cast(Exception, exc))

    @router.get(
        "/v1/schedules/{schedule_id}",
        response_model=SuccessResponse[ScheduleDetailData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def get_schedule(schedule_id: str, response: Response) -> dict[str, object] | JSONResponse:
        return _machine_route_response(response, get_query_service().get_schedule(schedule_id=schedule_id))

    @router.put(
        "/v1/schedules/{schedule_id}",
        response_model=SuccessResponse[ScheduleDetailData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def update_schedule(
        schedule_id: str,
        request: ScheduleUpsertRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            record = get_schedule_service().update_schedule_record(
                schedule_id,
                name=request.name,
                app_id=request.app_id,
                plan_ids=request.plan_ids,
                device_ref=request.device_ref,
                timezone_name=request.timezone,
                cron_expr=request.cron_expr,
                headless=request.headless,
                fail_fast=request.fail_fast,
                artifact_path=request.artifact_path,
                assets_root=request.assets_root,
                runtime_overrides=request.runtime_overrides,
                enabled=request.enabled,
            )
            data = get_query_service().get_schedule(schedule_id=record.schedule_id)
            return _machine_route_response(response, data)
        except Exception as exc:  # noqa: BLE001
            return _route_error_response(command="schedules_update", exc=cast(Exception, exc))

    @router.post(
        "/v1/schedules/{schedule_id}:enable",
        response_model=SuccessResponse[ScheduleSummaryData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def enable_schedule(schedule_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            record = get_schedule_service().enable_schedule(schedule_id)
        except Exception as exc:  # noqa: BLE001
            return _route_error_response(command="schedules_enable", exc=cast(Exception, exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "schedules_enable",
            "data": {
                "schedule_id": record.schedule_id,
                "name": record.name,
                "app_id": record.app_id,
                "plan_ids": [str(item) for item in record.request_json.get("plan_ids", [])],
                "device_ref": record.device_ref,
                "timezone": record.timezone,
                "cron_expr": record.cron_expr,
                "enabled": record.enabled,
                "next_run_at": record.next_run_at,
                "last_run_at": record.last_run_at,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        }

    @router.post(
        "/v1/schedules/{schedule_id}:disable",
        response_model=SuccessResponse[ScheduleSummaryData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def disable_schedule(schedule_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            record = get_schedule_service().disable_schedule(schedule_id)
        except Exception as exc:  # noqa: BLE001
            return _route_error_response(command="schedules_disable", exc=cast(Exception, exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "schedules_disable",
            "data": {
                "schedule_id": record.schedule_id,
                "name": record.name,
                "app_id": record.app_id,
                "plan_ids": [str(item) for item in record.request_json.get("plan_ids", [])],
                "device_ref": record.device_ref,
                "timezone": record.timezone,
                "cron_expr": record.cron_expr,
                "enabled": record.enabled,
                "next_run_at": record.next_run_at,
                "last_run_at": record.last_run_at,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        }

    @router.delete(
        "/v1/schedules/{schedule_id}",
        response_model=SuccessResponse[ScheduleSummaryData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def delete_schedule(schedule_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            record = get_registry().get_schedule(schedule_id)
            get_schedule_service().delete_schedule(schedule_id)
        except Exception as exc:  # noqa: BLE001
            return _route_error_response(command="schedules_delete", exc=cast(Exception, exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "schedules_delete",
            "data": {
                "schedule_id": record.schedule_id,
                "name": record.name,
                "app_id": record.app_id,
                "plan_ids": [str(item) for item in record.request_json.get("plan_ids", [])],
                "device_ref": record.device_ref,
                "timezone": record.timezone,
                "cron_expr": record.cron_expr,
                "enabled": record.enabled,
                "next_run_at": record.next_run_at,
                "last_run_at": record.last_run_at,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        }

    @router.get(
        "/v1/schedules/{schedule_id}/runs",
        response_model=SuccessResponse[ScheduleRunListData],
        responses=_SCHEDULE_ERROR_RESPONSES,
    )
    def list_schedule_runs(
        schedule_id: str,
        response: Response,
        limit: int = Query(20, ge=1, le=200),
    ) -> dict[str, object] | JSONResponse:
        return _machine_route_response(response, get_query_service().list_schedule_runs(schedule_id=schedule_id, limit=limit))

    return router


def _machine_route_response(response: Response, command_response) -> dict[str, object] | JSONResponse:  # noqa: ANN001
    payload = cast(dict[str, object], command_response.payload)
    if payload.get("ok") is True:
        response.status_code = command_response.http_status
        return payload
    return JSONResponse(status_code=command_response.http_status, content=payload)


def _route_error_response(*, command: str, exc: Exception) -> JSONResponse:
    response = build_error_result(command=command, exc=exc)
    return JSONResponse(
        status_code=response.http_status,
        content=response.payload,
    )
