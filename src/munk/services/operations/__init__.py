from __future__ import annotations

from importlib import import_module

__all__ = [
    "CleanupClaimResult",
    "default_operation_id",
    "DetachedLaunchResult",
    "DeviceClaimConflict",
    "DeviceClaimRequest",
    "now_iso",
    "OPERATION_DB_ENV",
    "OPERATION_ID_ENV",
    "OperationCommandResult",
    "OperationEventRecord",
    "OperationKind",
    "OperationQueryService",
    "OperationRecord",
    "OperationRegistry",
    "OperationService",
    "OperationStatus",
    "OperationTracker",
    "ResourceScope",
    "VerificationVerdict",
]

_EXPORTS = {
    "CleanupClaimResult": (".models", "CleanupClaimResult"),
    "default_operation_id": (".service", "default_operation_id"),
    "DetachedLaunchResult": (".models", "DetachedLaunchResult"),
    "DeviceClaimConflict": (".models", "DeviceClaimConflict"),
    "DeviceClaimRequest": (".models", "DeviceClaimRequest"),
    "now_iso": (".models", "now_iso"),
    "OPERATION_DB_ENV": (".models", "OPERATION_DB_ENV"),
    "OPERATION_ID_ENV": (".models", "OPERATION_ID_ENV"),
    "OperationCommandResult": (".service", "OperationCommandResult"),
    "OperationEventRecord": (".models", "OperationEventRecord"),
    "OperationKind": (".models", "OperationKind"),
    "OperationQueryService": (".query_service", "OperationQueryService"),
    "OperationRecord": (".models", "OperationRecord"),
    "OperationRegistry": (".registry", "OperationRegistry"),
    "OperationService": (".service", "OperationService"),
    "OperationStatus": (".models", "OperationStatus"),
    "OperationTracker": (".service", "OperationTracker"),
    "ResourceScope": (".models", "ResourceScope"),
    "VerificationVerdict": (".models", "VerificationVerdict"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
