from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from munk.services.optimization.request_models import OptimizeCaseOperationResult


class OptimizeCaseOperationResultPayload(BaseModel):
    summary: str
    patched_fields: list[str]
    applied: bool = False
    skip_reason: str | None = None
    confidence: float | None = None
    field_diffs: list[dict[str, object]]
    field_diff_artifact_path: str
    optimization_result_path: str
    optimization_request_path: str
    optimization_diagnostics_path: str
    artifacts: dict[str, str]

    def to_command_data(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"artifacts"})


def build_optimize_case_operation_result_payload(
    result: OptimizeCaseOperationResult,
) -> OptimizeCaseOperationResultPayload:
    return OptimizeCaseOperationResultPayload(
        summary=result.summary,
        patched_fields=list(result.patched_fields),
        applied=result.applied,
        skip_reason=result.skip_reason,
        confidence=result.confidence,
        field_diffs=list(result.field_diffs),
        field_diff_artifact_path=str(result.field_diffs_path),
        optimization_result_path=str(result.result_path),
        optimization_request_path=str(result.request_path),
        optimization_diagnostics_path=str(result.diagnostics_path),
        artifacts=dict(result.artifacts),
    )


def parse_optimize_case_operation_result_payload(payload: object) -> OptimizeCaseOperationResultPayload | None:
    if not isinstance(payload, dict):
        return None
    try:
        return OptimizeCaseOperationResultPayload.model_validate(payload)
    except ValidationError:
        return None
