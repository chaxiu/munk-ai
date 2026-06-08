from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, cast

from munk.services.errors import DeviceConflictError, OperationCancelledError
from munk.services.machine_contracts import (
    ERROR_RUNTIME_ERROR,
    EXIT_OPERATION_CANCELLED,
    MachineCommandResponse,
    build_error_result,
    build_success_result,
)
from munk.services.operations.command_helpers import merged_tracker_artifacts, result_is_cancelled
from munk.services.operations.launcher import launch_detached_operation
from munk.services.operations.models import OperationKind
from munk.services.operations.query_service import OperationQueryService
from munk.services.operations.service import OperationCommandResult, OperationService, OperationTracker
from munk.telemetry import TelemetrySink
from munk.telemetry.models import TelemetryEntrypoint


class OperationSubmissionService:
    def __init__(
        self,
        *,
        operation_service: OperationService,
        query_service: OperationQueryService,
        telemetry: TelemetrySink,
        entrypoint: TelemetryEntrypoint,
    ) -> None:
        self._operation_service = operation_service
        self._query_service = query_service
        self._telemetry = telemetry
        self._entrypoint: TelemetryEntrypoint = entrypoint

    def submit(
        self,
        *,
        kind: OperationKind,
        command: str,
        request_json: dict[str, Any],
        app_id: str | None,
        plan_id: str | None,
        case_id: str | None,
        requires_device: bool,
        device_ref: str | None,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None,
        parent_operation_id: str | None = None,
        reuse_current_tracker: bool = True,
        background_submitter: Callable[[str, Callable[[], None]], None] | None = None,
        execute: Callable[[OperationTracker], OperationCommandResult],
    ) -> MachineCommandResponse:
        telemetry_started_at = self._telemetry.capture_command_started(
            entrypoint=self._entrypoint,
            command=command,
            properties=self._telemetry_properties(
                kind=kind,
                app_id=app_id,
                plan_id=plan_id,
                case_id=case_id,
                requires_device=requires_device,
                device_ref=device_ref,
                wait=wait,
                detach=detach,
                operation_id=None,
            ),
        )
        existing_tracker = self._operation_service.tracker_for_current_env() if reuse_current_tracker else None
        use_background_attached = not wait and not detach and existing_tracker is None and background_submitter is not None
        detached = detach or (not wait and not use_background_attached)
        created_new_tracker = existing_tracker is None
        try:
            tracker = existing_tracker or self._operation_service.create_operation(
                kind=kind,
                request_json=request_json,
                app_id=app_id,
                plan_id=plan_id,
                case_id=case_id,
                parent_operation_id=parent_operation_id,
                requires_device=requires_device,
                device_ref=device_ref,
            )
        except DeviceConflictError as exc:
            self._append_blocking_conflict_event(command=command, exc=exc, requested_device_ref=device_ref)
            self._telemetry.capture_command_finished(
                entrypoint=self._entrypoint,
                command=command,
                started_at=telemetry_started_at,
                status="failed",
                properties={
                    **self._telemetry_properties(
                        kind=kind,
                        app_id=app_id,
                        plan_id=plan_id,
                        case_id=case_id,
                        requires_device=requires_device,
                        device_ref=device_ref,
                        wait=wait,
                        detach=detach,
                        operation_id=None,
                    ),
                    "error_code": "device_conflict",
                },
            )
            return build_error_result(command=command, exc=exc)

        if created_new_tracker and requires_device:
            tracker.append_event(
                event_type="resource_claimed",
                message="device resource claimed",
                data={
                    "device_ref": device_ref,
                    "resource_scope": tracker.get_record().resource_scope,
                },
            )

        if detached and existing_tracker is None:
            if detached_argv is None:
                raise ValueError("detached operation requires CLI argv")
            try:
                launch_result = launch_detached_operation(
                    argv=detached_argv,
                    operation_id=tracker.operation_id,
                    db_path=self._operation_service.registry.db_path,
                )
            except Exception as exc:
                tracker.mark_failed(error_code=ERROR_RUNTIME_ERROR, error_message=str(exc))
                self._telemetry.capture_command_finished(
                    entrypoint=self._entrypoint,
                    command=command,
                    started_at=telemetry_started_at,
                    status="failed",
                    properties={
                        **self._telemetry_properties(
                            kind=kind,
                            app_id=app_id,
                            plan_id=plan_id,
                            case_id=case_id,
                            requires_device=requires_device,
                            device_ref=device_ref,
                            wait=wait,
                            detach=detach,
                            operation_id=tracker.operation_id,
                        ),
                        "error_code": ERROR_RUNTIME_ERROR,
                    },
                )
                return build_error_result(command=command, exc=cast(Exception, exc))
            tracker.append_event(
                event_type="operation_submitted",
                message="detached operation submitted",
                data={"pid": launch_result.pid},
            )
            tracker.update_artifacts({"launcher_log": str(launch_result.launcher_log_path)})
            self._operation_service.registry.update_operation(tracker.operation_id, pid=launch_result.pid)
            tracker.update_progress(detached_pid=launch_result.pid)
            self._telemetry.capture_command_finished(
                entrypoint=self._entrypoint,
                command=command,
                started_at=telemetry_started_at,
                status="submitted",
                properties=self._telemetry_properties(
                    kind=kind,
                    app_id=app_id,
                    plan_id=plan_id,
                    case_id=case_id,
                    requires_device=requires_device,
                    device_ref=device_ref,
                    wait=wait,
                    detach=detach,
                    operation_id=tracker.operation_id,
                ),
            )
            return build_success_result(
                command=command,
                data={
                    "operation_id": tracker.operation_id,
                    "status": "queued",
                    "verification_verdict": None,
                },
                artifacts={"launcher_log": str(launch_result.launcher_log_path)},
            )

        if use_background_attached:
            submitter = background_submitter
            if submitter is None:
                raise RuntimeError("attached background operation requires submitter")
            try:
                submitter(
                    tracker.operation_id,
                    lambda: self._execute_tracker_operation_background(
                        tracker=tracker,
                        command=command,
                        execute=execute,
                        telemetry_started_at=telemetry_started_at,
                        kind=kind,
                        app_id=app_id,
                        plan_id=plan_id,
                        case_id=case_id,
                        requires_device=requires_device,
                        device_ref=device_ref,
                        wait=wait,
                        detach=detach,
                    ),
                )
            except Exception as exc:
                tracker.mark_failed(error_code=ERROR_RUNTIME_ERROR, error_message=str(exc))
                self._telemetry.capture_command_finished(
                    entrypoint=self._entrypoint,
                    command=command,
                    started_at=telemetry_started_at,
                    status="failed",
                    properties={
                        **self._telemetry_properties(
                            kind=kind,
                            app_id=app_id,
                            plan_id=plan_id,
                            case_id=case_id,
                            requires_device=requires_device,
                            device_ref=device_ref,
                            wait=wait,
                            detach=detach,
                            operation_id=tracker.operation_id,
                        ),
                        "error_code": ERROR_RUNTIME_ERROR,
                    },
                )
                return build_error_result(command=command, exc=cast(Exception, exc))
            tracker.append_event(
                event_type="operation_submitted",
                message="attached background operation submitted",
                data={"mode": "attached_background"},
            )
            tracker.update_progress(background_mode="attached")
            self._telemetry.capture_command_finished(
                entrypoint=self._entrypoint,
                command=command,
                started_at=telemetry_started_at,
                status="submitted",
                properties=self._telemetry_properties(
                    kind=kind,
                    app_id=app_id,
                    plan_id=plan_id,
                    case_id=case_id,
                    requires_device=requires_device,
                    device_ref=device_ref,
                    wait=wait,
                    detach=detach,
                    operation_id=tracker.operation_id,
                ),
            )
            return build_success_result(
                command=command,
                data={
                    "operation_id": tracker.operation_id,
                    "status": "queued",
                    "verification_verdict": None,
                },
            )

        return self._execute_tracker_operation(
            tracker=tracker,
            command=command,
            execute=execute,
            telemetry_started_at=telemetry_started_at,
            kind=kind,
            app_id=app_id,
            plan_id=plan_id,
            case_id=case_id,
            requires_device=requires_device,
            device_ref=device_ref,
            wait=wait,
            detach=detach,
        )

    def _execute_tracker_operation_background(
        self,
        *,
        tracker: OperationTracker,
        command: str,
        execute: Callable[[OperationTracker], OperationCommandResult],
        telemetry_started_at,
        kind: OperationKind,
        app_id: str | None,
        plan_id: str | None,
        case_id: str | None,
        requires_device: bool,
        device_ref: str | None,
        wait: bool,
        detach: bool,
    ) -> None:
        self._execute_tracker_operation(
            tracker=tracker,
            command=command,
            execute=execute,
            telemetry_started_at=telemetry_started_at,
            kind=kind,
            app_id=app_id,
            plan_id=plan_id,
            case_id=case_id,
            requires_device=requires_device,
            device_ref=device_ref,
            wait=wait,
            detach=detach,
        )

    def _execute_tracker_operation(
        self,
        *,
        tracker: OperationTracker,
        command: str,
        execute: Callable[[OperationTracker], OperationCommandResult],
        telemetry_started_at,
        kind: OperationKind,
        app_id: str | None,
        plan_id: str | None,
        case_id: str | None,
        requires_device: bool,
        device_ref: str | None,
        wait: bool,
        detach: bool,
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
            tracker.mark_cancelled()
            if requires_device:
                tracker.append_event(
                    event_type="resource_released",
                    message="device resource released",
                    data={"device_ref": device_ref, "reason": "cancelled"},
                )
            self._telemetry.capture_command_finished(
                entrypoint=self._entrypoint,
                command=command,
                started_at=telemetry_started_at,
                status="cancelled",
                properties=self._telemetry_properties(
                    kind=kind,
                    app_id=app_id,
                    plan_id=plan_id,
                    case_id=case_id,
                    requires_device=requires_device,
                    device_ref=device_ref,
                    wait=wait,
                    detach=detach,
                    operation_id=tracker.operation_id,
                ),
            )
            return build_error_result(
                command=command,
                exc=interrupted,
                details={"operation_id": tracker.operation_id},
            )
        except Exception as exc:
            if result_is_cancelled(exc):
                tracker.mark_cancelled()
                if requires_device:
                    tracker.append_event(
                        event_type="resource_released",
                        message="device resource released",
                        data={"device_ref": device_ref, "reason": "cancelled"},
                    )
                self._telemetry.capture_command_finished(
                    entrypoint=self._entrypoint,
                    command=command,
                    started_at=telemetry_started_at,
                    status="cancelled",
                    properties=self._telemetry_properties(
                        kind=kind,
                        app_id=app_id,
                        plan_id=plan_id,
                        case_id=case_id,
                        requires_device=requires_device,
                        device_ref=device_ref,
                        wait=wait,
                        detach=detach,
                        operation_id=tracker.operation_id,
                    ),
                )
                return build_error_result(
                    command=command,
                    exc=cast(Exception, exc),
                    details={"operation_id": tracker.operation_id},
                )
            tracker.mark_failed(error_code=ERROR_RUNTIME_ERROR, error_message=str(exc))
            if requires_device:
                tracker.append_event(
                    event_type="resource_released",
                    message="device resource released",
                    data={"device_ref": device_ref, "reason": "failed"},
                )
            self._telemetry.capture_command_finished(
                entrypoint=self._entrypoint,
                command=command,
                started_at=telemetry_started_at,
                status="failed",
                properties={
                    **self._telemetry_properties(
                        kind=kind,
                        app_id=app_id,
                        plan_id=plan_id,
                        case_id=case_id,
                        requires_device=requires_device,
                        device_ref=device_ref,
                        wait=wait,
                        detach=detach,
                        operation_id=tracker.operation_id,
                    ),
                    "error_code": ERROR_RUNTIME_ERROR,
                },
            )
            return build_error_result(command=command, exc=cast(Exception, exc))

        result = cast(OperationCommandResult, result)
        if tracker.cancel_observed or result.status == "cancelled":
            merged_artifacts = merged_tracker_artifacts(tracker, result.artifacts)
            tracker.mark_cancelled(
                result_json=result.result_json or result.data,
                artifacts=merged_artifacts,
            )
            if requires_device:
                tracker.append_event(
                    event_type="resource_released",
                    message="device resource released",
                    data={"device_ref": device_ref, "reason": "cancelled"},
                )
            extra_artifacts, _entries = self._query_service.materialize_reproduction(tracker.operation_id)
            self._telemetry.capture_command_finished(
                entrypoint=self._entrypoint,
                command=command,
                started_at=telemetry_started_at,
                status="cancelled",
                properties=self._telemetry_properties(
                    kind=kind,
                    app_id=app_id,
                    plan_id=plan_id,
                    case_id=case_id,
                    requires_device=requires_device,
                    device_ref=device_ref,
                    wait=wait,
                    detach=detach,
                    operation_id=tracker.operation_id,
                ),
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
        if requires_device:
            tracker.append_event(
                event_type="resource_released",
                message="device resource released",
                data={"device_ref": device_ref, "reason": "succeeded"},
            )
        extra_artifacts, _entries = self._query_service.materialize_reproduction(tracker.operation_id)
        self._telemetry.capture_command_finished(
            entrypoint=self._entrypoint,
            command=command,
            started_at=telemetry_started_at,
            status="success",
            properties={
                **self._telemetry_properties(
                    kind=kind,
                    app_id=app_id,
                    plan_id=plan_id,
                    case_id=case_id,
                    requires_device=requires_device,
                    device_ref=device_ref,
                    wait=wait,
                    detach=detach,
                    operation_id=tracker.operation_id,
                ),
                "verification_verdict": result.verification_verdict,
            },
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

    def _append_blocking_conflict_event(
        self,
        *,
        command: str,
        exc: DeviceConflictError,
        requested_device_ref: str | None,
    ) -> None:
        try:
            tracker = self._operation_service.get_tracker(exc.blocking_operation_id)
        except Exception:
            return
        tracker.append_event(
            event_type="resource_conflict",
            message="device resource conflict",
            data={
                "command": command,
                "requested_device_ref": requested_device_ref,
                "blocking_device_ref": exc.blocking_device_ref,
                "reason": exc.reason,
            },
        )

    @staticmethod
    def _telemetry_properties(
        *,
        kind: OperationKind,
        app_id: str | None,
        plan_id: str | None,
        case_id: str | None,
        requires_device: bool,
        device_ref: str | None,
        wait: bool,
        detach: bool,
        operation_id: str | None,
    ) -> dict[str, Any]:
        return {
            "kind": kind,
            "operation_id": operation_id,
            "app_id": app_id,
            "plan_id": plan_id,
            "case_id": case_id,
            "requires_device": requires_device,
            "device_ref_present": device_ref is not None,
            "wait": wait,
            "detach": detach,
        }
