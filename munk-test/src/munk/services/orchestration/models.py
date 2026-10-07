from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from munk.app import AppTarget
from munk.orchestration import AgentDecision, CaseWorkflowState, EventHistory, OrchestrationPolicy
from munk.testing import TestCase
from munk.token_usage import TokenUsage


def empty_artifacts() -> dict[str, str]:
    return {}


def empty_runtime_overrides() -> dict[str, str | int | float | bool]:
    return {}


def empty_attempts() -> list["CaseAttemptRecord"]:
    return []


class CaseOrchestrationRequest(BaseModel):
    app_id: str
    plan_id: str
    case: TestCase
    app_target: AppTarget
    device_ref: str | None = None
    artifact_path: Path | None = None
    assets_root: Path | None = None
    runtime_overrides: dict[str, str | int | float | bool] = Field(default_factory=empty_runtime_overrides)
    policy: OrchestrationPolicy = Field(default_factory=OrchestrationPolicy)


class CaseAttemptRecord(BaseModel):
    attempt_index: int
    runner: Any
    judge: Any
    retry_handoff_message: str | None = None
    runner_usage: TokenUsage | None = None
    judge_usage: TokenUsage | None = None
    total_usage: TokenUsage | None = None


class CaseOrchestrationResult(BaseModel):
    request: CaseOrchestrationRequest
    state: CaseWorkflowState
    final_decision: AgentDecision
    history: EventHistory = Field(default_factory=EventHistory)
    attempts: list[CaseAttemptRecord] = Field(default_factory=empty_attempts)
    artifacts: dict[str, str] = Field(default_factory=empty_artifacts)
    token_usage: TokenUsage | None = None
