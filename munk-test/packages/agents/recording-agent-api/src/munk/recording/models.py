from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from munk.app import AppTarget
from munk.testing import TestCase

from .errors import RecordingInteractionContractError

RecordingSessionStatus = Literal["created", "recording", "stopped", "cancelled", "failed"]
RecordingInteractionKind = Literal["click", "swipe", "input", "back"]
ForwardingKind = Literal["pointer", "input", "back"]
ForwardingStepKind = Literal[
    "pointer_down",
    "pointer_move",
    "pointer_up",
    "key_press",
    "key_down",
    "key_up",
    "text_inject",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_strings() -> list[str]:
    return []


def empty_data() -> dict[str, Any]:
    return {}


def empty_generated_files() -> dict[str, str]:
    return {}


def empty_steps() -> list["ForwardingStep"]:
    return []


def empty_entries() -> list["TimelineEntry"]:
    return []


def empty_analysis_steps() -> list["RecordingAnalysisStep"]:
    return []


def empty_warnings() -> list[str]:
    return []


def empty_tree_focus_hits() -> list["RecordingAnalysisTreeFocusHit"]:
    return []


def empty_tree_nodes() -> list["RecordingAnalysisTreeNode"]:
    return []


def empty_analysis_target_candidates() -> list["RecordingAnalysisTargetCandidate"]:
    return []


class RecordingSession(BaseModel):
    recording_id: str
    app_id: str
    app_target: AppTarget
    case_id: str | None = None
    device_ref: str | None = None
    status: RecordingSessionStatus
    asset_dir: Path
    created_at: str = Field(default_factory=now_iso)
    started_at: str | None = None
    finished_at: str | None = None
    latest_frame_seq: int | None = None
    failure_reason: str | None = None


class LiveViewFrame(BaseModel):
    recording_id: str
    seq: int
    captured_at: str = Field(default_factory=now_iso)
    image_path: Path
    width: int
    height: int
    entry_identity: str | None = None
    activity_name: str | None = None
    ui_tree_path: Path | None = None


class ObservedTapCommand(BaseModel):
    x: int
    y: int
    width: int
    height: int
    x_ratio: float | None = None
    y_ratio: float | None = None
    source: str = "scrcpy_bridge"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PointerForwardingPayload(_StrictModel):
    pointer_id: int
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    width: int
    height: int


class InputForwardingPayload(_StrictModel):
    text: str
    submit: bool = False


class BackForwardingPayload(_StrictModel):
    pass


class PointerStepPayload(_StrictModel):
    pointer_id: int
    x: int
    y: int


class TextInjectStepPayload(_StrictModel):
    text: str
    submit: bool = False


class KeyPressStepPayload(_StrictModel):
    key: str


class KeyTransitionStepPayload(_StrictModel):
    key: str


class ForwardingDeviceResult(_StrictModel):
    ok: bool = True
    error_code: str | None = None
    message: str | None = None


ForwardingAckPayload = PointerForwardingPayload | InputForwardingPayload | BackForwardingPayload
ForwardingStepPayload = (
    PointerStepPayload
    | TextInjectStepPayload
    | KeyPressStepPayload
    | KeyTransitionStepPayload
)
PayloadModelT = TypeVar("PayloadModelT", bound=BaseModel)


class ForwardingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seq: int
    step_kind: ForwardingStepKind
    payload: ForwardingStepPayload
    dispatched_at: str = Field(default_factory=now_iso)

    @model_validator(mode="before")
    @classmethod
    def _coerce_payload_model(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw_data = cast(dict[str, Any], data)
        payload = raw_data.get("payload")
        normalized: dict[str, Any] = {**raw_data}
        normalized["payload"] = _coerce_forwarding_step_payload(
            normalized.get("step_kind"), payload
        )
        return normalized


class ForwardingAck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ForwardingKind
    dispatched_at: str | None = None
    ack_at: str = Field(default_factory=now_iso)
    payload: ForwardingAckPayload = Field(default_factory=BackForwardingPayload)
    steps: list[ForwardingStep] = Field(default_factory=empty_steps)
    device_result: ForwardingDeviceResult = Field(default_factory=ForwardingDeviceResult)

    @model_validator(mode="before")
    @classmethod
    def _coerce_payload_model(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw_data = cast(dict[str, Any], data)
        payload = raw_data.get("payload")
        normalized: dict[str, Any] = {**raw_data}
        normalized["payload"] = _coerce_forwarding_ack_payload(
            normalized.get("kind"), payload
        )
        return normalized


class RecordInteractionCommand(BaseModel):
    client_command_id: str
    kind: RecordingInteractionKind
    forwarding_ack: ForwardingAck
    payload: dict[str, Any] = Field(default_factory=empty_data)
    source: str = "scrcpy_bridge"


class ForwardingEvent(BaseModel):
    forwarding_event_id: str
    recording_id: str
    client_command_id: str
    kind: ForwardingKind
    dispatched_at: str | None = None
    ack_at: str = Field(default_factory=now_iso)
    payload: ForwardingAckPayload = Field(default_factory=BackForwardingPayload)
    steps: list[ForwardingStep] = Field(default_factory=empty_steps)
    device_result: ForwardingDeviceResult = Field(default_factory=ForwardingDeviceResult)


class RecordingEvent(BaseModel):
    event_id: str
    recording_id: str
    kind: RecordingInteractionKind
    timestamp: str = Field(default_factory=now_iso)
    summary: str | None = None
    source: str = "scrcpy_bridge"
    payload: dict[str, Any] = Field(default_factory=empty_data)


class RecordedInputEvent(RecordingEvent):
    pass


class RecordedCurrentAppState(BaseModel):
    platform: str | None = None
    entry_identity: str | None = None
    surface_identity: str | None = None
    url: str | None = None
    title: str | None = None
    load_state: str | None = None
    raw: dict[str, Any] = Field(default_factory=empty_data)


class ObservationSnapshot(BaseModel):
    observation_id: str
    recording_id: str
    captured_at: str = Field(default_factory=now_iso)
    image_path: Path
    metadata_path: Path
    ui_tree_path: Path | None = None
    entry_identity: str | None = None
    surface_identity: str | None = None
    current_app_state: RecordedCurrentAppState | None = None
    frame_seq: int | None = None
    tree_available: bool = False
    ui_tree_hash: str | None = None
    screenshot_hash: str | None = None
    stabilized: bool = True


class ObservationRef(BaseModel):
    observation_id: str
    captured_at: str
    entry_identity: str | None = None
    surface_identity: str | None = None
    stabilized: bool = True


class TimelineEntry(BaseModel):
    entry_id: str
    recording_id: str
    seq: int
    kind: RecordingInteractionKind
    timestamp: str = Field(default_factory=now_iso)
    summary: str | None = None
    forwarding_event_id: str
    recording_event_id: str
    before_observation_id: str
    after_observation_id: str
    after_stabilized: bool = True


class RecordingTimeline(BaseModel):
    recording_id: str
    entries: list[TimelineEntry] = Field(default_factory=empty_entries)


class RecordingAnalysisTreeFocusHit(BaseModel):
    node_id: str | None = None
    label: str
    score: int


class RecordingAnalysisTreeNode(BaseModel):
    node_id: str
    parent_id: str | None = None
    stable_key: str | None = None
    class_name: str | None = None
    resource_id: str | None = None
    text: str | None = None
    content_desc: str | None = None
    bounds: list[int] | None = None
    state: dict[str, Any] = Field(default_factory=empty_data)


class RecordingAnalysisTreeExcerpt(BaseModel):
    node_count: int = 0
    focus_hits: list[RecordingAnalysisTreeFocusHit] = Field(default_factory=empty_tree_focus_hits)
    compact_nodes: list[RecordingAnalysisTreeNode] = Field(default_factory=empty_tree_nodes)


class RecordingAnalysisScreenshotRef(BaseModel):
    recording_id: str
    entry_id: str
    seq: int
    role: Literal["before", "after"]
    observation_id: str
    path: Path
    entry_identity: str | None = None
    surface_identity: str | None = None
    summary: str | None = None
    tree_available: bool = False
    tree_evidence_id: str | None = None
    compact_tree_excerpt: RecordingAnalysisTreeExcerpt | None = None


class RecordingAnalysisResolvedTarget(BaseModel):
    label: str | None = None
    kind: str | None = None
    source: str | None = None
    confidence: float | None = None
    bounds: list[int] | None = None
    stable_key: str | None = None
    class_name: str | None = None
    resource_id: str | None = None
    content_desc: str | None = None
    semantic_role: str | None = None
    linked_tree_node_id: str | None = None
    state: dict[str, Any] = Field(default_factory=empty_data)


class RecordingAnalysisTargetCandidate(RecordingAnalysisResolvedTarget):
    rank: int = 0


class RecordingAnalysisActionEvidence(BaseModel):
    action_kind: RecordingInteractionKind
    raw_action_summary: str | None = None
    before_entry_identity: str | None = None
    after_entry_identity: str | None = None
    before_surface_identity: str | None = None
    after_surface_identity: str | None = None
    resolved_target: RecordingAnalysisResolvedTarget | None = None
    target_candidates: list[RecordingAnalysisTargetCandidate] = Field(default_factory=empty_analysis_target_candidates)
    warnings: list[str] = Field(default_factory=empty_warnings)


class RecordingAnalysisOutcomeEvidence(BaseModel):
    screen_diff_summary: str | None = None
    screen_diff: dict[str, Any] = Field(default_factory=empty_data)
    before_entry_identity: str | None = None
    after_entry_identity: str | None = None
    before_surface_identity: str | None = None
    after_surface_identity: str | None = None
    warnings: list[str] = Field(default_factory=empty_warnings)


class RecordingAnalysisStep(BaseModel):
    recording_id: str
    entry_id: str
    seq: int
    kind: RecordingInteractionKind
    summary: str | None = None
    action: str | None = None
    intent: str | None = None
    state_change: str | None = None
    procedure_step: str | None = None
    before_observation_id: str
    after_observation_id: str
    before_screenshot: RecordingAnalysisScreenshotRef
    after_screenshot: RecordingAnalysisScreenshotRef
    action_evidence: RecordingAnalysisActionEvidence | None = None
    outcome_evidence: RecordingAnalysisOutcomeEvidence | None = None
    warnings: list[str] = Field(default_factory=empty_warnings)


class RecordingAnalysisResult(BaseModel):
    recording_id: str
    status: Literal["pending", "completed", "failed"] = "pending"
    test_case: TestCase | None = None
    steps: list[RecordingAnalysisStep] = Field(default_factory=empty_analysis_steps)
    source_summary: str | None = None
    warnings: list[str] = Field(default_factory=empty_warnings)
    export_ready: bool = False
    failure_reason: str | None = None


class RecordingCaseExport(BaseModel):
    recording_id: str
    case_id: str
    case_path: Path
    analysis_path: Path
    plan_id: str | None = None
    plan_path: Path | None = None
    snapshot_path: Path | None = None
    exported_at: str = Field(default_factory=now_iso)


class RecordingReplayResult(BaseModel):
    recording_id: str
    case_id: str
    operation_id: str
    run_dir: Path
    result_path: Path
    artifact_manifest_path: Path
    verdict: Literal["passed", "failed", "inconclusive"]
    replayed_at: str = Field(default_factory=now_iso)


class RecordingAssetManifest(BaseModel):
    recording_id: str
    session_path: Path
    current_frame_path: Path | None = None
    frame_count: int = 0
    event_count: int = 0
    timeline_count: int = 0
    observation_count: int = 0
    latest_frame_seq: int | None = None
    latest_observation_id: str | None = None
    latest_timeline_entry_id: str | None = None
    generated_files: dict[str, str] = Field(default_factory=empty_generated_files)


def _coerce_forwarding_step_payload(
    step_kind: Any,
    payload: Any,
) -> ForwardingStepPayload:
    if step_kind in {"pointer_down", "pointer_move", "pointer_up"}:
        return _validate_payload_model(
            PointerStepPayload,
            payload,
            context=f"forwarding step '{step_kind}'",
        )
    if step_kind == "text_inject":
        return _validate_payload_model(
            TextInjectStepPayload,
            payload,
            context=f"forwarding step '{step_kind}'",
        )
    if step_kind == "key_press":
        return _validate_payload_model(
            KeyPressStepPayload,
            payload,
            context=f"forwarding step '{step_kind}'",
        )
    if step_kind in {"key_down", "key_up"}:
        return _validate_payload_model(
            KeyTransitionStepPayload,
            payload,
            context=f"forwarding step '{step_kind}'",
        )
    return _validate_payload_model(
        KeyTransitionStepPayload,
        payload,
        context=f"forwarding step '{step_kind}'",
    )


def _coerce_forwarding_ack_payload(
    kind: Any,
    payload: Any,
) -> ForwardingAckPayload:
    if kind == "pointer":
        return _validate_payload_model(
            PointerForwardingPayload,
            payload,
            context=f"forwarding ack '{kind}'",
        )
    if kind == "input":
        return _validate_payload_model(
            InputForwardingPayload,
            payload,
            context=f"forwarding ack '{kind}'",
        )
    if kind == "back":
        return _validate_payload_model(
            BackForwardingPayload,
            payload,
            context=f"forwarding ack '{kind}'",
        )
    return _validate_payload_model(
        BackForwardingPayload,
        payload,
        context=f"forwarding ack '{kind}'",
    )


def _validate_payload_model(
    model: type[PayloadModelT],
    payload: Any,
    *,
    context: str,
) -> PayloadModelT:
    try:
        return model.model_validate(payload if payload is not None else {})
    except Exception as err:  # pragma: no cover - pydantic error shaping
        raise RecordingInteractionContractError(
            f"{context} has invalid payload: {err}"
        ) from err


def validate_record_interaction_contract(command: RecordInteractionCommand) -> None:
    expected_forwarding_kind = "pointer" if command.kind in {"click", "swipe"} else command.kind
    if command.forwarding_ack.kind != expected_forwarding_kind:
        raise RecordingInteractionContractError(
            "interaction kind "
            f"'{command.kind}' requires forwarding_ack.kind='{expected_forwarding_kind}', "
            f"got '{command.forwarding_ack.kind}'"
        )

    step_kinds = cast(list[ForwardingStepKind], [step.step_kind for step in command.forwarding_ack.steps])
    _require_step_sequence(command.forwarding_ack.steps)
    if command.kind == "click":
        _require_step_kinds(
            command.kind,
            step_kinds,
            required={"pointer_down", "pointer_up"},
            allowed={"pointer_down", "pointer_up"},
        )
        return
    if command.kind == "swipe":
        _require_step_kinds(
            command.kind,
            step_kinds,
            required={"pointer_down", "pointer_up"},
            allowed={"pointer_down", "pointer_move", "pointer_up"},
        )
        return
    if command.kind == "input":
        _require_step_kinds(
            command.kind,
            step_kinds,
            required={"text_inject"},
            allowed={"text_inject", "key_press"},
        )
        return
    if "key_press" in step_kinds:
        _require_step_kinds(
            command.kind,
            step_kinds,
            required={"key_press"},
            allowed={"key_press"},
        )
        return
    _require_step_kinds(
        command.kind,
        step_kinds,
        required={"key_down", "key_up"},
        allowed={"key_down", "key_up"},
    )


def _require_step_sequence(steps: Sequence[ForwardingStep]) -> None:
    if not steps:
        return
    expected_seq = list(range(1, len(steps) + 1))
    actual_seq = [step.seq for step in steps]
    if actual_seq != expected_seq:
        raise RecordingInteractionContractError(
            f"forwarding steps must use contiguous seq values starting at 1, got {actual_seq}"
        )


def _require_step_kinds(
    interaction_kind: RecordingInteractionKind,
    step_kinds: Sequence[ForwardingStepKind],
    *,
    required: set[ForwardingStepKind],
    allowed: set[ForwardingStepKind],
) -> None:
    if not step_kinds:
        raise RecordingInteractionContractError(
            f"interaction kind '{interaction_kind}' requires forwarding steps"
        )
    actual = set(step_kinds)
    missing = sorted(required - actual)
    unexpected = sorted(actual - allowed)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing steps={missing}")
        if unexpected:
            details.append(f"unexpected steps={unexpected}")
        joined = ", ".join(details)
        raise RecordingInteractionContractError(
            f"interaction kind '{interaction_kind}' has invalid forwarding steps: {joined}"
        )
