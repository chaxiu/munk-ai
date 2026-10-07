from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class OperationTimelinePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_role: str
    timeline_scope: str
    timeline_phase: str
    operation_id: str
    summary: str | None = None
    attempt_index: int | None = None
    parent_operation_id: str | None = None
    child_operation_id: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    lifecycle_state: str | None = None
    event_timestamp: str | None = None


class OperationTimelineProgressPayload(BaseModel):
    last_event_type: str
    agent_role: str | None = None
    timeline_scope: str | None = None
    timeline_phase: str | None = None
    attempt_index: int | None = None
    parent_operation_id: str | None = None
    child_operation_id: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    summary: str | None = None
    lifecycle_state: str | None = None
    event_timestamp: str | None = None


def build_operation_timeline_payload(
    *,
    agent_role: str,
    timeline_scope: str,
    timeline_phase: str,
    operation_id: str,
    summary: str | None = None,
    attempt_index: int | None = None,
    parent_operation_id: str | None = None,
    child_operation_id: str | None = None,
    app_id: str | None = None,
    plan_id: str | None = None,
    case_id: str | None = None,
    lifecycle_state: str | None = None,
    event_timestamp: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload_data = dict(data or {})
    payload_data["agent_role"] = agent_role
    payload_data["timeline_scope"] = timeline_scope
    payload_data["timeline_phase"] = timeline_phase
    payload_data["operation_id"] = operation_id
    if summary is not None:
        payload_data["summary"] = summary
    if attempt_index is not None:
        payload_data["attempt_index"] = attempt_index
    if parent_operation_id is not None:
        payload_data["parent_operation_id"] = parent_operation_id
    if child_operation_id is not None:
        payload_data["child_operation_id"] = child_operation_id
    if app_id is not None:
        payload_data["app_id"] = app_id
    if plan_id is not None:
        payload_data["plan_id"] = plan_id
    if case_id is not None:
        payload_data["case_id"] = case_id
    if lifecycle_state is not None:
        payload_data["lifecycle_state"] = lifecycle_state
    if event_timestamp is not None:
        payload_data["event_timestamp"] = event_timestamp
    payload = OperationTimelinePayload(**payload_data)
    return payload.model_dump(mode="json", exclude_none=True)


def build_operation_timeline_progress_payload(*, event_type: str, payload: object) -> dict[str, Any]:
    payload_dict = payload if isinstance(payload, dict) else {}
    progress = OperationTimelineProgressPayload(
        last_event_type=event_type,
        agent_role=_str_or_none(payload_dict.get("agent_role")),
        timeline_scope=_str_or_none(payload_dict.get("timeline_scope")),
        timeline_phase=_str_or_none(payload_dict.get("timeline_phase")),
        attempt_index=_int_or_none(payload_dict.get("attempt_index")),
        parent_operation_id=_str_or_none(payload_dict.get("parent_operation_id")),
        child_operation_id=_str_or_none(payload_dict.get("child_operation_id")),
        app_id=_str_or_none(payload_dict.get("app_id")),
        plan_id=_str_or_none(payload_dict.get("plan_id")),
        case_id=_str_or_none(payload_dict.get("case_id")),
        summary=_str_or_none(payload_dict.get("summary")),
        lifecycle_state=_str_or_none(payload_dict.get("lifecycle_state")),
        event_timestamp=_str_or_none(payload_dict.get("event_timestamp")),
    )
    return progress.model_dump(mode="json", exclude_none=True)


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None
