from __future__ import annotations

import os

from munk.services.operations.models import DeviceClaimConflict, DeviceClaimRequest, OperationRecord
from munk.services.operations.registry import OperationRegistry

from .models import InteractiveSession


class InteractiveDeviceClaimService:
    def __init__(self, operation_registry: OperationRegistry | None = None) -> None:
        self._operation_registry = operation_registry or OperationRegistry()

    def claim_for_session(self, session: InteractiveSession) -> None:
        claim_request = self._claim_request(session.device_ref)
        record = OperationRecord(
            operation_id=session.claim_owner_id,
            kind="interactive_session",
            status="running",
            app_id=session.app_target.app_id,
            request_json={
                "interactive_session_id": session.session_id,
                "platform": session.platform,
                "device_ref": session.device_ref,
            },
            progress_json=self._progress_payload(session),
            pid=os.getpid(),
            device_ref=session.device_ref,
            resource_scope=claim_request.resource_scope,
            created_at=session.started_at,
            started_at=session.started_at,
        )
        self._operation_registry.create_operation_with_claim(record, claim_request=claim_request)

    def refresh_session(self, session: InteractiveSession) -> None:
        self._operation_registry.update_operation(
            session.claim_owner_id,
            progress_json=self._progress_payload(session),
            pid=os.getpid(),
        )

    def release_for_session(
        self,
        session: InteractiveSession,
        *,
        terminal_status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._operation_registry.release_claims(session.claim_owner_id, released_at=session.updated_at)
        self._operation_registry.update_operation(
            session.claim_owner_id,
            status=terminal_status,
            error_code=error_code,
            error_message=error_message,
            finished_at=session.updated_at,
            progress_json=self._progress_payload(session),
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

    @staticmethod
    def _progress_payload(session: InteractiveSession) -> dict[str, object]:
        return {
            "interactive_session": {
                "session_id": session.session_id,
                "status": session.status,
                "last_active_at": session.last_active_at,
                "expires_at": session.expires_at,
                "idle_expires_at": session.idle_expires_at,
            }
        }
