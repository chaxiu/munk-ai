from __future__ import annotations

from munk.testing import TestCase
from pydantic import BaseModel, Field

from munk.orchestration import AgentDecision, StateDelta
from munk.planning.models import RequirementPlan


def empty_cases() -> list[TestCase]:
    return []


class PlanWorkflowInput(BaseModel):
    cases: list[TestCase] = Field(default_factory=empty_cases)


class PlanOrchestrationResult(BaseModel):
    plan: RequirementPlan
    workflow_input: PlanWorkflowInput
    decision: AgentDecision = Field(
        default_factory=lambda: AgentDecision(
            decision_type="continue",
            target_step="runner",
            reason="plan completed and emitted case workflow inputs",
        )
    )
    state_delta: StateDelta = Field(
        default_factory=lambda: StateDelta(
            status="ready",
            next_step="runner",
            reason="plan cases are ready for execution",
        )
    )
