from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from munk.agent_runtime import AgentRuntimeEvent
from munk.services.errors import OperationCancelledError
from munk.services.events import RunEvent
from munk.services.operations.event_payload_registry import serialize_operation_event_payload
from munk.services.operations.event_payloads import build_operation_timeline_progress_payload
from munk.services.operations.models import OperationRecord, OperationStatus, VerificationVerdict
from munk.services.operations.payloads import (
    normalize_operation_progress_payload,
    normalize_operation_result_payload,
)
from munk.services.operations.registry import OperationRegistry
from munk.services.operations.timeline import (
    base_timeline_payload,
    build_timeline_payload_from_agent_runtime_event,
    build_timeline_payload_from_run_event,
)


def default_operation_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8]
    return f"op_{timestamp}_{suffix}"


@dataclass
class OperationCommandResult:
    data: dict[str, Any]
    artifacts: dict[str, Any]
    verification_verdict: VerificationVerdict = None
    result_json: dict[str, Any] | None = None
    status: OperationStatus = "succeeded"
    exit_code: int = 0


class OperationTracker:
    def __init__(self, registry: OperationRegistry, operation_id: str) -> None:
        self._registry = registry
        self.operation_id = operation_id
        self._cancel_observed = False

    @property
    def cancel_observed(self) -> bool:
        return self._cancel_observed

    @property
    def registry(self) -> OperationRegistry:
        return self._registry

    def get_record(self) -> OperationRecord:
        return self._registry.get_operation(self.operation_id)

    def mark_running(self, *, pid: int, progress: dict[str, Any] | None = None) -> OperationRecord:
        progress_json = self._normalized_progress_payload(progress or {})
        return self._registry.update_operation(
            self.operation_id,
            status="running",
            pid=pid,
            started_at=self._now_iso(),
            progress_json=progress_json,
        )

    def mark_succeeded(
        self,
        *,
        verification_verdict: VerificationVerdict,
        result_json: dict[str, Any] | None,
        artifacts: dict[str, str] | None = None,
        progress: dict[str, Any] | None = None,
    ) -> OperationRecord:
        normalized_result_json = self._normalized_result_payload(result_json)
        normalized_progress_json = self._normalized_progress_payload(progress or self.get_record().progress_json)
        record = self._registry.update_operation(
            self.operation_id,
            status="succeeded",
            verification_verdict=verification_verdict,
            result_json=normalized_result_json,
            artifacts_json=artifacts or {},
            progress_json=normalized_progress_json,
            finished_at=self._now_iso(),
            error_code=None,
            error_message=None,
        )
        self._registry.release_claims(self.operation_id)
        return record

    def mark_failed(
        self,
        *,
        error_code: str,
        error_message: str,
        artifacts: dict[str, str] | None = None,
        progress: dict[str, Any] | None = None,
    ) -> OperationRecord:
        normalized_progress_json = self._normalized_progress_payload(progress or self.get_record().progress_json)
        record = self._registry.update_operation(
            self.operation_id,
            status="failed",
            error_code=error_code,
            error_message=error_message,
            artifacts_json=artifacts or self.get_record().artifacts_json,
            progress_json=normalized_progress_json,
            finished_at=self._now_iso(),
        )
        self._registry.release_claims(self.operation_id)
        return record

    def mark_cancelled(
        self,
        *,
        result_json: dict[str, Any] | None = None,
        artifacts: dict[str, str] | None = None,
        progress: dict[str, Any] | None = None,
    ) -> OperationRecord:
        normalized_result_json = self._normalized_result_payload(result_json)
        normalized_progress_json = self._normalized_progress_payload(progress or self.get_record().progress_json)
        record = self._registry.update_operation(
            self.operation_id,
            status="cancelled",
            verification_verdict=None,
            result_json=normalized_result_json,
            artifacts_json=artifacts or self.get_record().artifacts_json,
            progress_json=normalized_progress_json,
            finished_at=self._now_iso(),
            error_code="operation_cancelled",
            error_message="operation cancelled cooperatively",
        )
        self._registry.release_claims(self.operation_id)
        return record

    def mark_interrupted(
        self,
        *,
        error_code: str = "operation_interrupted",
        error_message: str = "operation interrupted",
        result_json: dict[str, Any] | None = None,
        artifacts: dict[str, str] | None = None,
        progress: dict[str, Any] | None = None,
    ) -> OperationRecord:
        normalized_result_json = self._normalized_result_payload(result_json)
        normalized_progress_json = self._normalized_progress_payload(progress or self.get_record().progress_json)
        record = self._registry.update_operation(
            self.operation_id,
            status="interrupted",
            verification_verdict=None,
            result_json=normalized_result_json,
            artifacts_json=artifacts or self.get_record().artifacts_json,
            progress_json=normalized_progress_json,
            finished_at=self._now_iso(),
            error_code=error_code,
            error_message=error_message,
        )
        self._registry.release_claims(self.operation_id)
        return record

    def update_artifacts(self, artifacts: dict[str, str]) -> OperationRecord:
        current = self.get_record().artifacts_json
        updated = dict(current)
        updated.update(artifacts)
        return self._registry.update_operation(self.operation_id, artifacts_json=updated)

    def update_progress(self, **progress: Any) -> OperationRecord:
        current = dict(self.get_record().progress_json)
        current.update(progress)
        return self._registry.update_operation(
            self.operation_id,
            progress_json=self._normalized_progress_payload(current),
        )

    def update_operation(self, **fields: Any) -> OperationRecord:
        return self._registry.update_operation(self.operation_id, **fields)

    def append_run_event(self, event: RunEvent) -> None:
        payload = build_timeline_payload_from_run_event(
            event,
            operation_id=self.operation_id,
        )
        self._append_timeline_record(
            timestamp=event.timestamp,
            event_type=event.type.value,
            message=event.message,
            payload=payload,
        )

    def append_event(self, *, event_type: str, message: str | None, data: dict[str, Any] | None = None) -> None:
        payload = serialize_operation_event_payload(event_type, data)
        self._registry.append_event(
            self.operation_id,
            timestamp=self._now_iso(),
            event_type=event_type,
            message=message,
            data_json=payload,
        )
        self.update_progress(last_event_type=event_type)

    def append_agent_runtime_event(self, event: AgentRuntimeEvent) -> None:
        payload = build_timeline_payload_from_agent_runtime_event(
            event,
            operation_id=self.operation_id,
        )
        self._append_timeline_record(
            timestamp=event.timestamp,
            event_type=event.event_type,
            message=event.message,
            payload=payload,
        )

    def append_timeline_event(
        self,
        *,
        event_type: str,
        message: str | None,
        agent_role: str,
        timeline_scope: str,
        timeline_phase: str,
        summary: str | None = None,
        attempt_index: int | None = None,
        timestamp: str | None = None,
        parent_operation_id: str | None = None,
        child_operation_id: str | None = None,
        app_id: str | None = None,
        plan_id: str | None = None,
        case_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        payload = base_timeline_payload(
            agent_role=agent_role,
            operation_id=self.operation_id,
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
        self._append_timeline_record(
            timestamp=timestamp or self._now_iso(),
            event_type=event_type,
            message=message,
            payload=payload,
        )

    def _append_timeline_record(
        self,
        *,
        timestamp: str,
        event_type: str,
        message: str | None,
        payload: dict[str, Any],
    ) -> None:
        serialized_payload = serialize_operation_event_payload(event_type, payload)
        self._registry.append_event(
            self.operation_id,
            timestamp=timestamp,
            event_type=event_type,
            message=message,
            data_json=serialized_payload,
        )
        self.update_progress(
            **build_operation_timeline_progress_payload(
                event_type=event_type,
                payload=serialized_payload,
            )
        )

    def _normalized_progress_payload(self, progress: dict[str, Any]) -> dict[str, Any]:
        return normalize_operation_progress_payload(self.get_record().kind, progress)

    def _normalized_result_payload(self, result_json: dict[str, Any] | None) -> dict[str, Any] | None:
        return normalize_operation_result_payload(self.get_record().kind, result_json)

    def should_cancel(self) -> bool:
        record = self.get_record()
        if record.cancel_requested:
            self._cancel_observed = True
            return True
        return False

    def raise_if_cancelled(self) -> None:
        if self.should_cancel():
            raise OperationCancelledError("operation cancelled cooperatively")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
