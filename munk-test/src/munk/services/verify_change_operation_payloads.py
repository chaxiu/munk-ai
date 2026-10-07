from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from munk.execution.models import ExecutedPlanResult, GeneratedPlanResult, PhasedOperationResult


class VerifyChangeOperationResultPayload(BaseModel):
    app_id: str
    plan_id: str
    phase: str
    plan_result: GeneratedPlanResult
    execution_result: ExecutedPlanResult | None = None
    artifacts: dict[str, str]

    def to_command_data(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"artifacts"})


def build_verify_change_operation_result_payload(
    result: PhasedOperationResult,
    *,
    artifacts: dict[str, str],
) -> VerifyChangeOperationResultPayload:
    return VerifyChangeOperationResultPayload(
        app_id=result.app_id,
        plan_id=result.plan_id,
        phase=result.phase,
        plan_result=result.plan_result,
        execution_result=result.execution_result,
        artifacts=dict(artifacts),
    )
