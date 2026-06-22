from __future__ import annotations

import os

from munk.services.operations.models import DeviceClaimConflict, DeviceClaimRequest
from munk.services.operations.service import OperationService
from munk.services.operations.registry import OperationRegistry
from .operation_payloads import (
    build_interactive_session_operation_request_payload,
    build_interactive_session_progress_payload,
)

from .models import InteractiveSession



class InteractiveDeviceClaimService:
    def __init__(self, operation_registry: OperationRegistry | None = None) -> None:
        self._operation_service = OperationService(operation_registry or OperationRegistry())
        self._operation_registry = self._operation_service.registry

    def claim_for_session(self, session: InteractiveSession) -> None:
        self._operation_service.create_operation(
            operation_id=session.claim_owner_id,
            kind="interactive_session",
            status="running",
            request_json=build_interactive_session_operation_request_payload(session),
            app_id=session.app_target.app_id,
            progress_json=build_interactive_session_progress_payload(session),
            requires_device=True,
            device_ref=session.device_ref,
            pid=os.getpid(),
            created_at=session.started_at,
            started_at=session.started_at,
        )

    def refresh_session(self, session: InteractiveSession) -> None:
        tracker = self._operation_service.get_tracker(session.claim_owner_id)
        tracker.update_progress(**build_interactive_session_progress_payload(session))
        self._operation_registry.update_operation(session.claim_owner_id, pid=os.getpid())

    def release_for_session(
        self,
        session: InteractiveSession,
        *,
        terminal_status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        tracker = self._operation_service.get_tracker(session.claim_owner_id)
        tracker.update_progress(**build_interactive_session_progress_payload(session))
        self._operation_registry.release_claims(session.claim_owner_id, released_at=session.updated_at)
        self._operation_registry.update_operation(
            session.claim_owner_id,
            status=terminal_status,
            error_code=error_code,
            error_message=error_message,
            finished_at=session.updated_at,
        )

    def cleanup_for_request(self, device_ref: str | None) -> None:
        self._operation_registry.cleanup_stale_claims(claim_request=self._claim_request(device_ref))

    def find_conflict(self, device_ref: str | None) -> DeviceClaimConflict | None:
        conflicts = self._operation_registry.find_active_device_conflicts(self._claim_request(device_ref))
        return conflicts[0] if conflicts else None

    @staticmethod
    def _claim_request(device_ref: str | None) -> DeviceClaimRequest:
        return DeviceClaimRequest(
            device_ref=device_ref,
            resource_scope="device_ref" if device_ref else "device_unspecified",
        )
