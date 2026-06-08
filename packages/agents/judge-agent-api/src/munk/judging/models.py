from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from munk.agent_runtime.events import AgentEventSink
from munk.testing import AiGuidance
from munk.token_usage import TokenUsage

JudgeVerdict = Literal["passed", "failed", "inconclusive"]
JudgeEvidenceSource = Literal["execution", "event", "artifact"]
JUDGE_RESULT_SCHEMA_VERSION = "phase7e.judge_result.v1"


def empty_strings() -> list[str]:
    return []


def empty_events() -> list["JudgeEventRecord"]:
    return []


def empty_evidence() -> list["JudgeEvidence"]:
    return []


def empty_payload() -> dict[str, Any]:
    return {}


def empty_tool_calls() -> list[str]:
    return []


class JudgeEventRecord(BaseModel):
    event_type: str
    timestamp: str
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=empty_payload)


class JudgeExecutionSummary(BaseModel):
    status: Literal["completed", "failed", "incomplete"]
    stop_reason: str | None = None
    steps_completed: int = 0
    error_message: str | None = None
    error_type: str | None = None
    last_action_summary: str | None = None
    last_target_identity: str | None = None
    last_surface_identity: str | None = None


class JudgeEvidenceBundle(BaseModel):
    runner_history_path: Path | None = None
    runner_memory_path: Path | None = None
    decision_trace_path: Path | None = None
    runtime_logs_path: Path | None = None
    observation_frames_path: Path | None = None
    observation_diffs_path: Path | None = None
    observation_tree_path: Path | None = None
    raw_screenshots_path: Path | None = None
    annotated_screenshots_path: Path | None = None
    llm_transcript_path: Path | None = None
    artifact_manifest_path: Path | None = None


class JudgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    plan_id: str
    case_id: str
    case_title: str
    intent: str
    preconditions: list[str] = Field(default_factory=empty_strings)
    expected: list[str] = Field(default_factory=empty_strings)
    runner_goal: str
    ai_guidance: AiGuidance | None = None
    execution: JudgeExecutionSummary
    events: list[JudgeEventRecord] = Field(default_factory=empty_events)
    evidence_bundle: JudgeEvidenceBundle = Field(default_factory=JudgeEvidenceBundle)

    @model_validator(mode="after")
    def validate_request(self) -> "JudgeRequest":
        self.case_title = self.case_title.strip()
        self.intent = self.intent.strip()
        self.runner_goal = self.runner_goal.strip()
        self.preconditions = [item.strip() for item in self.preconditions if item.strip()]
        self.expected = [item.strip() for item in self.expected if item.strip()]
        if not self.case_title:
            raise ValueError("case_title must not be empty")
        if not self.intent:
            raise ValueError("intent must not be empty")
        if not self.runner_goal:
            raise ValueError("runner_goal must not be empty")
        if not self.expected:
            raise ValueError("expected must not be empty")
        return self


class JudgeEvidence(BaseModel):
    evidence_id: str
    kind: str
    source: JudgeEvidenceSource
    summary: str
    payload: dict[str, Any] = Field(default_factory=empty_payload)


class JudgeRuntimeResultData(BaseModel):
    verdict: JudgeVerdict
    summary: str
    reason: str
    failure_hypothesis: str | None = None
    confidence: float | None = None
    missing_evidence: list[str] = Field(default_factory=empty_strings)
    supporting_evidence_ids: list[str] = Field(default_factory=empty_strings)
    evidence: list[JudgeEvidence] = Field(default_factory=empty_evidence)
    needs_optimization: bool = False
    optimization_fields: list[str] = Field(default_factory=empty_strings)
    optimization_reason: str | None = None
    optimization_confidence: float | None = None


class JudgeRuntimeOutput(BaseModel):
    result_data: JudgeRuntimeResultData
    started_at: str
    duration_ms: int
    warning_summary: list[str] = Field(default_factory=empty_strings)
    tool_calls: list[str] = Field(default_factory=empty_tool_calls)
    token_usage: TokenUsage | None = None


class JudgeResult(BaseModel):
    schema_version: str = JUDGE_RESULT_SCHEMA_VERSION
    app_id: str
    plan_id: str
    case_id: str
    operation_id: str | None = None
    verdict: JudgeVerdict
    summary: str
    reason: str
    failure_hypothesis: str | None = None
    confidence: float | None = None
    missing_evidence: list[str] = Field(default_factory=empty_strings)
    supporting_evidence_ids: list[str] = Field(default_factory=empty_strings)
    evidence: list[JudgeEvidence] = Field(default_factory=empty_evidence)
    needs_optimization: bool = False
    optimization_fields: list[str] = Field(default_factory=empty_strings)
    optimization_reason: str | None = None
    optimization_confidence: float | None = None
    judge_request_path: Path
    judge_result_path: Path
    diagnostics_path: Path | None = None
    llm_transcript_path: Path | None = None
    token_usage: TokenUsage | None = None


@dataclass(frozen=True)
class JudgeManagedPaths:
    root_dir: Path
    judge_request_path: Path
    judge_prompt_path: Path
    tool_calls_path: Path
    evidence_selection_path: Path
    llm_transcript_path: Path | None


@dataclass(frozen=True)
class JudgeRuntimeContext:
    operation_id: str | None
    managed_paths: JudgeManagedPaths
    progress: AgentEventSink | None = None
