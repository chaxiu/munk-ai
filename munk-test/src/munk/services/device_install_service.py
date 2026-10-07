from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from munk.adapters.shared.app_lifecycle import AppLifecycleResult, AppLifecycleService
from munk.adapters.shared.machine_requests import AppInstallRequest
from munk.app import AppTarget
from munk.services.machine_contracts import (
    ERROR_INVALID_REQUEST,
    ERROR_RUNTIME_ERROR,
    InvalidMachineRequestError,
)
from munk.services.operations.registry import OperationRegistry
from munk.services.operations.service import OperationService


@dataclass(frozen=True)
class DeviceInstallResult:
    operation_id: str
    action: str
    app_id: str
    platform: str
    device_ref: str
    entry_identity: str
    artifact_path: str | None


class DeviceInstallService:
    """Synchronous app install with the same device claim semantics as verify."""

    def __init__(
        self,
        *,
        operation_registry: OperationRegistry | None = None,
        app_lifecycle: AppLifecycleService | None = None,
    ) -> None:
        self._operation_service = OperationService(operation_registry)
        self._app_lifecycle = app_lifecycle or AppLifecycleService()

    def install(
        self,
        *,
        device_ref: str,
        artifact_path: Path,
        app_target: AppTarget,
    ) -> DeviceInstallResult:
        normalized_device_ref = device_ref.strip()
        if not normalized_device_ref:
            raise InvalidMachineRequestError("device_ref is required for app_install")

        request_json = {
            "device_ref": normalized_device_ref,
            "artifact_path": str(artifact_path),
            "app_target": app_target.model_dump(mode="json"),
        }
        tracker = self._operation_service.create_operation(
            kind="app_install",
            status="running",
            request_json=request_json,
            app_id=app_target.app_id,
            requires_device=True,
            device_ref=normalized_device_ref,
            pid=os.getpid(),
        )
        try:
            lifecycle_result = self._app_lifecycle.install(
                AppInstallRequest(
                    app_id=app_target.app_id,
                    app_target=app_target,
                    device_ref=normalized_device_ref,
                    artifact_path=artifact_path,
                )
            )
        except InvalidMachineRequestError as exc:
            tracker.mark_failed(error_code=ERROR_INVALID_REQUEST, error_message=str(exc))
            raise
        except Exception as exc:
            tracker.mark_failed(error_code=ERROR_RUNTIME_ERROR, error_message=str(exc))
            raise

        result = self._to_result(operation_id=tracker.operation_id, lifecycle_result=lifecycle_result)
        tracker.mark_succeeded(
            verification_verdict=None,
            result_json={
                "action": result.action,
                "app_id": result.app_id,
                "platform": result.platform,
                "device_ref": result.device_ref,
                "entry_identity": result.entry_identity,
                "artifact_path": result.artifact_path,
            },
        )
        return result

    @staticmethod
    def _to_result(*, operation_id: str, lifecycle_result: AppLifecycleResult) -> DeviceInstallResult:
        device_ref = lifecycle_result.device_ref
        if not device_ref:
            raise InvalidMachineRequestError("app_install requires a resolved device_ref")
        return DeviceInstallResult(
            operation_id=operation_id,
            action=lifecycle_result.action,
            app_id=lifecycle_result.app_id,
            platform=lifecycle_result.platform,
            device_ref=device_ref,
            entry_identity=lifecycle_result.entry_identity,
            artifact_path=lifecycle_result.artifact_path,
        )
