from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from munk.app import AppTarget
from munk.orchestration import AgentDecision, EventHistoryEntry, StateDelta
from munk.running.models import RuntimeOverrideValue
from munk.testing import TestCase
from munk.token_usage import TokenUsage


def empty_strings() -> list[str]:
    return []


def empty_runtime_overrides() -> dict[str, RuntimeOverrideValue]:
    return {}


def empty_history_entries() -> list[EventHistoryEntry]:
    return []


def empty_path_map() -> dict[str, str]:
    return {}


class RunnerExecutionContext(BaseModel):
    attempt_index: int = 0
    supplemental_context: list[str] = Field(default_factory=empty_strings)
    retry_reason: str | None = None
    retry_handoff_message: str | None = None


class RunnerOrchestrationRequest(BaseModel):
    app_id: str
    plan_id: str
    case_id: str
    case: TestCase
    app_target: AppTarget
    device_ref: str | None = None
    assets_root: Path | None = None
    artifact_path: Path | None = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=empty_runtime_overrides)
    execution_context: RunnerExecutionContext = Field(default_factory=RunnerExecutionContext)


class RunnerOrchestrationResult(BaseModel):
    status: str
    stop_reason: str | None = None
    steps_completed: int = 0
    run_dir: Path
    error_message: str | None = None
    error_type: str | None = None
    last_action_summary: str | None = None
    last_target_identity: str | None = None
    last_surface_identity: str | None = None
    artifacts: dict[str, str] = Field(default_factory=empty_path_map)
    history_entries: list[EventHistoryEntry] = Field(default_factory=empty_history_entries)
    state_delta: StateDelta = Field(default_factory=StateDelta)
    token_usage: TokenUsage | None = None
    decision: AgentDecision = Field(
        default_factory=lambda: AgentDecision(
            decision_type="continue",
            target_step="judge",
            reason="runner execution completed",
        )
    )
