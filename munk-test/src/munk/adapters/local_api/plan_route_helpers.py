from __future__ import annotations

from typing import Any, cast

from fastapi import Response
from fastapi.responses import JSONResponse

from munk.adapters.local_api.plan_models import CaseBudgetRequest, CaseStartStateRequest, CaseUpdateRequest, TestCasePayload
from munk.adapters.local_api.response_models import CaseRewritePreviewData, ErrorResponse
from munk.adapters.local_api.route_helpers import error_response
from munk.planning.models import RequirementPlan
from munk.testing import TestCase

PLAN_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def success_payload(
    response: Response,
    *,
    command: str,
    data: dict[str, Any],
) -> dict[str, object]:
    response.status_code = 200
    return {
        "ok": True,
        "command": command,
        "data": data,
    }


def plan_error_response(status_code: int, command: str, code: str, message: str) -> JSONResponse:
    return error_response(
        status_code=status_code,
        command=command,
        code=code,
        message=message,
    )


def build_case_rewrite_preview_data(case: TestCase, *, source_prompt: str) -> CaseRewritePreviewData:
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
            ai_guidance=case.ai_guidance,
            source_metadata=dict(case.source_metadata),
        ),
        source_prompt=source_prompt,
    )


def updated_plan_with_case_change(
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
