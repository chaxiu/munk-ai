from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Annotated, Literal, TypeAlias, TypeGuard

from pydantic import BaseModel, ConfigDict, Field, model_validator

from munk.agent_runtime.events import AgentEventSink
from munk.testing import AiGuidance
from munk.token_usage import TokenUsage

JudgeVerdict = Literal["passed", "failed", "inconclusive"]
JudgeEvidenceSource = Literal["execution", "event", "artifact"]
JUDGE_RESULT_SCHEMA_VERSION = "phase7e.judge_result.v1"
JsonValue: TypeAlias = Any
JsonObject: TypeAlias = dict[str, Any]


def empty_strings() -> list[str]:
    return []


def empty_events() -> list["JudgeEventRecord"]:
    return []


def empty_evidence() -> list["JudgeEvidence"]:
    return []


def empty_json_object() -> JsonObject:
    return {}


def empty_tool_calls() -> list[str]:
    return []


def empty_runner_history_entries() -> list["JudgeRunnerHistoryEntry"]:
    return []


def empty_runner_memory_entries() -> list["JudgeRunnerMemoryEntry"]:
    return []


def empty_runtime_log_entries() -> list["JudgeRuntimeLogEntry"]:
    return []


def empty_focus_hits() -> list["JudgeFocusHit"]:
    return []


def empty_json_objects() -> list[JsonObject]:
    return []


def empty_json_values() -> list[JsonValue]:
    return []


def empty_ints() -> list[int]:
    return []


def empty_compact_ui_nodes() -> list["JudgeCompactUiNode"]:
    return []


def empty_screen_node_changes() -> list["JudgeScreenNodeChange"]:
    return []


class JudgeContractModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class JudgeEventRecord(JudgeContractModel):
    event_type: str
    timestamp: str
    message: str | None = None
    data: JsonObject = Field(default_factory=empty_json_object)


class JudgeExecutionSummary(JudgeContractModel):
    status: Literal["completed", "failed", "incomplete"]
    stop_reason: str | None = None
    steps_completed: int = 0
    error_message: str | None = None
    error_type: str | None = None
    last_action_summary: str | None = None
    last_target_identity: str | None = None
    last_surface_identity: str | None = None


class JudgeEvidenceBundle(JudgeContractModel):
    runner_history_path: Path | None = None
    runner_memory_path: Path | None = None
    runner_issues_path: Path | None = None
    decision_trace_path: Path | None = None
    runtime_logs_path: Path | None = None
    observation_frames_path: Path | None = None
    observation_diffs_path: Path | None = None
    observation_tree_path: Path | None = None
    raw_screenshots_path: Path | None = None
    annotated_screenshots_path: Path | None = None
    llm_transcript_path: Path | None = None
    artifact_manifest_path: Path | None = None


class JudgeRequest(JudgeContractModel):
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


class JudgeExecutionEvidencePayload(JudgeContractModel):
    status: Literal["completed", "failed", "incomplete"]
    stop_reason: str | None = None
    steps_completed: int = 0
    error_message: str | None = None
    error_type: str | None = None
    last_action_summary: str | None = None
    last_target_identity: str | None = None
    last_surface_identity: str | None = None


class JudgeEventEvidencePayload(JudgeContractModel):
    event_type: str
    timestamp: str
    message: str | None = None
    data: JsonObject = Field(default_factory=empty_json_object)


class JudgeDecisionTraceEvidencePayload(JudgeContractModel):
    path: str | None = None
    step_index: int | None = None
    attempt_index: int | None = None
    decision: str | None = None
    action: str | None = None
    summary: str | None = None
    result_summary: str | None = None
    tool_name: str | None = None
    tool_names: list[str] = Field(default_factory=empty_strings)
    arguments: JsonObject = Field(default_factory=empty_json_object)
    will_retry: bool | None = None
    seeded_element_count: int | None = None
    ui_elements_summary: str | None = None
    raw_line: str | None = None


class JudgeRunnerHistoryEntry(JudgeContractModel):
    step_index: int | None = None
    action_type: str | None = None
    summary: str | None = None
    outcome_summary: str | None = None
    record: JsonObject | None = None


class JudgeRunnerHistoryEvidencePayload(JudgeContractModel):
    path: str | None = None
    latest_step_index: int | None = None
    entries: list[JudgeRunnerHistoryEntry] = Field(default_factory=empty_runner_history_entries)
    excerpt: list[JudgeRunnerHistoryEntry] = Field(default_factory=empty_runner_history_entries)


class JudgeRunnerMemoryEntry(JudgeContractModel):
    key: str | None = None
    summary: str | None = None
    value: JsonValue = None
    updated_step_index: int | None = None
    timestamp: str | None = None


class JudgeRunnerMemoryEvidencePayload(JudgeContractModel):
    path: str | None = None
    entries: list[JudgeRunnerMemoryEntry] = Field(default_factory=empty_runner_memory_entries)
    excerpt: list[JudgeRunnerMemoryEntry] = Field(default_factory=empty_runner_memory_entries)


class JudgeRunnerIssueRecord(JudgeContractModel):
    step_index: int | None = None
    severity: str | None = None
    summary: str | None = None
    record: JsonObject | None = None


class JudgeRunnerIssueEvidencePayload(JudgeContractModel):
    path: str | None = None
    issue: JudgeRunnerIssueRecord


class JudgeRuntimeLogEntry(JudgeContractModel):
    step_index: int | None = None
    source: str | None = None
    surface_identity: str | None = None
    message: str


class JudgeRuntimeErrorLogEvidencePayload(JudgeContractModel):
    path: str | None = None
    excerpt: str
    step_indexes: list[int] = Field(default_factory=list)
    entries: list[JudgeRuntimeLogEntry] = Field(default_factory=empty_runtime_log_entries)


class JudgeFocusHit(JudgeContractModel):
    node_id: str | None = None
    label: str | None = None
    score: int | None = None


class JudgeCompactUiNodeState(JudgeContractModel):
    clickable: bool | None = None
    enabled: bool | None = None
    checkable: bool | None = None
    checked: bool | None = None
    focused: bool | None = None
    selected: bool | None = None
    scrollable: bool | None = None


class JudgeCompactUiNode(JudgeContractModel):
    node_id: str | None = None
    stable_key: str | None = None
    parent_node_id: str | None = None
    class_name: str | None = None
    resource_id: str | None = None
    text: str | None = None
    content_desc: str | None = None
    bounds: list[int] = Field(default_factory=empty_ints)
    state: JudgeCompactUiNodeState = Field(default_factory=JudgeCompactUiNodeState)
    role: str | None = None
    visual_ids: list[str] = Field(default_factory=empty_strings)


class JudgeCompactUiTree(JudgeContractModel):
    node_count: int = 0
    focus_term_count: int | None = None
    nodes: list[JudgeCompactUiNode] = Field(default_factory=empty_compact_ui_nodes)


class JudgeScreenNodeChange(JudgeContractModel):
    change_type: str | None = None
    stable_key: str | None = None
    label: str | None = None


class JudgeScreenFrameEvidencePayload(JudgeContractModel):
    path: str
    step_index: int
    package: str | None = None
    tree_available: bool | None = None
    tree_summary: str | None = None
    compact_tree: JudgeCompactUiTree = Field(default_factory=JudgeCompactUiTree)
    focus_hits: list[JudgeFocusHit] = Field(default_factory=empty_focus_hits)


class JudgeScreenDiffEvidencePayload(JudgeContractModel):
    path: str
    step_index: int
    summary: str | None = None
    appeared_labels: list[str] = Field(default_factory=empty_strings)
    updated_labels: list[str] = Field(default_factory=empty_strings)
    disappeared_labels: list[str] = Field(default_factory=empty_strings)
    linked_visual_changes: list[str] = Field(default_factory=empty_strings)
    appeared_nodes: list[JudgeScreenNodeChange] = Field(default_factory=empty_screen_node_changes)
    updated_nodes: list[JudgeScreenNodeChange] = Field(default_factory=empty_screen_node_changes)
    disappeared_nodes: list[JudgeScreenNodeChange] = Field(default_factory=empty_screen_node_changes)


class JudgeScreenshotRef(JudgeContractModel):
    screenshot_id: str
    step_index: int
    kind: Literal["raw", "annotated"]
    path: str
    package: str | None = None
    action_summary: str | None = None
    observation_summary: str | None = None
    tree_evidence_id: str | None = None
    diff_evidence_id: str | None = None


class JudgeScreenshotEvidencePayload(JudgeScreenshotRef):
    pass


class JudgeEvidenceBase(JudgeContractModel):
    evidence_id: str
    kind: str
    source: JudgeEvidenceSource
    summary: str


class JudgeExecutionEvidence(JudgeEvidenceBase):
    kind: Literal["execution_outcome"] = "execution_outcome"
    source: Literal["execution"] = "execution"
    payload: JudgeExecutionEvidencePayload


class JudgeEventEvidence(JudgeEvidenceBase):
    kind: Literal["event"] = "event"
    source: Literal["event"] = "event"
    payload: JudgeEventEvidencePayload


class JudgeDecisionTraceEvidence(JudgeEvidenceBase):
    kind: Literal["decision_trace"] = "decision_trace"
    source: Literal["artifact"] = "artifact"
    payload: JudgeDecisionTraceEvidencePayload


class JudgeRunnerHistoryEvidence(JudgeEvidenceBase):
    kind: Literal["runner_history"] = "runner_history"
    source: Literal["artifact"] = "artifact"
    payload: JudgeRunnerHistoryEvidencePayload


class JudgeRunnerMemoryEvidence(JudgeEvidenceBase):
    kind: Literal["runner_memory"] = "runner_memory"
    source: Literal["artifact"] = "artifact"
    payload: JudgeRunnerMemoryEvidencePayload


class JudgeRunnerIssueEvidence(JudgeEvidenceBase):
    kind: Literal["runner_issue"] = "runner_issue"
    source: Literal["artifact"] = "artifact"
    payload: JudgeRunnerIssueEvidencePayload


class JudgeRuntimeErrorLogEvidence(JudgeEvidenceBase):
    kind: Literal["runtime_error_log"] = "runtime_error_log"
    source: Literal["artifact"] = "artifact"
    payload: JudgeRuntimeErrorLogEvidencePayload


class JudgeScreenFrameEvidence(JudgeEvidenceBase):
    kind: Literal["screen_frame"] = "screen_frame"
    source: Literal["artifact"] = "artifact"
    payload: JudgeScreenFrameEvidencePayload


class JudgeScreenDiffEvidence(JudgeEvidenceBase):
    kind: Literal["screen_diff"] = "screen_diff"
    source: Literal["artifact"] = "artifact"
    payload: JudgeScreenDiffEvidencePayload


class JudgeScreenshotEvidence(JudgeEvidenceBase):
    kind: Literal["screenshot"] = "screenshot"
    source: Literal["artifact"] = "artifact"
    payload: JudgeScreenshotEvidencePayload


JudgeEvidence: TypeAlias = Annotated[
    JudgeExecutionEvidence
    | JudgeEventEvidence
    | JudgeDecisionTraceEvidence
    | JudgeRunnerHistoryEvidence
    | JudgeRunnerMemoryEvidence
    | JudgeRunnerIssueEvidence
    | JudgeRuntimeErrorLogEvidence
    | JudgeScreenFrameEvidence
    | JudgeScreenDiffEvidence
    | JudgeScreenshotEvidence,
    Field(discriminator="kind"),
]


def is_execution_evidence(item: JudgeEvidence) -> TypeGuard[JudgeExecutionEvidence]:
    return item.kind == "execution_outcome"


def is_event_evidence(item: JudgeEvidence) -> TypeGuard[JudgeEventEvidence]:
    return item.kind == "event"


def is_decision_trace_evidence(item: JudgeEvidence) -> TypeGuard[JudgeDecisionTraceEvidence]:
    return item.kind == "decision_trace"


def is_runner_history_evidence(item: JudgeEvidence) -> TypeGuard[JudgeRunnerHistoryEvidence]:
    return item.kind == "runner_history"


def is_runner_memory_evidence(item: JudgeEvidence) -> TypeGuard[JudgeRunnerMemoryEvidence]:
    return item.kind == "runner_memory"


def is_runner_issue_evidence(item: JudgeEvidence) -> TypeGuard[JudgeRunnerIssueEvidence]:
    return item.kind == "runner_issue"


def is_runtime_error_log_evidence(item: JudgeEvidence) -> TypeGuard[JudgeRuntimeErrorLogEvidence]:
    return item.kind == "runtime_error_log"


def is_screen_frame_evidence(item: JudgeEvidence) -> TypeGuard[JudgeScreenFrameEvidence]:
    return item.kind == "screen_frame"


def is_screen_diff_evidence(item: JudgeEvidence) -> TypeGuard[JudgeScreenDiffEvidence]:
    return item.kind == "screen_diff"


def is_screenshot_evidence(item: JudgeEvidence) -> TypeGuard[JudgeScreenshotEvidence]:
    return item.kind == "screenshot"


class JudgeRuntimeResultData(JudgeContractModel):
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


class JudgeRuntimeOutput(JudgeContractModel):
    result_data: JudgeRuntimeResultData
    started_at: str
    duration_ms: int
    warning_summary: list[str] = Field(default_factory=empty_strings)
    tool_calls: list[str] = Field(default_factory=empty_tool_calls)
    token_usage: TokenUsage | None = None


class JudgeResult(JudgeContractModel):
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
    attempt_index: int = 0
    progress: AgentEventSink | None = None
