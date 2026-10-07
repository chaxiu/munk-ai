from __future__ import annotations

from pydantic import BaseModel, Field

from munk.judging.models import JudgeResult, JudgeVerdict
from munk.orchestration import AgentDecision, EventHistoryEntry, StateDelta, WorkflowStepName
from munk.token_usage import TokenUsage


def empty_strings() -> list[str]:
    return []


def empty_history_entries() -> list[EventHistoryEntry]:
    return []


def empty_artifacts() -> dict[str, str]:
    return {}


class JudgeOptimizationTrigger(BaseModel):
    needs_optimization: bool = False
    optimization_fields: list[str] = Field(default_factory=empty_strings)
    optimization_reason: str | None = None
    optimization_confidence: float | None = None


class JudgeRetryGuidance(BaseModel):
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    retry_reason: str | None = None


class JudgeOrchestrationResult(BaseModel):
    judge_result: JudgeResult
    decision: AgentDecision
    state_delta: StateDelta
    retry_guidance: JudgeRetryGuidance = Field(default_factory=JudgeRetryGuidance)
    optimization_trigger: JudgeOptimizationTrigger = Field(default_factory=JudgeOptimizationTrigger)
    artifacts: dict[str, str] = Field(default_factory=empty_artifacts)
    history_entries: list[EventHistoryEntry] = Field(default_factory=empty_history_entries)
    token_usage: TokenUsage | None = None


def build_default_judge_decision(
    *,
    verdict: JudgeVerdict,
    reason: str,
    supplemental_context: list[str] | None = None,
    next_step: WorkflowStepName | None = None,
) -> AgentDecision:
    if verdict == "passed":
        return AgentDecision(
            decision_type="finish",
            reason=reason,
            summary="judge accepted the case result",
        )
    if next_step is None:
        return AgentDecision(
            decision_type="finish",
            reason=reason,
            summary="judge produced a terminal verdict",
            supplemental_context=list(supplemental_context or []),
        )
    return AgentDecision(
        decision_type="retry_with_context",
        target_step=next_step,
        reason=reason,
        summary="judge requested another runner attempt",
        supplemental_context=list(supplemental_context or []),
    )
