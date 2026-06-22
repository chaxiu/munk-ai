from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from munk.services.operations.models import (
    OPERATION_DB_ENV,
    OPERATION_ID_ENV,
    CleanupClaimResult,
    DeviceClaimRequest,
    OperationKind,
    OperationRecord,
    OperationStatus,
    ResourceScope,
)
from munk.services.operations.paths import operations_db_path
from munk.services.operations.payloads import (
    normalize_operation_progress_payload,
    normalize_operation_request_payload,
    with_projected_fields,
)
from munk.services.operations.registry import OperationRegistry
from munk.services.operations.tracker import (
    OperationCommandResult,
    OperationTracker,
    default_operation_id,
)

__all__ = [
    "OperationCommandResult",
    "OperationService",
    "OperationTracker",
    "default_operation_id",
]


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
        operation_id: str | None = None,
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
        status: OperationStatus = "queued",
        progress_json: dict[str, Any] | None = None,
        pid: int | None = None,
        created_at: str | None = None,
        started_at: str | None = None,
    ) -> OperationTracker:
        resource_scope = self._resource_scope(requires_device=requires_device, device_ref=device_ref)
        normalized_request_json = normalize_operation_request_payload(kind, request_json)
        normalized_progress_json = normalize_operation_progress_payload(kind, progress_json or {})
        created_timestamp = created_at or datetime.now(timezone.utc).isoformat()
        record = with_projected_fields(
            OperationRecord(
                operation_id=operation_id or default_operation_id(),
                kind=kind,
                status=status,
                app_id=app_id,
                plan_id=plan_id,
                case_id=case_id,
                parent_operation_id=parent_operation_id,
                batch_id=batch_id,
                position_index=position_index,
                position_label=position_label,
                request_json=normalized_request_json,
                progress_json=normalized_progress_json,
                pid=pid,
                device_ref=device_ref,
                resource_scope=resource_scope,
                created_at=created_timestamp,
                started_at=started_at or (created_timestamp if status == "running" else None),
            )
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
