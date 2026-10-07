from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from munk.token_usage import TokenUsage


class PlanningTimelineEventPayload(BaseModel):
    app_id: str | None = None
    plan_id: str | None = None
    case_count: int | None = None
    plan_path: str | None = None
    snapshot_path: str | None = None
    planning_usage: TokenUsage | None = None
    has_requirement_doc: bool | None = None
    has_technical_doc: bool | None = None
    has_review_contract: bool | None = None
    assets_root: str | None = None
    target_case_count: int | None = None
    completed_case_count: int | None = None
    case_index: int | None = None
    case_id: str | None = None
    case_title: str | None = None
    duplicate_titles: list[str] | None = None
    uncovered_indices: list[int] | None = None


class PlanOperationProgressPayload(BaseModel):
    plan_event_type: str
    stage: str | None = None
    lifecycle_state: str | None = None
    agent_role: str | None = None
    event_timestamp: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    plan_name: str | None = None
    target_case_count: int | None = None
    completed_case_count: int | None = None
    case_index: int | None = None
    case_id: str | None = None
    case_title: str | None = None
    case_count: int | None = None
    plan_path: str | None = None
    snapshot_path: str | None = None


_PLAN_STAGE_BY_EVENT_TYPE = {
    "plan_context_loaded": "context_loaded",
    "plan_agent_ready": "agent_ready",
    "plan_skeleton_generation_started": "skeleton_generation_started",
    "plan_skeleton_generated": "skeleton_generated",
    "plan_case_generation_started": "case_generation_started",
    "plan_case_generated": "case_generated",
    "plan_finalize_started": "finalize_started",
    "plan_finalize_completed": "finalize_completed",
    "plan_saved": "saved",
}


def build_plan_operation_progress_payload(
    event_type: str,
    data: object,
    *,
    lifecycle_state: str | None = None,
    agent_role: str | None = None,
    event_timestamp: str | None = None,
) -> dict[str, Any]:
    payload_dict = data if isinstance(data, dict) else {}
    payload = PlanOperationProgressPayload(
        plan_event_type=event_type,
        stage=_PLAN_STAGE_BY_EVENT_TYPE.get(event_type),
        lifecycle_state=lifecycle_state,
        agent_role=agent_role,
        event_timestamp=event_timestamp,
        app_id=_str_or_none(payload_dict.get("app_id")),
        plan_id=_str_or_none(payload_dict.get("plan_id")),
        plan_name=_str_or_none(payload_dict.get("plan_name")),
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
