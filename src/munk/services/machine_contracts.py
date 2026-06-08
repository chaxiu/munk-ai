from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from munk.services.errors import (
    BatchPlanExecutionError,
    ConfigValidationError,
    DeviceConflictError,
    OperationCancelledError,
    OperationNotFoundError,
    ScheduleDeletionConflictError,
    ScheduleNotFoundError,
)
from munk.services.operations.models import VerificationVerdict

EXIT_OK = 0
EXIT_VERDICT_FAILED = 10
EXIT_VERDICT_INCONCLUSIVE = 11
EXIT_INVALID_REQUEST = 20
EXIT_CONFIG_ERROR = 21
EXIT_OPERATION_NOT_FOUND = 24
EXIT_DEVICE_CONFLICT = 25
EXIT_RUNTIME_ERROR = 30
EXIT_OPERATION_CANCELLED = 31

ERROR_INVALID_REQUEST = "invalid_request"
ERROR_CONFIG_ERROR = "config_error"
ERROR_RUNTIME_ERROR = "runtime_error"
ERROR_OPERATION_NOT_FOUND = "operation_not_found"
ERROR_DEVICE_CONFLICT = "device_conflict"
ERROR_OPERATION_CANCELLED = "operation_cancelled"
ERROR_SCHEDULE_DELETE_CONFLICT = "schedule_delete_conflict"


class InvalidMachineRequestError(ValueError):
    """Raised when machine request input is invalid."""


@dataclass(frozen=True)
class MachineCommandResponse:
    payload: dict[str, Any]
    exit_code: int
    http_status: int


def build_success_response(
    *,
    command: str,
    data: dict[str, Any],
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "command": command,
        "data": data,
    }
    if artifacts:
        payload["artifacts"] = artifacts
    return payload


def build_error_response(
    *,
    command: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {
        "ok": False,
        "command": command,
        "error": error,
    }


def classify_exception(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, InvalidMachineRequestError):
        return EXIT_INVALID_REQUEST, ERROR_INVALID_REQUEST
    if isinstance(exc, ConfigValidationError):
        return EXIT_CONFIG_ERROR, ERROR_CONFIG_ERROR
    if isinstance(exc, BatchPlanExecutionError):
        return EXIT_INVALID_REQUEST, ERROR_INVALID_REQUEST
    if isinstance(exc, OperationNotFoundError):
        return EXIT_OPERATION_NOT_FOUND, ERROR_OPERATION_NOT_FOUND
    if isinstance(exc, ScheduleNotFoundError):
        return EXIT_OPERATION_NOT_FOUND, ERROR_OPERATION_NOT_FOUND
    if isinstance(exc, ScheduleDeletionConflictError):
        return EXIT_DEVICE_CONFLICT, ERROR_SCHEDULE_DELETE_CONFLICT
    if isinstance(exc, DeviceConflictError):
        return EXIT_DEVICE_CONFLICT, ERROR_DEVICE_CONFLICT
    if isinstance(exc, OperationCancelledError):
        return EXIT_OPERATION_CANCELLED, ERROR_OPERATION_CANCELLED
    return EXIT_RUNTIME_ERROR, ERROR_RUNTIME_ERROR


def http_status_for_result(*, exit_code: int, error_code: str | None = None) -> int:
    if exit_code == EXIT_OK or exit_code in {EXIT_VERDICT_FAILED, EXIT_VERDICT_INCONCLUSIVE}:
        return 200
    if exit_code in {EXIT_INVALID_REQUEST, EXIT_CONFIG_ERROR}:
        return 400
    if exit_code == EXIT_OPERATION_NOT_FOUND:
        return 404
    if exit_code in {EXIT_DEVICE_CONFLICT, EXIT_OPERATION_CANCELLED}:
        return 409
    if error_code == ERROR_OPERATION_NOT_FOUND:
        return 404
    if error_code in {
        ERROR_DEVICE_CONFLICT,
        ERROR_OPERATION_CANCELLED,
        ERROR_SCHEDULE_DELETE_CONFLICT,
    }:
        return 409
    return 500


def build_success_result(
    *,
    command: str,
    data: dict[str, Any],
    artifacts: dict[str, Any] | None = None,
    exit_code: int = EXIT_OK,
    http_status: int | None = None,
) -> MachineCommandResponse:
    return MachineCommandResponse(
        payload=build_success_response(command=command, data=data, artifacts=artifacts),
        exit_code=exit_code,
        http_status=http_status if http_status is not None else http_status_for_result(exit_code=exit_code),
    )


def build_error_result(
    *,
    command: str,
    exc: Exception,
    details: dict[str, Any] | None = None,
) -> MachineCommandResponse:
    exit_code, error_code = classify_exception(exc)
    if details is None and isinstance(exc, DeviceConflictError):
        details = exc.to_details()
    if details is None and isinstance(exc, ScheduleDeletionConflictError):
        details = exc.to_details()
    return MachineCommandResponse(
        payload=build_error_response(
            command=command,
            code=error_code,
            message=str(exc),
            details=details,
        ),
        exit_code=exit_code,
        http_status=http_status_for_result(exit_code=exit_code, error_code=error_code),
    )


def verdict_exit_code(verdict: VerificationVerdict) -> int:
    if verdict == "failed":
        return EXIT_VERDICT_FAILED
    if verdict == "inconclusive":
        return EXIT_VERDICT_INCONCLUSIVE
    return EXIT_OK
