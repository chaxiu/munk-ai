from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WorkflowStartedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_id: str | None = None


class WorkflowAttemptStartedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    attempt_index: int | None = None
    case_id: str | None = None
    retry_count: int | None = None


class WorkflowAttemptFinishedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    attempt_index: int | None = None
    verdict: str | None = None
    decision_type: str | None = None


class WorkflowRetryScheduledEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    attempt_index: int | None = None
    retry_count: int | None = None
    retry_attempt: int | None = None
    reason: str | None = None
    retry_reason: str | None = None
    supplemental_context: list[str] | None = None
    focus_items: list[str] | None = None
    handoff_summary: str | None = None


class WorkflowFinishedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    decision_type: str | None = None
    verdict: str | None = None
    attempt_count: int | None = None


class JudgeDecisionEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    verdict: str | None = None
    reason: str | None = None
    decision_type: str | None = None
