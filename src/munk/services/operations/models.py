from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

OperationKind = Literal[
    "plan",
    "run_case",
    "run_plan",
    "run_plans",
    "verify_change",
    "review",
    "optimize_case",
    "knowledge_post_action",
    "record_case",
    "recording_analysis",
    "interactive_session",
]
OperationStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
VerificationVerdict = Literal["passed", "failed", "inconclusive"] | None
ResourceScope = Literal["none", "device_ref", "device_unspecified"]
OPERATION_ID_ENV = "MUNK_OPERATION_ID"
OPERATION_DB_ENV = "MUNK_OPERATION_DB"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationArtifactSnapshot(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class OperationRecord(BaseModel):
    operation_id: str
    kind: OperationKind
    status: OperationStatus
    verification_verdict: VerificationVerdict = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    parent_operation_id: str | None = None
    batch_id: str | None = None
    position_index: int | None = None
    position_label: str | None = None
    request_json: dict[str, Any] = Field(default_factory=dict)
    result_json: dict[str, Any] | None = None
    artifacts_json: dict[str, str] = Field(default_factory=dict)
    progress_json: dict[str, Any] = Field(default_factory=dict)
    pid: int | None = None
    cancel_requested: bool = False
    device_ref: str | None = None
    resource_scope: ResourceScope = "none"
    conflict_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = Field(default_factory=now_iso)
    started_at: str | None = None
    finished_at: str | None = None


class OperationEventRecord(BaseModel):
    seq: int
    operation_id: str
    timestamp: str = Field(default_factory=now_iso)
    event_type: str
    message: str | None = None
    data_json: dict[str, Any] = Field(default_factory=dict)


class DetachedLaunchResult(BaseModel):
    operation_id: str
    pid: int
    command: list[str]
    launcher_log_path: Path


class DeviceClaimRequest(BaseModel):
    device_ref: str | None = None
    resource_scope: ResourceScope = "device_unspecified"

    def resource_keys(self) -> list[str] | None:
        if self.resource_scope == "none":
            return None
        if self.resource_scope == "device_ref" and self.device_ref:
            return ["device:any", f"device:{self.device_ref}"]
        return None


class DeviceClaimConflict(BaseModel):
    requested_device_ref: str | None = None
    blocking_operation_id: str
    blocking_kind: OperationKind
    blocking_status: OperationStatus
    blocking_device_ref: str | None = None
    reason: str


class CleanupClaimResult(BaseModel):
    operation_id: str | None = None
    resource_key: str
    action: Literal["released_missing_owner", "released_terminal_owner", "released_dead_owner", "released_start_timeout"]
    detail: str
