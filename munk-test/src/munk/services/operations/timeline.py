from __future__ import annotations

from typing import Any

from munk.agent_runtime import AgentRuntimeEvent
from munk.agent_runtime.events import build_agent_runtime_host_data_payload
from munk.services.events import RunEvent, RunEventType
from munk.services.events import run_event_summary, serialize_run_event_payload
from munk.services.operations.event_payloads import build_operation_timeline_payload


def build_timeline_payload_from_agent_runtime_event(
    event: AgentRuntimeEvent,
    *,
    operation_id: str,
) -> dict[str, Any]:
    return build_operation_timeline_payload(
        agent_role=event.agent_role,
        operation_id=operation_id,
        timeline_scope=event.timeline_scope or default_scope_for_agent_role(event.agent_role),
        timeline_phase=event.timeline_phase or event.lifecycle_state,
        summary=event.summary,
        attempt_index=event.attempt_index,
        parent_operation_id=event.parent_operation_id,
        child_operation_id=event.child_operation_id,
        app_id=event.app_id,
        plan_id=event.plan_id,
        case_id=event.case_id,
        data=build_agent_runtime_host_data_payload(event),
    )


def build_timeline_payload_from_run_event(
    event: RunEvent,
    *,
    operation_id: str,
) -> dict[str, Any]:
    event_data = serialize_run_event_payload(event)
    return build_operation_timeline_payload(
        agent_role="runner",
        operation_id=operation_id,
        timeline_scope="parent_run",
        timeline_phase=runner_timeline_phase(event.type),
        summary=summary_from_event(event),
        attempt_index=attempt_index_from_payload(event_data),
        parent_operation_id=str_or_none(event_data.get("parent_operation_id")),
        child_operation_id=str_or_none(event_data.get("child_operation_id")),
        app_id=str_or_none(event_data.get("app_id")),
        plan_id=str_or_none(event_data.get("plan_id")),
        case_id=str_or_none(event_data.get("case_id")),
        data=event_data,
    )


def base_timeline_payload(
    *,
    agent_role: str,
    operation_id: str,
    timeline_scope: str,
    timeline_phase: str,
    summary: str | None,
    attempt_index: int | None,
    parent_operation_id: str | None,
    child_operation_id: str | None,
    app_id: str | None,
    plan_id: str | None,
    case_id: str | None,
    data: dict[str, Any] | None,
) -> dict[str, Any]:
    return build_operation_timeline_payload(
        agent_role=agent_role,
        operation_id=operation_id,
        timeline_scope=timeline_scope,
        timeline_phase=timeline_phase,
        summary=summary,
        attempt_index=attempt_index,
        parent_operation_id=parent_operation_id,
        child_operation_id=child_operation_id,
        app_id=app_id,
        plan_id=plan_id,
        case_id=case_id,
        data=data,
    )


def summary_from_event(event: RunEvent) -> str | None:
    if event.message:
        return event.message
    return run_event_summary(event)


def attempt_index_from_payload(payload: dict[str, Any]) -> int | None:
    raw = payload.get("attempt_index")
    if isinstance(raw, int):
        return raw
    return None


def str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def default_scope_for_agent_role(agent_role: str) -> str:
    if agent_role in {"optimize", "knowledge"}:
        return "child_operation"
    return "parent_run"


def runner_timeline_phase(event_type: RunEventType) -> str:
    return {
        RunEventType.RUN_STARTED: "started",
        RunEventType.STEP_STARTED: "step_started",
        RunEventType.PERCEPTION_COMPLETED: "evidence_ready",
        RunEventType.RUNNER_TOOL_CALLED: "tool_called",
        RunEventType.RUNNER_CONTRACT_MISS: "contract_miss",
        RunEventType.RUNNER_DECISION_COMPLETED: "decision_ready",
        RunEventType.ACTION_PROPOSED: "action_proposed",
        RunEventType.ACTION_EXECUTION_STARTED: "action_started",
        RunEventType.ACTION_EXECUTED: "action_completed",
        RunEventType.ACTION_EXECUTION_FAILED: "action_failed",
        RunEventType.RUN_STOPPED: "completed",
        RunEventType.RUN_FAILED: "failed",
        RunEventType.LOG: "log",
    }[event_type]
