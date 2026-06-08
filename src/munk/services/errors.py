from __future__ import annotations


class MunkServiceError(RuntimeError):
    """Base error for service-layer failures."""


class ConfigValidationError(MunkServiceError):
    """Raised when config resolution or validation fails."""


class MissingResourceError(MunkServiceError):
    """Raised when required local resources are missing."""


class VisionPreflightError(MunkServiceError):
    """Raised when configured model cannot accept vision input."""


class DeviceConnectionError(MunkServiceError):
    """Raised when the Android device cannot be connected."""


class RunExecutionError(MunkServiceError):
    """Raised when a run fails during execution."""


class PlanGenerationError(MunkServiceError):
    """Raised when plan generation fails."""


class AppAssetNotFoundError(MunkServiceError):
    """Raised when app-level planning assets are missing."""


class RequirementDocumentError(MunkServiceError):
    """Raised when requirement or technical documents cannot be read."""


class PlanExecutionError(MunkServiceError):
    """Raised when plan execution orchestration fails."""


class BatchPlanExecutionError(PlanExecutionError):
    """Raised when batch plan execution request is invalid or orchestration fails."""


class PlanNotFoundError(PlanExecutionError):
    """Raised when the requested plan cannot be loaded."""


class CaseNotFoundError(PlanExecutionError):
    """Raised when the requested case cannot be found in a plan."""


class StartStateError(MunkServiceError):
    """Raised when case start-state preparation cannot be completed."""


class OperationError(MunkServiceError):
    """Base error for operation lifecycle failures."""


class OperationNotFoundError(OperationError):
    """Raised when the requested operation cannot be found."""


class DeviceConflictError(OperationError):
    """Raised when a device-scoped operation conflicts with an active claim."""

    def __init__(
        self,
        *,
        requested_device_ref: str | None,
        blocking_operation_id: str,
        blocking_kind: str,
        blocking_status: str,
        blocking_device_ref: str | None,
        reason: str,
    ) -> None:
        self.requested_device_ref = requested_device_ref
        self.blocking_operation_id = blocking_operation_id
        self.blocking_kind = blocking_kind
        self.blocking_status = blocking_status
        self.blocking_device_ref = blocking_device_ref
        self.reason = reason
        requested = requested_device_ref or "<unspecified>"
        blocking = blocking_device_ref or "<unspecified>"
        super().__init__(
            f"device conflict: requested={requested} blocked_by={blocking_operation_id}"
            f" ({blocking_kind}/{blocking_status}, device_ref={blocking})"
        )

    def to_details(self) -> dict[str, str | None]:
        return {
            "requested_device_ref": self.requested_device_ref,
            "blocking_operation_id": self.blocking_operation_id,
            "blocking_kind": self.blocking_kind,
            "blocking_status": self.blocking_status,
            "blocking_device_ref": self.blocking_device_ref,
            "reason": self.reason,
        }


class OperationCancelledError(OperationError):
    """Raised when execution is cooperatively cancelled."""


class ScheduleError(MunkServiceError):
    """Base error for schedule lifecycle failures."""


class ScheduleNotFoundError(ScheduleError):
    """Raised when the requested schedule cannot be found."""

    def __init__(self, schedule_id: str) -> None:
        self.schedule_id = schedule_id
        super().__init__(f"schedule not found: {schedule_id}")


class ScheduleDeletionConflictError(ScheduleError):
    """Raised when a schedule cannot be deleted due to active runs."""

    def __init__(
        self,
        *,
        schedule_id: str,
        blocking_statuses: list[str],
    ) -> None:
        self.schedule_id = schedule_id
        self.blocking_statuses = blocking_statuses
        statuses = ",".join(blocking_statuses)
        super().__init__(
            f"schedule delete conflict: schedule={schedule_id} active_statuses={statuses}"
        )

    def to_details(self) -> dict[str, str | list[str]]:
        return {
            "schedule_id": self.schedule_id,
            "blocking_statuses": self.blocking_statuses,
        }
