from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from munk.adapters.local_api.plan_route_dependencies import PlanRouteDependencies
from munk.adapters.local_api.plan_route_helpers import (
    PLAN_ERROR_RESPONSES,
    build_case_rewrite_preview_data,
    plan_error_response,
    success_payload,
    updated_plan_with_case_change,
)
from munk.adapters.local_api.response_models import CaseDeleteData, CaseRewritePreviewData, SuccessResponse
from munk.adapters.shared.payload_models import CaseDetailData, PlanDetailData
from munk.adapters.shared.plan_queries import build_case_detail_data, build_plan_detail_data

from .plan_models import (
    CaseRewritePreviewRequest,
    CaseUpdateRequest,
    CaseUpsertRequest,
    PlanCaseReorderRequest,
)


def register_plan_case_routes(router: APIRouter, dependencies: PlanRouteDependencies) -> None:
    @router.put(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}",
        response_model=SuccessResponse[CaseDetailData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def update_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        request: CaseUpdateRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            plan_store = dependencies.get_plan_store()
            plan = plan_store.load(app_id, plan_id)
        except FileNotFoundError:
            return plan_error_response(404, "plans_case_update", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_case_update", "plans_case_update_failed", str(exc))
        try:
            updated_plan, updated_case = updated_plan_with_case_change(plan, case_id=case_id, request=request)
            plan_store.replace(updated_plan)
        except LookupError as exc:
            return plan_error_response(404, "plans_case_update", "case_not_found", str(exc))
        except ValueError as exc:
            return plan_error_response(422, "plans_case_update", "case_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_case_update", "plans_case_update_failed", str(exc))
        return success_payload(
            response,
            command="plans_case_update",
            data=build_case_detail_data(updated_plan, updated_case).model_dump(mode="json"),
        )

    @router.post(
        "/v1/plans/{app_id}/{plan_id}/cases",
        response_model=SuccessResponse[CaseDetailData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def add_case(
        app_id: str,
        plan_id: str,
        request: CaseUpsertRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = dependencies.get_mutation_service().add_case(app_id, plan_id, request.to_test_case())
        except FileNotFoundError:
            return plan_error_response(404, "plans_case_add", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except ValueError as exc:
            return plan_error_response(422, "plans_case_add", "case_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_case_add", "plans_case_add_failed", str(exc))
        return success_payload(
            response,
            command="plans_case_add",
            data=build_case_detail_data(result.plan, result.case).model_dump(mode="json"),
        )

    @router.put(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}/replace",
        response_model=SuccessResponse[CaseDetailData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def replace_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        request: CaseUpsertRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = dependencies.get_mutation_service().replace_case(app_id, plan_id, case_id, request.to_test_case())
        except FileNotFoundError:
            return plan_error_response(404, "plans_case_replace", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except LookupError as exc:
            return plan_error_response(404, "plans_case_replace", "case_not_found", str(exc))
        except ValueError as exc:
            return plan_error_response(422, "plans_case_replace", "case_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_case_replace", "plans_case_replace_failed", str(exc))
        return success_payload(
            response,
            command="plans_case_replace",
            data=build_case_detail_data(result.plan, result.case).model_dump(mode="json"),
        )

    @router.post(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}/rewrite-preview",
        response_model=SuccessResponse[CaseRewritePreviewData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def rewrite_case_preview(
        app_id: str,
        plan_id: str,
        case_id: str,
        request: CaseRewritePreviewRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            rewritten_case = dependencies.get_rewrite_service().rewrite_case_preview(
                app_id=app_id,
                plan_id=plan_id,
                case_id=case_id,
                prompt=request.prompt,
            )
            preview = build_case_rewrite_preview_data(rewritten_case, source_prompt=request.prompt)
        except FileNotFoundError:
            return plan_error_response(
                404,
                "plans_case_rewrite_preview",
                "plan_not_found",
                f"plan '{app_id}/{plan_id}' not found",
            )
        except LookupError as exc:
            return plan_error_response(404, "plans_case_rewrite_preview", "case_not_found", str(exc))
        except ValueError as exc:
            return plan_error_response(422, "plans_case_rewrite_preview", "case_rewrite_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_case_rewrite_preview", "plans_case_rewrite_preview_failed", str(exc))
        return success_payload(
            response,
            command="plans_case_rewrite_preview",
            data=preview.model_dump(mode="json"),
        )

    @router.delete(
        "/v1/plans/{app_id}/{plan_id}/cases/{case_id}",
        response_model=SuccessResponse[CaseDeleteData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def delete_case(
        app_id: str,
        plan_id: str,
        case_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            result = dependencies.get_mutation_service().delete_case(app_id, plan_id, case_id)
        except FileNotFoundError:
            return plan_error_response(404, "plans_case_delete", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except LookupError as exc:
            return plan_error_response(404, "plans_case_delete", "case_not_found", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_case_delete", "plans_case_delete_failed", str(exc))
        return success_payload(
            response,
            command="plans_case_delete",
            data=CaseDeleteData(
                app_id=app_id,
                plan_id=plan_id,
                case_id=result.case_id,
                case_count=len(result.plan.cases),
            ).model_dump(mode="json"),
        )

    @router.post(
        "/v1/plans/{app_id}/{plan_id}/cases:reorder",
        response_model=SuccessResponse[PlanDetailData],
        responses=PLAN_ERROR_RESPONSES,
    )
    def reorder_cases(
        app_id: str,
        plan_id: str,
        request: PlanCaseReorderRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        try:
            updated_plan = dependencies.get_mutation_service().reorder_cases(app_id, plan_id, request.case_ids)
        except FileNotFoundError:
            return plan_error_response(404, "plans_cases_reorder", "plan_not_found", f"plan '{app_id}/{plan_id}' not found")
        except ValueError as exc:
            return plan_error_response(422, "plans_cases_reorder", "case_reorder_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return plan_error_response(500, "plans_cases_reorder", "plans_cases_reorder_failed", str(exc))
        return success_payload(
            response,
            command="plans_cases_reorder",
            data=build_plan_detail_data(updated_plan).model_dump(mode="json"),
        )
