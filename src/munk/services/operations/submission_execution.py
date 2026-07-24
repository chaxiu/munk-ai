from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from munk.services.errors import OperationCancelledError
from munk.services.machine_contracts import (
    ERROR_RUNTIME_ERROR,
    EXIT_OPERATION_CANCELLED,
    MachineCommandResponse,
    build_error_result,
    build_success_result,
)
from munk.services.operations.command_helpers import merged_tracker_artifacts, result_is_cancelled
from munk.services.operations.models import OperationKind
from munk.services.operations.query_service import OperationQueryService
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.telemetry import TelemetrySink
from munk.telemetry.models import TelemetryEntrypoint


@dataclass(frozen=True)
class SubmissionExecutionContext:
    kind: OperationKind
    app_id: str | None
    plan_id: str | None
    case_id: str | None
    requires_device: bool
    device_ref: str | None
    wait: bool
    detach: bool


def submission_telemetry_properties(
    *,
    context: SubmissionExecutionContext,
    operation_id: str | None,
) -> dict[str, Any]:
    return {
        "kind": context.kind,
        "operation_id": operation_id,
        "app_id": context.app_id,
        "plan_id": context.plan_id,
        "case_id": context.case_id,
        "requires_device": context.requires_device,
        "device_ref_present": context.device_ref is not None,
        "wait": context.wait,
        "detach": context.detach,
    }


class SubmissionExecutionRunner:
    def __init__(
        self,
        *,
        query_service: OperationQueryService,
        telemetry: TelemetrySink,
        entrypoint: TelemetryEntrypoint,
    ) -> None:
        self._query_service = query_service
        self._telemetry = telemetry
        self._entrypoint = entrypoint

    def execute(
        self,
        *,
        tracker: OperationTracker,
        command: str,
        execute: Callable[[OperationTracker], OperationCommandResult],
        telemetry_started_at: float,
        context: SubmissionExecutionContext,
    ) -> MachineCommandResponse:
        tracker.mark_running(pid=os.getpid())
        tracker.append_event(
            event_type="operation_started",
            message="operation started",
            data={"pid": os.getpid(), "command": command},
        )
        try:
            result = execute(tracker)
        except KeyboardInterrupt:
            interrupted = OperationCancelledError("operation interrupted by user")
            tracker.append_event(
                event_type="operation_interrupted",
                message="operation interrupted by user",
                data={"command": command},
            )
            tracker.mark_interrupted(
                error_code="operation_interrupted",
                error_message="operation interrupted by user",
            )
            self._append_resource_released_event(
                tracker=tracker,
                device_ref=context.device_ref,
                requires_device=context.requires_device,
                reason="interrupted",
            )
            self._capture_command_finished(
                command=command,
                started_at=telemetry_started_at,
                status="interrupted",
                context=context,
                operation_id=tracker.operation_id,
            )
            return build_error_result(
                command=command,
                exc=interrupted,
                details={"operation_id": tracker.operation_id},
            )
        except Exception as exc:
            if result_is_cancelled(exc):
                tracker.mark_cancelled()
                self._append_resource_released_event(
                    tracker=tracker,
                    device_ref=context.device_ref,
                    requires_device=context.requires_device,
                    reason="cancelled",
                )
                self._capture_command_finished(
                    command=command,
                    started_at=telemetry_started_at,
                    status="cancelled",
                    context=context,
                    operation_id=tracker.operation_id,
                )
                return build_error_result(
                    command=command,
                    exc=cast(Exception, exc),
                    details={"operation_id": tracker.operation_id},
                )
            tracker.mark_failed(error_code=ERROR_RUNTIME_ERROR, error_message=str(exc))
            self._append_resource_released_event(
                tracker=tracker,
                device_ref=context.device_ref,
                requires_device=context.requires_device,
                reason="failed",
            )
            self._capture_command_finished(
                command=command,
                started_at=telemetry_started_at,
                status="failed",
                context=context,
                operation_id=tracker.operation_id,
                extra_properties={"error_code": ERROR_RUNTIME_ERROR},
            )
            return build_error_result(command=command, exc=cast(Exception, exc))

        result = cast(OperationCommandResult, result)
        if tracker.cancel_observed or result.status == "cancelled":
            merged_artifacts = merged_tracker_artifacts(tracker, result.artifacts)
            tracker.mark_cancelled(
                result_json=result.result_json or result.data,
                artifacts=merged_artifacts,
            )
            self._append_resource_released_event(
                tracker=tracker,
                device_ref=context.device_ref,
                requires_device=context.requires_device,
                reason="cancelled",
            )
            extra_artifacts, _entries = self._query_service.materialize_reproduction(tracker.operation_id)
            self._capture_command_finished(
                command=command,
                started_at=telemetry_started_at,
                status="cancelled",
                context=context,
                operation_id=tracker.operation_id,
            )
            return build_success_result(
                command=command,
                data={
                    **result.data,
                    "operation_id": tracker.operation_id,
                    "status": "cancelled",
                    "verification_verdict": None,
                },
                artifacts={**merged_artifacts, **extra_artifacts},
                exit_code=EXIT_OPERATION_CANCELLED,
            )

        merged_artifacts = merged_tracker_artifacts(tracker, result.artifacts)
        tracker.mark_succeeded(
            verification_verdict=result.verification_verdict,
            result_json=result.result_json or result.data,
            artifacts=merged_artifacts,
        )
        self._append_resource_released_event(
            tracker=tracker,
            device_ref=context.device_ref,
            requires_device=context.requires_device,
            reason="succeeded",
        )
        extra_artifacts, _entries = self._query_service.materialize_reproduction(tracker.operation_id)
        self._capture_command_finished(
            command=command,
            started_at=telemetry_started_at,
            status="success",
            context=context,
            operation_id=tracker.operation_id,
            extra_properties={"verification_verdict": result.verification_verdict},
        )
        return build_success_result(
            command=command,
            data={
                **result.data,
                "operation_id": tracker.operation_id,
                "status": "succeeded",
                "verification_verdict": result.verification_verdict,
            },
            artifacts={**merged_artifacts, **extra_artifacts},
            exit_code=result.exit_code,
        )

    def _capture_command_finished(
        self,
        *,
        command: str,
        started_at: float,
        status: str,
        context: SubmissionExecutionContext,
        operation_id: str | None,
        extra_properties: dict[str, Any] | None = None,
    ) -> None:
        properties = submission_telemetry_properties(
            context=context,
            operation_id=operation_id,
        )
        if extra_properties:
            properties = {**properties, **extra_properties}
        self._telemetry.capture_command_finished(
            entrypoint=self._entrypoint,
            command=command,
            started_at=started_at,
            status=status,
            properties=properties,
        )

    @staticmethod
    def _append_resource_released_event(
        *,
        tracker: OperationTracker,
        device_ref: str | None,
        requires_device: bool,
        reason: str,
    ) -> None:
        if not requires_device:
            return
        tracker.append_event(
            event_type="resource_released",
            message="device resource released",
            data={"device_ref": device_ref, "reason": reason},
        )
