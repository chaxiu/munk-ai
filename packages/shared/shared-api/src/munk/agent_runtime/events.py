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
    message: str | None = None
    data: dict[str, object] = Field(default_factory=empty_object_map)


class AgentEventSink(Protocol):
    def emit(self, event: AgentRuntimeEvent) -> None: ...


@dataclass(frozen=True)
class AgentRuntimeEventEmitter:
    agent_role: str
    operation_id: str | None = None
    event_sink: AgentEventSink | None = None

    def emit_started(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_started",
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="started",
            message=message,
            data=data,
        )

    def emit_running(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_running",
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="running",
            message=message,
            data=data,
        )

    def emit_ended(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_ended",
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="ended",
            message=message,
            data=data,
        )

    def emit_failed(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_failed",
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="failed",
            message=message,
            data=data,
        )

    def emit_canceled(
        self,
        *,
        message: str | None = None,
        data: dict[str, object] | None = None,
        event_type: str = "agent_canceled",
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="canceled",
            message=message,
            data=data,
        )

    def emit_progress(
        self,
        *,
        event_type: str,
        message: str | None = None,
        data: dict[str, object] | None = None,
    ) -> AgentRuntimeEvent | None:
        return self._emit(
            event_type=event_type,
            lifecycle_state="running",
            message=message,
            data=data,
        )

    def _emit(
        self,
        *,
        event_type: str,
        lifecycle_state: AgentLifecycleState,
        message: str | None,
        data: dict[str, object] | None,
    ) -> AgentRuntimeEvent | None:
        event = AgentRuntimeEvent(
            event_type=event_type,
            lifecycle_state=lifecycle_state,
            timestamp=self._now_iso(),
            agent_role=self.agent_role,
            operation_id=self.operation_id,
            message=message,
            data=dict(data or {}),
        )
        if self.event_sink is not None:
            self.event_sink.emit(event)
        return event

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ["AgentEventSink", "AgentRuntimeEvent", "AgentRuntimeEventEmitter"]
