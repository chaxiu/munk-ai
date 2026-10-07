from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from munk.services.operations.models import OperationKind, OperationStatus, VerificationVerdict

DiagnosticsFailureCategory = Literal[
    "contract_error",
    "retrieval_error",
    "model_error",
    "planning_error",
    "protocol_error",
    "execution_error",
    "artifact_error",
    "unknown_error",
]

OPERATION_DIAGNOSTICS_SCHEMA_VERSION = "phase7e.operation_diagnostics.v1"


def empty_strings() -> list[str]:
    return []


def empty_string_map() -> dict[str, str]:
    return {}


def empty_optional_string_map() -> dict[str, str | None]:
    return {}


def empty_artifact_checks() -> list["ArtifactCheck"]:
    return []


class ArtifactCheck(BaseModel):
    artifact_id: str
    path: Path | None = None
    required: bool = True
    exists: bool = False
    valid: bool = False
    summary: str | None = None


class OperationDiagnostics(BaseModel):
    schema_version: str = OPERATION_DIAGNOSTICS_SCHEMA_VERSION
    operation_id: str | None = None
    operation_kind: OperationKind | None = None
    app_id: str | None = None
    status: OperationStatus | None = None
    verification_verdict: VerificationVerdict = None
    started_at: str
    finished_at: str
    duration_ms: int
    provider: str | None = None
    model: str | None = None
    role_models: dict[str, str] = Field(default_factory=empty_string_map)
    config_fingerprint: str | None = None
    device_ref: str | None = None
    entry_identity: str | None = None
    warning_summary: list[str] = Field(default_factory=empty_strings)
    retry_count: int = 0
    fallback_count: int = 0
    failure_category: DiagnosticsFailureCategory | None = None
    failure_stage: str | None = None
    failure_message: str | None = None
    artifact_checks: list[ArtifactCheck] = Field(default_factory=empty_artifact_checks)
    contract_versions: dict[str, str] = Field(default_factory=empty_string_map)
    linked_operation_ids: dict[str, str | None] = Field(default_factory=empty_optional_string_map)
