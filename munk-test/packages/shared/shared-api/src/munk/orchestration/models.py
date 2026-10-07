from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from munk.testing import TestCase

WorkflowStepName = Literal["review", "plan", "runner", "judge"]
WorkflowStatus = Literal[
    "pending",
    "ready",
    "running",
    "needs_retry",
    "escalated",
    "finished",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_strings() -> list[str]:
    return []


def empty_string_map() -> dict[str, str]:
    return {}


def empty_object_map() -> dict[str, object]:
    return {}


def empty_history_entries() -> list["EventHistoryEntry"]:
    return []


def empty_steps() -> list["WorkflowStep"]:
    return []


class StateDelta(BaseModel):
    status: WorkflowStatus | None = None
    next_step: WorkflowStepName | None = None
    retry_count_increment: int = 0
    reason: str | None = None
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    metadata: dict[str, object] = Field(default_factory=empty_object_map)


class AgentDecision(BaseModel):
    decision_type: Literal["continue", "retry_with_context", "escalate", "finish"]
    target_step: WorkflowStepName | None = None
    reason: str
    summary: str | None = None
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    metadata: dict[str, object] = Field(default_factory=empty_object_map)


class EventHistoryEntry(BaseModel):
    event_type: str
    timestamp: str = Field(default_factory=utc_now_iso)
    step: WorkflowStepName | None = None
    message: str | None = None
    payload: dict[str, object] = Field(default_factory=empty_object_map)


class EventHistory(BaseModel):
    entries: list[EventHistoryEntry] = Field(default_factory=empty_history_entries)


class OrchestrationArtifactIndex(BaseModel):
    artifacts: dict[str, str] = Field(default_factory=empty_string_map)


class CaseWorkflowState(BaseModel):
    app_id: str
    plan_id: str
    case: TestCase
    status: WorkflowStatus = "pending"
    current_step: WorkflowStepName | None = None
    last_completed_step: WorkflowStepName | None = None
    retry_count: int = 0
    last_verdict: str | None = None
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    artifact_index: OrchestrationArtifactIndex = Field(default_factory=OrchestrationArtifactIndex)
    metadata: dict[str, object] = Field(default_factory=empty_object_map)


class StepRequest(BaseModel):
    app_id: str
    plan_id: str
    case: TestCase
    state: CaseWorkflowState
    step: WorkflowStepName


class StepResult(BaseModel):
    step: WorkflowStepName
    state_delta: StateDelta = Field(default_factory=StateDelta)
    decision: AgentDecision
    artifacts: dict[str, str] = Field(default_factory=empty_string_map)
    history_entries: list[EventHistoryEntry] = Field(default_factory=empty_history_entries)
    metadata: dict[str, object] = Field(default_factory=empty_object_map)


class WorkflowStep(BaseModel):
    step: WorkflowStepName
    request: StepRequest
    result: StepResult | None = None


class OrchestrationPolicy(BaseModel):
    max_retry_attempts: int = Field(default=0, ge=0)
    retry_on_inconclusive: bool = True
    retry_on_failed: bool = True
    escalate_after_max_attempts: bool = False
    terminal_decisions: list[str] = Field(default_factory=lambda: ["finish", "escalate"])
    allowed_steps: list[WorkflowStepName] = Field(default_factory=lambda: ["review", "plan", "runner", "judge"])
