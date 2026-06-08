from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.shared.payload_models import CaseDetailData, CaseSearchData, PlanDetailData, PlanListData
from munk.adapters.shared.plan_queries import (
    build_case_detail_data,
    build_plan_detail_data,
    get_case_payload,
    get_plan_payload,
    list_plans_payload,
    search_cases_payload,
)
from munk.app_assets.storage import AppRegistry
from munk.planning.case_rewrite_service import CaseRewriteService
from munk.planning.import_service import PlanImportService
from munk.planning.index_store import PlanCaseIndexStore
from munk.planning.models import RequirementPlan
from munk.planning.plan_mutation_service import PlanMutationService
from munk.planning.storage import PlanStore
from munk.testing import TestCase

from .plan_models import (
    CaseBudgetRequest,
    CaseRewritePreviewRequest,
    CaseStartStateRequest,
    CaseUpdateRequest,
    CaseUpsertRequest,
    PlanCaseReorderRequest,
    PlanImportRequest,
    TestCasePayload,
)
from .response_models import (
    CaseDeleteData,
    CaseRewritePreviewData,
    ErrorResponse,
    PlanImportData,
    SuccessResponse,
)

_PLAN_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_plan_router(
    *,
    plan_store_factory: Callable[[], PlanStore] | None = None,
    index_store_factory: Callable[[], PlanCaseIndexStore] | None = None,
    mutation_service_factory: Callable[[], PlanMutationService] | None = None,
    rewrite_service_factory: Callable[[], CaseRewriteService] | None = None,
    import_service_factory: Callable[[], PlanImportService] | None = None,
) -> APIRouter:
    router = APIRouter()

    def get_plan_store() -> PlanStore:
        if plan_store_factory is not None:
            return plan_store_factory()
        return PlanStore()

    def get_index_store() -> PlanCaseIndexStore:
        if index_store_factory is not None:
            return index_store_factory()
        return PlanCaseIndexStore()

    def get_mutation_service() -> PlanMutationService:
        if mutation_service_factory is not None:
            return mutation_service_factory()
        return PlanMutationService(plan_store=get_plan_store())

    def get_rewrite_service() -> CaseRewriteService:
        if rewrite_service_factory is not None:
            return rewrite_service_factory()
        plan_store = get_plan_store()
        return CaseRewriteService(
            workspace_root=Path.cwd(),
            plan_store=plan_store,
            app_registry=AppRegistry(plan_store.root_dir),
        )

    def get_import_service() -> PlanImportService:
        if import_service_factory is not None:
            return import_service_factory()
        plan_store = get_plan_store()
        return PlanImportService(
            plan_store=plan_store,
            app_registry=AppRegistry(plan_store.root_dir),
        )

    @router.get(
        "/v1/plans",
        response_model=SuccessResponse[PlanListData],
        responses=_PLAN_ERROR_RESPONSES,
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
                index_store=get_index_store(),
                app_id=app_id,
                source=source,
                case_count_mode=case_count_mode,
                limit=limit,
                offset=offset,
                include_latest_run=include_latest_run,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_list", "plans_list_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_list",
            "data": data.model_dump(mode="json"),
        }

    @router.post(
        "/v1/plans:import",
        response_model=SuccessResponse[PlanImportData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def import_plan(
        request: PlanImportRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = get_import_service().import_plan(
                app_id=request.app_id,
                name=request.name,
                raw_plan=request.raw_plan,
                file_name=request.file_name,
            )
        except FileNotFoundError as exc:
            return _error_response(404, "plans_import", "app_not_found", str(exc))
        except ValueError as exc:
            return _error_response(422, "plans_import", "plan_import_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_import", "plans_import_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_import",
            "data": PlanImportData(
                app_id=result.plan.app_id,
                plan_id=result.plan.plan_id,
                plan_name=result.plan.name,
                source=result.plan.source,
                version=result.plan.version,
                case_count=len(result.plan.cases),
                plan_path=result.plan_path,
            ).model_dump(mode="json"),
        }

    @router.get(
        "/v1/plans/cases",
        response_model=SuccessResponse[CaseSearchData],
        responses=_PLAN_ERROR_RESPONSES,
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
                index_store=get_index_store(),
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
            return _error_response(500, "plans_cases", "plans_cases_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_cases",
            "data": data.model_dump(mode="json"),
        }

    @router.get(
        "/v1/plans/{app_id}/{plan_id}",
        response_model=SuccessResponse[PlanDetailData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def get_plan(app_id: str, plan_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            data = get_plan_payload(plan_store=get_plan_store(), app_id=app_id, plan_id=plan_id)
        except FileNotFoundError:
            return _error_response(404, "plans_get", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_get", "plans_get_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_get",
            "data": data.model_dump(mode="json"),
        }

    @router.get(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}",
        response_model=SuccessResponse[CaseDetailData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def get_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            data = get_case_payload(plan_store=get_plan_store(), app_id=app_id, plan_id=plan_id, case_id=case_id)
        except FileNotFoundError:
            return _error_response(404, "plans_case_get", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except LookupError as exc:
            return _error_response(404, "plans_case_get", "case_not_found", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_case_get", "plans_case_get_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_case_get",
            "data": data.model_dump(mode="json"),
        }

    @router.put(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}",
        response_model=SuccessResponse[CaseDetailData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def update_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        request: CaseUpdateRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            plan = get_plan_store().load(app_id, plan_id)
        except FileNotFoundError:
            return _error_response(404, "plans_case_update", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_case_update", "plans_case_update_failed", str(exc))
        try:
            updated_plan, updated_case = _updated_plan_with_case_change(plan, case_id=case_id, request=request)
            get_plan_store().save(updated_plan)
        except LookupError as exc:
            return _error_response(404, "plans_case_update", "case_not_found", str(exc))
        except ValueError as exc:
            return _error_response(422, "plans_case_update", "case_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_case_update", "plans_case_update_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_case_update",
            "data": build_case_detail_data(updated_plan, updated_case).model_dump(mode="json"),
        }

    @router.post(
        "/v1/plans/{app_id}/{plan_id}/cases",
        response_model=SuccessResponse[CaseDetailData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def add_case(
        app_id: str,
        plan_id: str,
        request: CaseUpsertRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = get_mutation_service().add_case(app_id, plan_id, request.to_test_case())
        except FileNotFoundError:
            return _error_response(404, "plans_case_add", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except ValueError as exc:
            return _error_response(422, "plans_case_add", "case_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_case_add", "plans_case_add_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_case_add",
            "data": build_case_detail_data(result.plan, result.case).model_dump(mode="json"),
        }

    @router.put(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}/replace",
        response_model=SuccessResponse[CaseDetailData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def replace_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        request: CaseUpsertRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = get_mutation_service().replace_case(app_id, plan_id, case_id, request.to_test_case())
        except FileNotFoundError:
            return _error_response(404, "plans_case_replace", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except LookupError as exc:
            return _error_response(404, "plans_case_replace", "case_not_found", str(exc))
        except ValueError as exc:
            return _error_response(422, "plans_case_replace", "case_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_case_replace", "plans_case_replace_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_case_replace",
            "data": build_case_detail_data(result.plan, result.case).model_dump(mode="json"),
        }

    @router.post(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}/rewrite-preview",
        response_model=SuccessResponse[CaseRewritePreviewData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def rewrite_case_preview(
        app_id: str,
        plan_id: str,
        case_id: str,
        request: CaseRewritePreviewRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            rewritten_case = get_rewrite_service().rewrite_case_preview(
                app_id=app_id,
                plan_id=plan_id,
                case_id=case_id,
                prompt=request.prompt,
            )
            preview = _case_rewrite_preview_data(rewritten_case, source_prompt=request.prompt)
        except FileNotFoundError:
            return _error_response(404, "plans_case_rewrite_preview", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except LookupError as exc:
            return _error_response(404, "plans_case_rewrite_preview", "case_not_found", str(exc))
        except ValueError as exc:
            return _error_response(422, "plans_case_rewrite_preview", "case_rewrite_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_case_rewrite_preview", "plans_case_rewrite_preview_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_case_rewrite_preview",
            "data": preview.model_dump(mode="json"),
        }

    @router.delete(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}",
        response_model=SuccessResponse[CaseDeleteData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def delete_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = get_mutation_service().delete_case(app_id, plan_id, case_id)
        except FileNotFoundError:
            return _error_response(404, "plans_case_delete", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except LookupError as exc:
            return _error_response(404, "plans_case_delete", "case_not_found", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_case_delete", "plans_case_delete_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_case_delete",
            "data": CaseDeleteData(
                app_id=app_id,
                plan_id=plan_id,
                case_id=result.case_id,
                case_count=len(result.plan.cases),
            ).model_dump(mode="json"),
        }

    @router.post(
        "/v1/plans/{app_id}/{plan_id}/cases:reorder",
        response_model=SuccessResponse[PlanDetailData],
        responses=_PLAN_ERROR_RESPONSES,
    )
    def reorder_cases(
        app_id: str,
        plan_id: str,
        request: PlanCaseReorderRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            updated_plan = get_mutation_service().reorder_cases(app_id, plan_id, request.case_ids)
        except FileNotFoundError:
            return _error_response(404, "plans_cases_reorder", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except ValueError as exc:
            return _error_response(422, "plans_cases_reorder", "case_reorder_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "plans_cases_reorder", "plans_cases_reorder_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "plans_cases_reorder",
            "data": build_plan_detail_data(updated_plan).model_dump(mode="json"),
        }

    return router


def _case_rewrite_preview_data(case: TestCase, *, source_prompt: str) -> CaseRewritePreviewData:
    budget = case.budget
    return CaseRewritePreviewData(
        case=TestCasePayload(
            case_id=case.case_id,
            title=case.title,
            intent=case.intent,
            preconditions=list(case.preconditions),
            expected=list(case.expected),
            procedure=list(case.procedure),
            post_action=list(case.post_action),
            is_core_case=case.is_core_case,
            runner_goal=case.runner_goal,
            budget=None if budget is None else CaseBudgetRequest(
                max_steps=budget.max_steps,
                max_seconds=budget.max_seconds,
            ),
            start_state=CaseStartStateRequest(
                mode=case.start_state.mode,
                page_id=case.start_state.page_id,
            ),
            source_metadata=dict(case.source_metadata),
        ),
        source_prompt=source_prompt,
    )
def _updated_plan_with_case_change(
    plan: RequirementPlan,
    *,
    case_id: str,
    request: CaseUpdateRequest,
) -> tuple[RequirementPlan, TestCase]:
    case_index = next((index for index, item in enumerate(plan.cases) if item.case_id == case_id), None)
    if case_index is None:
        raise LookupError(f"case '{case_id}' not found in plan '{plan.app_id}/{plan.plan_id}'")
    current_case = plan.cases[case_index]
    field_name, field_value = request.require_single_field()
    updated_case = _updated_case(current_case, field_name=field_name, field_value=field_value)
    updated_cases = list(plan.cases)
    updated_cases[case_index] = updated_case
    return plan.model_copy(update={"cases": updated_cases}), updated_case


def _updated_case(
    case: TestCase,
    *,
    field_name: str,
    field_value: str | list[str] | None,
) -> TestCase:
    if field_name == "start_mode":
        return case.model_copy(update={"start_state": case.start_state.model_copy(update={"mode": field_value})})
    if field_name == "start_page_id":
        return case.model_copy(update={"start_state": case.start_state.model_copy(update={"page_id": field_value})})
    return case.model_copy(update={field_name: field_value})
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
