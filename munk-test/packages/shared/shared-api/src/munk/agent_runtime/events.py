from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, Field

from .lifecycle import AgentLifecycleState


def empty_object_map() -> dict[str, object]:
    return {}


class AgentRuntimeEvent(BaseModel):
    event_type: str
    lifecycle_state: AgentLifecycleState
    timestamp: str
    agent_role: str
    operation_id: str | None = None
    timeline_scope: str | None = None
    timeline_phase: str | None = None
    attempt_index: int | None = None
    parent_operation_id: str | None = None
    child_operation_id: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    summary: str | None = None
    message: str | None = None
    data: dict[str, object] = Field(default_factory=empty_object_map)


class AgentRuntimeHostContext(BaseModel):
    lifecycle_state: AgentLifecycleState
    agent_role: str
    event_timestamp: str


class AgentEventSink(Protocol):
    def emit(self, event: AgentRuntimeEvent) -> None: ...


@dataclass(frozen=True)
class AgentRuntimeEventEmitter:
    agent_role: str
    operation_id: str | None = None
    event_sink: AgentEventSink | None = None
    timeline_scope: str | None = None
    attempt_index: int | None = None
    parent_operation_id: str | None = None
    child_operation_id: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None

    def emit_started(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_started",
        timeline_phase: str | None = "started",
        summary: str | None = None,
        child_operation_id: str | None = None,
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="started",
            message=message,
            data=data,
            timeline_phase=timeline_phase,
            summary=summary,
            child_operation_id=child_operation_id,
        )

    def emit_running(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_running",
        timeline_phase: str | None = None,
        summary: str | None = None,
        child_operation_id: str | None = None,
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="running",
            message=message,
            data=data,
            timeline_phase=timeline_phase,
            summary=summary,
            child_operation_id=child_operation_id,
        )

    def emit_ended(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_ended",
        timeline_phase: str | None = "completed",
        summary: str | None = None,
        child_operation_id: str | None = None,
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="ended",
            message=message,
            data=data,
            timeline_phase=timeline_phase,
            summary=summary,
            child_operation_id=child_operation_id,
        )

    def emit_failed(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_failed",
        timeline_phase: str | None = "failed",
        summary: str | None = None,
        child_operation_id: str | None = None,
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="failed",
            message=message,
            data=data,
            timeline_phase=timeline_phase,
            summary=summary,
            child_operation_id=child_operation_id,
        )

    def emit_canceled(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_canceled",
        timeline_phase: str | None = "canceled",
        summary: str | None = None,
        child_operation_id: str | None = None,
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="canceled",
            message=message,
            data=data,
            timeline_phase=timeline_phase,
            summary=summary,
            child_operation_id=child_operation_id,
        )

    def emit_progress(
        self,
        *,
        event_type: str,
        message: str | None = None,
        data: dict[str, object] | None = None,
        timeline_phase: str | None = None,
        summary: str | None = None,
        child_operation_id: str | None = None,
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="running",
            message=message,
            data=data,
            timeline_phase=timeline_phase,
            summary=summary,
            child_operation_id=child_operation_id,
        )

    def _emit(
        self,
        *,
        event_type: str,
        lifecycle_state: AgentLifecycleState,
        message: str | None,
        data: dict[str, object] | None,
        timeline_phase: str | None,
        summary: str | None,
        child_operation_id: str | None,
    ) -> AgentRuntimeEvent | None:
        event = AgentRuntimeEvent(
            event_type=event_type,
            lifecycle_state=lifecycle_state,
            timestamp=self._now_iso(),
            agent_role=self.agent_role,
            operation_id=self.operation_id,
            timeline_scope=self.timeline_scope,
            timeline_phase=timeline_phase,
            attempt_index=self.attempt_index,
            parent_operation_id=self.parent_operation_id,
            child_operation_id=child_operation_id or self.child_operation_id,
            app_id=self.app_id,
            plan_id=self.plan_id,
            case_id=self.case_id,
            summary=summary,
            message=message,
            data=dict(data or {}),
        )
        if self.event_sink is not None:
            self.event_sink.emit(event)
        return event

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def build_agent_runtime_host_data_payload(
    event: AgentRuntimeEvent,
    *,
    timestamp_key: str = "event_timestamp",
) -> dict[str, object]:
    payload = dict(event.data)
    context = AgentRuntimeHostContext(
        lifecycle_state=event.lifecycle_state,
        agent_role=event.agent_role,
        event_timestamp=event.timestamp,
    ).model_dump(mode="json")
    if timestamp_key != "event_timestamp":
        context[timestamp_key] = context.pop("event_timestamp")
    payload.update(context)
    return payload


__all__ = [
    "AgentEventSink",
    "AgentRuntimeEvent",
    "AgentRuntimeEventEmitter",
    "build_agent_runtime_host_data_payload",
]
