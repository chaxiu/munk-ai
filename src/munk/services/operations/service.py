from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from munk.services.errors import OperationCancelledError
from munk.services.events import RunEvent
from munk.services.operations.models import (
    OPERATION_DB_ENV,
    OPERATION_ID_ENV,
    CleanupClaimResult,
    DeviceClaimRequest,
    OperationKind,
    OperationRecord,
    OperationStatus,
    ResourceScope,
    VerificationVerdict,
)
from munk.services.operations.paths import operations_db_path
from munk.services.operations.registry import OperationRegistry


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
        return self._registry.update_operation(
            self.operation_id,
            status="running",
            pid=pid,
            started_at=self._now_iso(),
            progress_json=progress or {},
        )

    def mark_succeeded(
        self,
        *,
        verification_verdict: VerificationVerdict,
        result_json: dict[str, Any] | None,
        artifacts: dict[str, str] | None = None,
        progress: dict[str, Any] | None = None,
    ) -> OperationRecord:
        record = self._registry.update_operation(
            self.operation_id,
            status="succeeded",
            verification_verdict=verification_verdict,
            result_json=result_json,
            artifacts_json=artifacts or {},
            progress_json=progress or self.get_record().progress_json,
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
        record = self._registry.update_operation(
            self.operation_id,
            status="failed",
            error_code=error_code,
            error_message=error_message,
            artifacts_json=artifacts or self.get_record().artifacts_json,
            progress_json=progress or self.get_record().progress_json,
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
        record = self._registry.update_operation(
            self.operation_id,
            status="cancelled",
            verification_verdict=None,
            result_json=result_json,
            artifacts_json=artifacts or self.get_record().artifacts_json,
            progress_json=progress or self.get_record().progress_json,
            finished_at=self._now_iso(),
            error_code="operation_cancelled",
            error_message="operation cancelled cooperatively",
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
        return self._registry.update_operation(self.operation_id, progress_json=current)

    def update_operation(self, **fields: Any) -> OperationRecord:
        return self._registry.update_operation(self.operation_id, **fields)

    def append_run_event(self, event: RunEvent) -> None:
        self._registry.append_event(
            self.operation_id,
            timestamp=event.timestamp,
            event_type=event.type.value,
            message=event.message,
            data_json=dict(event.data),
        )
        self.update_progress(last_event_type=event.type.value)

    def append_event(self, *, event_type: str, message: str | None, data: dict[str, Any] | None = None) -> None:
        self._registry.append_event(
            self.operation_id,
            timestamp=self._now_iso(),
            event_type=event_type,
            message=message,
            data_json=data or {},
        )
        self.update_progress(last_event_type=event_type)

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


class OperationService:
    def __init__(self, registry: OperationRegistry | None = None) -> None:
        self._registry = registry or OperationRegistry(self._registry_path_from_env())
        self._registry.cleanup_stale_claims()

    @property
    def registry(self) -> OperationRegistry:
        return self._registry

    def create_operation(
        self,
        *,
        kind: OperationKind,
        request_json: dict[str, Any],
        app_id: str | None = None,
        plan_id: str | None = None,
        case_id: str | None = None,
        parent_operation_id: str | None = None,
        batch_id: str | None = None,
        position_index: int | None = None,
        position_label: str | None = None,
        requires_device: bool = False,
        device_ref: str | None = None,
    ) -> OperationTracker:
        resource_scope = self._resource_scope(requires_device=requires_device, device_ref=device_ref)
        record = OperationRecord(
            operation_id=default_operation_id(),
            kind=kind,
            status="queued",
            app_id=app_id,
            plan_id=plan_id,
            case_id=case_id,
            parent_operation_id=parent_operation_id,
            batch_id=batch_id,
            position_index=position_index,
            position_label=position_label,
            request_json=request_json,
            device_ref=device_ref,
            resource_scope=resource_scope,
        )
        claim_request = self._claim_request(resource_scope=resource_scope, device_ref=device_ref)
        if claim_request is None:
            self._registry.create_operation(record)
        else:
            self._registry.create_operation_with_claim(record, claim_request=claim_request)
        return OperationTracker(self._registry, record.operation_id)

    def cleanup_stale_claims(
        self,
        *,
        claim_request: DeviceClaimRequest | None = None,
    ) -> list[CleanupClaimResult]:
        return self._registry.cleanup_stale_claims(claim_request=claim_request)

    def tracker_for_current_env(self) -> OperationTracker | None:
        operation_id = os.environ.get(OPERATION_ID_ENV)
        if not operation_id:
            return None
        return OperationTracker(self._registry, operation_id)

    def get_tracker(self, operation_id: str) -> OperationTracker:
        self._registry.get_operation(operation_id)
        return OperationTracker(self._registry, operation_id)

    @staticmethod
    def _resource_scope(*, requires_device: bool, device_ref: str | None) -> ResourceScope:
        if not requires_device:
            return "none"
        if device_ref:
            return "device_ref"
        return "device_unspecified"

    @staticmethod
    def _claim_request(
        *,
        resource_scope: ResourceScope,
        device_ref: str | None,
    ) -> DeviceClaimRequest | None:
        if resource_scope == "none":
            return None
        return DeviceClaimRequest(device_ref=device_ref, resource_scope=resource_scope)

    @staticmethod
    def _registry_path_from_env():
        db_path = os.environ.get(OPERATION_DB_ENV)
        if db_path:
            return Path(db_path)
        return operations_db_path()
