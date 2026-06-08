from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from munk.adapters.shared.payload_models import DeviceListData


class InteractiveScreenData(BaseModel):
    screen_size: tuple[int, int] = Field(description="Observed screen size as width, height.")
    entry_identity: str | None = Field(default=None, description="Current entry identity when available.")
    surface_identity: str | None = Field(default=None, description="Current surface identity when available.")
    platform: str | None = Field(default=None, description="Observed platform when available.")
    element_count: int = Field(description="Number of resolved screen elements.")
    platform_context: dict[str, object] | None = Field(
        default=None,
        description="Optional lightweight platform-specific observation context.",
    )


class InteractiveTargetData(BaseModel):
    target_id: int = Field(description="Resolved target identifier.")
    label: str | None = Field(default=None, description="Optional target label.")
    kind: str | None = Field(default=None, description="Optional target kind.")
    source: str = Field(description="Resolver source of the target.")
    box: tuple[int, int, int, int] = Field(description="Target bounds as left, top, right, bottom.")
    resource_id: str | None = Field(default=None, description="Optional resource identifier.")
    text: str | None = Field(default=None, description="Optional target text.")


class InteractiveTargetCompactData(BaseModel):
    target_id: int = Field(description="Resolved target identifier.")
    source: str = Field(description="Resolver source of the target.")
    box: tuple[int, int, int, int] = Field(description="Target bounds as left, top, right, bottom.")
    label: str | None = Field(default=None, description="Optional target label.")
    text: str | None = Field(default=None, description="Optional target text.")


InteractiveTargetPayload: TypeAlias = InteractiveTargetData | InteractiveTargetCompactData


class InteractiveObservationData(BaseModel):
    detail: Literal["compact", "full"] = Field(description="Observation payload detail level.")
    captured_at: str = Field(description="Observation capture timestamp in ISO format.")
    summary: str = Field(description="Concise observation summary.")
    screen: InteractiveScreenData = Field(description="Serializable screen summary.")
    total_target_count: int = Field(description="Total number of resolved targets before output projection.")
    returned_target_count: int = Field(description="Number of targets returned in this payload.")
    truncated: bool = Field(description="Whether the payload omitted targets due to compact projection.")
    targets: list[InteractiveTargetPayload] = Field(default_factory=list, description="Resolved interactive targets.")
    screenshot_mime_type: str | None = Field(
        default=None,
        description="Optional screenshot MIME type when include_screenshot is enabled.",
    )
    screenshot_path: str | None = Field(
        default=None,
        description="Optional absolute PNG screenshot path when include_screenshot is enabled.",
    )


class InteractiveActionData(BaseModel):
    type: str = Field(description="Action type.")
    target_id: int | None = Field(default=None, description="Optional target identifier from the original request.")
    resource_id: str | None = Field(default=None, description="Optional target resource identifier from the original request.")
    label: str | None = Field(default=None, description="Optional target label from the original request.")
    box: tuple[int, int, int, int] | None = Field(default=None, description="Optional action box.")
    point: tuple[int, int] | None = Field(default=None, description="Optional action point.")
    text: str | None = Field(default=None, description="Optional action text.")
    start: tuple[int, int] | None = Field(default=None, description="Optional action start point.")
    end: tuple[int, int] | None = Field(default=None, description="Optional action end point.")
    duration: float | None = Field(default=None, description="Optional action duration in seconds.")
    dismiss_keyboard: bool | None = Field(default=None, description="Optional keyboard dismissal flag.")
    summary: str | None = Field(default=None, description="Optional human-readable action summary.")


class InteractiveSessionData(BaseModel):
    session_id: str = Field(description="Interactive session identifier.")
    status: Literal["created", "waiting_agent", "acting", "finalized", "aborted", "expired"] = Field(
        description="Current interactive session status.",
    )
    platform: str = Field(description="Interactive target platform.")
    app_id: str = Field(description="Application identifier associated with the session.")
    device_ref: str | None = Field(default=None, description="Claimed device reference when available.")
    step_count: int = Field(description="Current recorded step count.")
    started_at: str = Field(description="Session start timestamp in ISO format.")
    updated_at: str = Field(description="Session update timestamp in ISO format.")
    last_active_at: str = Field(description="Last agent activity timestamp in ISO format.")
    expires_at: str = Field(description="Session absolute expiry timestamp in ISO format.")
    idle_expires_at: str = Field(description="Session idle expiry timestamp in ISO format.")
    last_observation_summary: str | None = Field(default=None, description="Summary of the latest observation when available.")
    finalized_agent_summary: str | None = Field(default=None, description="Agent summary from finalize when available.")


class InteractiveSessionListItemData(BaseModel):
    session_id: str = Field(description="Interactive session identifier.")
    status: Literal["created", "waiting_agent", "acting", "finalized", "aborted", "expired"] = Field(
        description="Current interactive session status.",
    )
    platform: str = Field(description="Interactive target platform.")
    app_id: str = Field(description="Application identifier associated with the session.")
    device_ref: str | None = Field(default=None, description="Claimed device reference when available.")
    step_count: int = Field(description="Current recorded step count.")
    last_active_at: str = Field(description="Last agent activity timestamp in ISO format.")
    idle_expires_at: str = Field(description="Session idle expiry timestamp in ISO format.")
    last_observation_summary: str | None = Field(default=None, description="Summary of the latest observation when available.")


class SessionStartConflictData(BaseModel):
    requested_device_ref: str | None = Field(default=None, description="Requested device reference when available.")
    blocked_by: str = Field(description="Blocking operation or interactive session identifier.")
    blocking_kind: str = Field(description="Blocking owner kind.")
    blocking_status: str = Field(description="Blocking owner status.")
    blocking_device_ref: str | None = Field(default=None, description="Blocking device reference when available.")
    reason: str = Field(description="Concise conflict reason.")
    can_resume: bool = Field(description="Whether the blocking owner can be resumed through device MCP tools.")
    resume_session_id: str | None = Field(default=None, description="Interactive session id to resume when available.")
    suggested_next_actions: list[str] = Field(
        default_factory=list,
        description="Suggested next MCP tool calls to recover from the conflict.",
    )


class AppLifecycleData(BaseModel):
    action: Literal["launch", "stop", "install"] = Field(description="Lifecycle action that was executed.")
    app_id: str = Field(description="Application identifier associated with the lifecycle action.")
    platform: str = Field(description="Target platform for the lifecycle action.")
    device_ref: str | None = Field(default=None, description="Target device reference when available.")
    entry_identity: str = Field(description="Resolved entry identity used for the lifecycle action.")
    artifact_path: str | None = Field(default=None, description="Installed artifact path when applicable.")


class DevicesListOutput(BaseModel):
    summary: str = Field(description="Concise device list summary.")
    data: DeviceListData = Field(description="Canonical discovered device payload.")


class AppLifecycleOutput(BaseModel):
    summary: str = Field(description="Concise lifecycle action summary.")
    data: AppLifecycleData = Field(description="Lifecycle action result payload.")


class SessionsListOutput(BaseModel):
    summary: str = Field(description="Concise active session list summary.")
    data: list[InteractiveSessionListItemData] = Field(
        default_factory=list,
        description="Active interactive session summaries for resume and troubleshooting.",
    )


class SessionStartOutput(BaseModel):
    summary: str = Field(description="Concise session start summary.")
    data: InteractiveSessionData = Field(description="Interactive session summary.")


class SessionGetOutput(BaseModel):
    summary: str = Field(description="Concise session state summary.")
    data: InteractiveSessionData = Field(description="Interactive session summary.")


class SessionObserveOutput(BaseModel):
    summary: str = Field(description="Concise observe summary.")
    session: InteractiveSessionData = Field(description="Interactive session summary after observe.")
    observation: InteractiveObservationData = Field(description="Structured observation payload.")


class SessionActOutput(BaseModel):
    summary: str = Field(description="Concise action result summary.")
    session: InteractiveSessionData = Field(description="Interactive session summary after action.")
    action: InteractiveActionData = Field(description="Original requested action payload.")
    normalized_action: InteractiveActionData = Field(description="Normalized action payload actually executed.")
    before: InteractiveObservationData | None = Field(
        default=None,
        description="Observation captured before action execution when full detail is requested.",
    )
    after: InteractiveObservationData = Field(description="Observation captured after action execution.")
    before_summary: str = Field(description="Concise summary of the observation captured before action execution.")
    after_summary: str = Field(description="Concise summary of the observation captured after action execution.")
    executed: bool = Field(description="Whether the action executed.")
    timed_out: bool = Field(description="Whether the action timed out.")
    duration_ms: int = Field(description="Action duration in milliseconds.")
    effect_summary: str = Field(description="Concise action effect summary.")
    settle_status: str = Field(description="Post-action settle status.")
    settle_timed_out: bool = Field(description="Whether the post-action settle window timed out.")
    settle_elapsed_ms: int = Field(description="Elapsed settle time in milliseconds.")
    settle_summary: str | None = Field(default=None, description="Optional settle summary.")
    error_type: str | None = Field(default=None, description="Optional action error type.")
    error_message: str | None = Field(default=None, description="Optional action error message.")


class SessionFinalizeOutput(BaseModel):
    summary: str = Field(description="Concise finalize summary.")
    session: InteractiveSessionData = Field(description="Interactive session summary after finalize.")
    step_count: int = Field(description="Finalized step count.")
    steps_summary: list[str] = Field(default_factory=list, description="Transcript step summaries.")
    last_observation_summary: str | None = Field(default=None, description="Last observation summary when available.")
    agent_summary: str | None = Field(default=None, description="Optional agent-authored finalize summary.")


class SessionAbortOutput(BaseModel):
    summary: str = Field(description="Concise abort summary.")
    data: InteractiveSessionData = Field(description="Interactive session summary after abort.")
