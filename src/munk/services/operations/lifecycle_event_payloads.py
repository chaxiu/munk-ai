from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AgentRuntimeLifecycleEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    lifecycle_state: str
    agent_role: str
    event_timestamp: str | None = None
    timestamp: str | None = None
    runner_event_type: str | None = None


class ContextPrepareParamsResolvedEventPayload(AgentRuntimeLifecycleEventPayload):
    device_ref: str | None = None
    max_steps: int | None = None
    max_seconds: float | None = None
    interval: float | None = None
    initial_ready_timeout_sec: float | None = None
    max_side: int | None = None
    settle_timeout: float | None = None
    settle_mode: str | None = None
    settle_ocr_only: bool | None = None
    settle_ratio_threshold: float | None = None
    settle_delay_sec: float | None = None


class ContextPrepareDeviceReadyEventPayload(AgentRuntimeLifecycleEventPayload):
    device_ref: str | None = None
    platform: str | None = None


class ContextPreparePerceptionReadyEventPayload(AgentRuntimeLifecycleEventPayload):
    max_side: int | None = None
    icon_conf: float | None = None


class JudgeRuntimeEventPayload(AgentRuntimeLifecycleEventPayload):
    root_dir: str | None = None
    evidence_count: int | None = None
    primary_evidence_count: int | None = None
    supporting_evidence_count: int | None = None
    verdict: str | None = None
    tool_call_count: int | None = None
    prompt_path: str | None = None
    error_type: str | None = None


class RunnerRuntimeEventPayload(AgentRuntimeLifecycleEventPayload):
    root_dir: str | None = None


class OperationSubmittedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    pid: int | None = None
    mode: str | None = None


class OperationStartedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    pid: int | None = None
    command: str | None = None
    operation_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None
    title: str | None = None
    parent_operation_id: str | None = None
    position_label: str | None = None
    case_title: str | None = None


class OperationInterruptedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    command: str | None = None


class ResourceClaimedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_ref: str | None = None
    resource_scope: str | None = None


class ResourceReleasedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_ref: str | None = None
    reason: str | None = None


class ResourceConflictEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    command: str | None = None
    requested_device_ref: str | None = None
    blocking_device_ref: str | None = None
    reason: str | None = None
