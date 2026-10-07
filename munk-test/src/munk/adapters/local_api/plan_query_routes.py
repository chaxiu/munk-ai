from __future__ import annotations

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.local_api.plan_route_dependencies import PlanRouteDependencies
from munk.adapters.local_api.plan_route_helpers import PLAN_ERROR_RESPONSES, plan_error_response, success_payload
from munk.adapters.local_api.response_models import PlanImportData, SuccessResponse
from munk.adapters.shared.payload_models import CaseDetailData, CaseSearchData, PlanDetailData, PlanListData
from munk.adapters.shared.plan_queries import get_case_payload, get_plan_payload, list_plans_payload, search_cases_payload

from .plan_models import PlanImportRequest


def register_plan_query_routes(router: APIRouter, dependencies: PlanRouteDependencies) -> None:
    @router.get(
        "/v1/plans",
        response_model=SuccessResponse[PlanListData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def list_plans(
        response: Response,
        app_id: str | None = Query(None),
        source: str | None = Query(None),
        case_count_mode: str | None = Query(None),
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
        include_latest_run: bool = Query(False),
    ) -> dict[str, object] | JSONResponse:
        try:
            data = list_plans_payload(
                index_store=dependencies.get_index_store(),
                app_id=app_id,
                source=source,
                case_count_mode=case_count_mode,
                limit=limit,
                offset=offset,
                include_latest_run=include_latest_run,
            )
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_list", "plans_list_failed", str(exc))
        return success_payload(
            response,
            command="plans_list",
            data=data.model_dump(mode="json"),
        )

    @router.post(
        "/v1/plans:import",
        response_model=SuccessResponse[PlanImportData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def import_plan(
        request: PlanImportRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = dependencies.get_import_service().import_plan(
                app_id=request.app_id,
                name=request.name,
                raw_plan=request.raw_plan,
                file_name=request.file_name,
            )
        except FileNotFoundError as exc:
            return plan_error_response(404, "plans_import", "app_not_found", str(exc))
        except ValueError as exc:
            return plan_error_response(422, "plans_import", "plan_import_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_import", "plans_import_failed", str(exc))
        return success_payload(
            response,
            command="plans_import",
            data=PlanImportData(
                app_id=result.plan.app_id,
                plan_id=result.plan.plan_id,
                plan_name=result.plan.name,
                source=result.plan.source,
                version=result.plan.version,
                case_count=len(result.plan.cases),
                plan_path=result.plan_path,
            ).model_dump(mode="json"),
        )

    @router.get(
        "/v1/plans/cases",
        response_model=SuccessResponse[CaseSearchData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def search_cases(
        response: Response,
        app_id: str | None = Query(None),
        plan_id: str | None = Query(None),
        case_id: str | None = Query(None),
        query: str | None = Query(None),
        is_core_case: bool | None = Query(None),
        start_mode: str | None = Query(None),
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> dict[str, object] | JSONResponse:
        try:
            data = search_cases_payload(
                index_store=dependencies.get_index_store(),
                app_id=app_id,
                plan_id=plan_id,
                case_id=case_id,
                query=query,
                is_core_case=is_core_case,
                start_mode=start_mode,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_cases", "plans_cases_failed", str(exc))
        return success_payload(
            response,
            command="plans_cases",
            data=data.model_dump(mode="json"),
        )

    @router.get(
        "/v1/plans/{app_id}/{plan_id}",
        response_model=SuccessResponse[PlanDetailData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def get_plan(app_id: str, plan_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = get_plan_payload(
                plan_store=dependencies.get_plan_store(),
                app_id=app_id,
                plan_id=plan_id,
            )
        except FileNotFoundError:
            return plan_error_response(404, "plans_get", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_get", "plans_get_failed", str(exc))
        return success_payload(
            response,
            command="plans_get",
            data=data.model_dump(mode="json"),
        )

    @router.get(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}",
        response_model=SuccessResponse[CaseDetailData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def get_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            data = get_case_payload(
                plan_store=dependencies.get_plan_store(),
                app_id=app_id,
                plan_id=plan_id,
                case_id=case_id,
            )
        except FileNotFoundError:
            return plan_error_response(404, "plans_case_get", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except LookupError as exc:
            return plan_error_response(404, "plans_case_get", "case_not_found", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_case_get", "plans_case_get_failed", str(exc))
        return success_payload(
            response,
            command="plans_case_get",
            data=data.model_dump(mode="json"),
        )
