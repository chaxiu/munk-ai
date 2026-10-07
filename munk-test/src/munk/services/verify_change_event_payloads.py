from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from munk.token_usage import TokenUsage


class ChangeVerificationReviewContractLoadedPayload(BaseModel):
    app_id: str
    review_hint_enabled: bool
    review_required_case_count: int


class ChangeVerificationCasesReadyPayload(BaseModel):
    manual_case_count: int
    review_required_case_count: int
    planner_case_count: int
    review_hint_enabled: bool


class ChangeVerificationPlanSavedPayload(BaseModel):
    app_id: str
    plan_id: str
    case_count: int
    plan_path: str
    snapshot_path: str
    planning_usage: TokenUsage | None = None


class VerifyChangeOperationProgressPayload(BaseModel):
    verify_change_event_type: str
    stage: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    review_hint_enabled: bool | None = None
    review_required_case_count: int | None = None
    manual_case_count: int | None = None
    planner_case_count: int | None = None
    target_case_count: int | None = None
    completed_case_count: int | None = None
    case_index: int | None = None
    case_id: str | None = None
    case_title: str | None = None
    case_count: int | None = None
    plan_path: str | None = None
    snapshot_path: str | None = None


_VERIFY_CHANGE_STAGE_BY_EVENT_TYPE = {
    "change_verification_started": "change_verification_started",
    "change_verification_review_contract_loaded": "review_contract_loaded",
    "change_plan_context_loaded": "planner_context_loaded",
    "plan_skeleton_generation_started": "planner_skeleton_generation_started",
    "plan_skeleton_generated": "planner_skeleton_generated",
    "plan_case_generation_started": "planner_case_generation_started",
    "plan_case_generated": "planner_case_generated",
    "plan_finalize_started": "planner_finalize_started",
    "plan_finalize_completed": "planner_finalize_completed",
    "change_plan_saved": "planner_plan_saved",
    "change_verification_cases_ready": "runtime_cases_ready",
    "change_verification_plan_saved": "runtime_plan_saved",
}


def build_change_verification_review_contract_loaded_payload(
    *,
    app_id: str,
    review_hint_enabled: bool,
    review_required_case_count: int,
) -> dict[str, Any]:
    payload = ChangeVerificationReviewContractLoadedPayload(
        app_id=app_id,
        review_hint_enabled=review_hint_enabled,
        review_required_case_count=review_required_case_count,
    )
    return payload.model_dump(mode="json")


def build_change_verification_cases_ready_payload(
    *,
    manual_case_count: int,
    review_required_case_count: int,
    planner_case_count: int,
    review_hint_enabled: bool,
) -> dict[str, Any]:
    payload = ChangeVerificationCasesReadyPayload(
        manual_case_count=manual_case_count,
        review_required_case_count=review_required_case_count,
        planner_case_count=planner_case_count,
        review_hint_enabled=review_hint_enabled,
    )
    return payload.model_dump(mode="json")


def build_change_verification_plan_saved_payload(
    *,
    app_id: str,
    plan_id: str,
    case_count: int,
    plan_path: str,
    snapshot_path: str,
    planning_usage: TokenUsage | None,
) -> dict[str, Any]:
    payload = ChangeVerificationPlanSavedPayload(
        app_id=app_id,
        plan_id=plan_id,
        case_count=case_count,
        plan_path=plan_path,
        snapshot_path=snapshot_path,
        planning_usage=planning_usage,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_verify_change_operation_progress_payload(event_type: str, data: object) -> dict[str, Any]:
    payload_dict = data if isinstance(data, dict) else {}
    payload = VerifyChangeOperationProgressPayload(
        verify_change_event_type=event_type,
        stage=_VERIFY_CHANGE_STAGE_BY_EVENT_TYPE.get(event_type),
        app_id=_str_or_none(payload_dict.get("app_id")),
        plan_id=_str_or_none(payload_dict.get("plan_id")),
        review_hint_enabled=_bool_or_none(payload_dict.get("review_hint_enabled")),
        review_required_case_count=_int_or_none(payload_dict.get("review_required_case_count")),
        manual_case_count=_int_or_none(payload_dict.get("manual_case_count")),
        planner_case_count=_int_or_none(payload_dict.get("planner_case_count")),
        target_case_count=_int_or_none(payload_dict.get("target_case_count")),
        completed_case_count=_int_or_none(payload_dict.get("completed_case_count")),
        case_index=_int_or_none(payload_dict.get("case_index")),
        case_id=_str_or_none(payload_dict.get("case_id")),
        case_title=_str_or_none(payload_dict.get("case_title")),
        case_count=_int_or_none(payload_dict.get("case_count")),
        plan_path=_str_or_none(payload_dict.get("plan_path")),
        snapshot_path=_str_or_none(payload_dict.get("snapshot_path")),
    )
    return payload.model_dump(mode="json", exclude_none=True)


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None
