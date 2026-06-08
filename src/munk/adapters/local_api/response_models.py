from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from munk.adapters.local_api.config_models import (
    GeminiSectionEditor,
    OpenAICompatibleSectionEditor,
    OrchestrationConfigEditor,
    ProxyConfigEditor,
    RuntimeConfigEditor,
    SettingsAgentsEditor,
)
from munk.adapters.local_api.plan_models import TestCasePayload
from munk.adapters.shared.payload_models import AttemptTokenUsageData, TokenUsageData
from munk.recording import (
    ObservationSnapshot,
    RecordedInputEvent,
    RecordingAnalysisResult,
    RecordingCaseExport,
    RecordingReplayResult,
    RecordingSession,
    TimelineEntry,
)
from munk.services.artifact_manifest_models import ReproductionEntry, UpstreamReviewArtifacts

PayloadT = TypeVar("PayloadT")


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    command: str
    error: ApiError


class SuccessResponse(BaseModel, Generic[PayloadT]):
    ok: Literal[True] = True
    command: str
    data: PayloadT
    artifacts: dict[str, str] | None = None


class OperationSubmissionData(BaseModel):
    operation_id: str
    status: str
    verification_verdict: str | None = None
    app_id: str | None = None
    plan_id: str | None = None
    plan_name: str | None = None
    phase: str | None = None
    plan_result: dict[str, Any] | None = None
    execution_result: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class PlanImportData(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    source: str
    version: str
    case_count: int = 0
    plan_path: str


class RunArtifactItemData(BaseModel):
    artifact_id: str
    role: str
    kind: str
    scope: str
    media_type: str | None = None
    exists: bool = True
    label: str
    case_id: str | None = None
    path: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_url: str | None = None
    download_url: str | None = None


class RunArtifactGroupData(BaseModel):
    group_id: str
    title: str
    items: list[RunArtifactItemData] = Field(default_factory=list)


class CaseRunArtifactSummaryData(BaseModel):
    case_id: str
    title: str
    operation_id: str | None = None
    verdict: str
    execution_status: str
    run_dir: str
    token_usage: TokenUsageData | None = None


class OperationArtifactsData(BaseModel):
    operation_id: str
    run_type: str | None = None
    title: str | None = None
    platform: str | None = None
    phase: str | None = None
    target_label: str | None = None
    source_recording_id: str | None = None
    status: str
    verification_verdict: str | None = None
    device_ref: str | None = None
    resource_scope: str | None = None
    conflict_reason: str | None = None
    artifact_manifest_path: str | None = None
    repro_dir: str | None = None
    primary_artifact_ids: list[str] = Field(default_factory=list)
    artifact_manifest_version: int | None = None
    schema_versions: dict[str, str] = Field(default_factory=dict)
    diagnostics_path: str | None = None
    duration_ms: int | None = None
    failure_category: str | None = None
    warning_summary: list[str] = Field(default_factory=list)
    case_runs: list[CaseRunArtifactSummaryData] = Field(default_factory=list)
    reproduction_entries: list[ReproductionEntry] = Field(default_factory=list)
    upstream_review: UpstreamReviewArtifacts | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    primary_artifacts: list[RunArtifactItemData] = Field(default_factory=list)
    artifact_groups: list[RunArtifactGroupData] = Field(default_factory=list)
    token_usage: TokenUsageData | None = None
    planning_usage: TokenUsageData | None = None
    execution_usage: TokenUsageData | None = None
    attempt_usages: list[AttemptTokenUsageData] = Field(default_factory=list)


class RunArtifactContentData(BaseModel):
    artifact_id: str
    media_type: str | None = None
    encoding: str = "utf-8"
    truncated: bool = False
    content: str


class RunArtifactChildItemData(BaseModel):
    child_id: str
    name: str
    path: str
    media_type: str | None = None
    size_bytes: int | None = None
    content_url: str | None = None


class RunArtifactChildrenData(BaseModel):
    operation_id: str
    artifact_id: str
    title: str
    kind: str
    items: list[RunArtifactChildItemData] = Field(default_factory=list)


class CancelOperationData(BaseModel):
    operation_id: str
    status: str
    cancel_requested: bool


class ReproduceOperationData(OperationArtifactsData):
    reproduction_entries: list[ReproductionEntry] = Field(default_factory=list)


class DeleteAppData(BaseModel):
    app_id: str


class SettingsConfigData(BaseModel):
    config_path: str
    file_exists: bool = False
    provider: str
    openai_compatible: OpenAICompatibleSectionEditor = Field(default_factory=OpenAICompatibleSectionEditor)
    gemini: GeminiSectionEditor = Field(default_factory=GeminiSectionEditor)
    agents: SettingsAgentsEditor = Field(default_factory=SettingsAgentsEditor)
    proxy: ProxyConfigEditor = Field(default_factory=ProxyConfigEditor)
    runtime: RuntimeConfigEditor = Field(default_factory=RuntimeConfigEditor)
    orchestration: OrchestrationConfigEditor = Field(default_factory=OrchestrationConfigEditor)


class CaseRewritePreviewData(BaseModel):
    case: TestCasePayload
    source_prompt: str


class CaseDeleteData(BaseModel):
    app_id: str
    plan_id: str
    case_id: str
    case_count: int = 0


class RecordingBridgeInfo(BaseModel):
    recording_id: str
    base_url: str
    ws_url: str


class RecordingCreateData(BaseModel):
    session: RecordingSession


class RecordingBeginData(BaseModel):
    session: RecordingSession
    bridge: RecordingBridgeInfo


class RecordingGetData(BaseModel):
    session: RecordingSession
    events: list[RecordedInputEvent] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)


class RecordingTapData(BaseModel):
    event: RecordedInputEvent


class RecordingInteractionData(BaseModel):
    entry: TimelineEntry


class RecordingTimelineData(BaseModel):
    timeline: list[TimelineEntry] = Field(default_factory=list)


class RecordingObservationData(BaseModel):
    observation: ObservationSnapshot


class RecordingAnalysisData(BaseModel):
    analysis: RecordingAnalysisResult
    operation: OperationSubmissionData | None = None


class RecordingExportData(BaseModel):
    analysis: RecordingAnalysisResult
    case: RecordingCaseExport
    artifacts: dict[str, str] = Field(default_factory=dict)


class RecordingReplayData(BaseModel):
    replay: RecordingReplayResult


class RecordingSessionData(BaseModel):
    session: RecordingSession
