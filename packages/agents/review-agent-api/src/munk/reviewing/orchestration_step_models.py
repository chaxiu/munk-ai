from __future__ import annotations

from pydantic import BaseModel, Field

from munk.orchestration import AgentDecision, StateDelta
from munk.reviewing.models import ReviewResult
from munk.reviewing.orchestration_models import ReviewOrchestrationContract


def empty_strings() -> list[str]:
    return []


class ReviewInputEnrichment(BaseModel):
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    recommended_checks: list[str] = Field(default_factory=empty_strings)


class ReviewOrchestrationResult(BaseModel):
    review_result: ReviewResult
    orchestration_contract: ReviewOrchestrationContract
    decision: AgentDecision = Field(
        default_factory=lambda: AgentDecision(
            decision_type="continue",
            target_step="plan",
            reason="review completed and produced orchestration hints",
        )
    )
    state_delta: StateDelta = Field(
        default_factory=lambda: StateDelta(
            status="ready",
            next_step="plan",
            reason="review artifacts are ready for downstream planning",
        )
    )
    input_enrichment: ReviewInputEnrichment = Field(default_factory=ReviewInputEnrichment)
