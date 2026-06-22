from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict


def empty_event_data() -> dict[str, Any]:
    return {}


class RunEventType(str, Enum):
    RUN_STARTED = "run_started"
    STEP_STARTED = "step_started"
    PERCEPTION_COMPLETED = "perception_completed"
    RUNNER_TOOL_CALLED = "runner_tool_called"
    RUNNER_CONTRACT_MISS = "runner_contract_miss"
    RUNNER_DECISION_COMPLETED = "runner_decision_completed"
    ACTION_PROPOSED = "action_proposed"
    ACTION_EXECUTION_STARTED = "action_execution_started"
    ACTION_EXECUTED = "action_executed"
    ACTION_EXECUTION_FAILED = "action_execution_failed"
    RUN_STOPPED = "run_stopped"
    RUN_FAILED = "run_failed"
    LOG = "log"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RunEvent:
    type: RunEventType
    timestamp: str = field(default_factory=utc_now_iso)
    message: str | None = None
    # `data` may contain Phase 0 case tracking keys:
    # 'app_id', 'plan_id', 'case_id'
    data: dict[str, Any] = field(default_factory=empty_event_data)


class RunEventContextPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    app_id: str
    plan_id: str
    case_id: str
    attempt_index: int


class RunStartedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    run_dir: str
    case_title: str | None = None


class RunFailedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    run_dir: str


class LogEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    logger: str
    level: str


class RunnerToolCalledEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int | None = None
    tool_name: str
    arguments: dict[str, object]
    result_summary: str


class RunnerContractMissEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int | None = None
    attempt: int
    tool_names: list[str]
    result_summary: str
    will_retry: bool
    seeded_element_count: int


class RunnerDecisionCompletedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int | None = None
    action: str
    summary: str | None = None


class StepStartedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int


class PerceptionCompletedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int
    element_count: int
    icon_conf: float | None = None
    tree_available: bool | None = None
    tree_node_count: int | None = None


class RunnerActionEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int | None = None
    action: str
    summary: str | None = None


class RunStoppedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int | None = None
    reason: str | None = None
    action: str | None = None
    summary: str | None = None
    warning_code: str | None = None
    consecutive_no_effect_count: int | None = None


@dataclass(frozen=True)
class RunStartedEvent(RunEvent):
    type: RunEventType = RunEventType.RUN_STARTED


@dataclass(frozen=True)
class StepStartedEvent(RunEvent):
    type: RunEventType = RunEventType.STEP_STARTED


@dataclass(frozen=True)
class PerceptionCompletedEvent(RunEvent):
    type: RunEventType = RunEventType.PERCEPTION_COMPLETED


@dataclass(frozen=True)
class RunnerToolCalledEvent(RunEvent):
    type: RunEventType = RunEventType.RUNNER_TOOL_CALLED


@dataclass(frozen=True)
class RunnerContractMissEvent(RunEvent):
    type: RunEventType = RunEventType.RUNNER_CONTRACT_MISS


@dataclass(frozen=True)
class RunnerDecisionCompletedEvent(RunEvent):
    type: RunEventType = RunEventType.RUNNER_DECISION_COMPLETED


@dataclass(frozen=True)
class ActionProposedEvent(RunEvent):
    type: RunEventType = RunEventType.ACTION_PROPOSED


@dataclass(frozen=True)
class ActionExecutedEvent(RunEvent):
    type: RunEventType = RunEventType.ACTION_EXECUTED


@dataclass(frozen=True)
class ActionExecutionStartedEvent(RunEvent):
    type: RunEventType = RunEventType.ACTION_EXECUTION_STARTED


@dataclass(frozen=True)
class ActionExecutionFailedEvent(RunEvent):
    type: RunEventType = RunEventType.ACTION_EXECUTION_FAILED


@dataclass(frozen=True)
class RunStoppedEvent(RunEvent):
    type: RunEventType = RunEventType.RUN_STOPPED


@dataclass(frozen=True)
class RunFailedEvent(RunEvent):
    type: RunEventType = RunEventType.RUN_FAILED


@dataclass(frozen=True)
class LogEvent(RunEvent):
    type: RunEventType = RunEventType.LOG


def build_run_event_context_payload(
    *,
    app_id: str,
    plan_id: str,
    case_id: str,
    attempt_index: int,
) -> dict[str, Any]:
    payload = RunEventContextPayload(
        app_id=app_id,
        plan_id=plan_id,
        case_id=case_id,
        attempt_index=attempt_index,
    )
    return payload.model_dump(mode="json")


def with_run_event_context(
    event: RunEvent,
    *,
    app_id: str,
    plan_id: str,
    case_id: str,
    attempt_index: int,
) -> RunEvent:
    data = dict(event.data)
    data.update(
        build_run_event_context_payload(
            app_id=app_id,
            plan_id=plan_id,
            case_id=case_id,
            attempt_index=attempt_index,
        )
    )
    return replace(event, data=data)


def build_run_started_event_payload(*, run_dir: str, case_title: str | None) -> dict[str, Any]:
    payload = RunStartedEventPayload(run_dir=run_dir, case_title=case_title)
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_failed_event_payload(*, run_dir: str) -> dict[str, Any]:
    payload = RunFailedEventPayload(run_dir=run_dir)
    return payload.model_dump(mode="json")


def build_runner_tool_called_event_payload(
    *,
    step: int | None,
    tool_name: str,
    arguments: dict[str, object],
    result_summary: str,
) -> dict[str, Any]:
    payload = RunnerToolCalledEventPayload(
        step=step,
        tool_name=tool_name,
        arguments=arguments,
        result_summary=result_summary,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_runner_contract_miss_event_payload(
    *,
    step: int | None,
    attempt: int,
    tool_names: list[str],
    result_summary: str,
    will_retry: bool,
    seeded_element_count: int,
) -> dict[str, Any]:
    payload = RunnerContractMissEventPayload(
        step=step,
        attempt=attempt,
        tool_names=tool_names,
        result_summary=result_summary,
        will_retry=will_retry,
        seeded_element_count=seeded_element_count,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_runner_decision_completed_event_payload(
    *,
    step: int | None,
    action: str,
    summary: str | None,
) -> dict[str, Any]:
    payload = RunnerDecisionCompletedEventPayload(
        step=step,
        action=action,
        summary=summary,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_step_started_event_payload(*, step: int) -> dict[str, Any]:
    payload = StepStartedEventPayload(step=step)
    return payload.model_dump(mode="json")


def build_perception_completed_event_payload(
    *,
    step: int,
    element_count: int,
    icon_conf: float | None = None,
    tree_available: bool | None = None,
    tree_node_count: int | None = None,
) -> dict[str, Any]:
    payload = PerceptionCompletedEventPayload(
        step=step,
        element_count=element_count,
        icon_conf=icon_conf,
        tree_available=tree_available,
        tree_node_count=tree_node_count,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_runner_action_event_payload(
    *,
    step: int | None,
    action: str,
    summary: str | None,
    **extra: Any,
) -> dict[str, Any]:
    payload = RunnerActionEventPayload(
        step=step,
        action=action,
        summary=summary,
        **extra,
    )
    return payload.model_dump(mode="json")


def build_run_stopped_event_payload(
    *,
    step: int | None,
    reason: str | None,
    action: str | None = None,
    summary: str | None = None,
    warning_code: str | None = None,
    consecutive_no_effect_count: int | None = None,
) -> dict[str, Any]:
    payload = RunStoppedEventPayload(
        step=step,
        reason=reason,
        action=action,
        summary=summary,
        warning_code=warning_code,
        consecutive_no_effect_count=consecutive_no_effect_count,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def serialize_run_event_payload(event: RunEvent) -> dict[str, Any]:
    payload = dict(event.data)
    if event.type == RunEventType.RUN_STARTED:
        return RunStartedEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if event.type == RunEventType.STEP_STARTED:
        return StepStartedEventPayload.model_validate(payload).model_dump(mode="json")
    if event.type == RunEventType.PERCEPTION_COMPLETED:
        return PerceptionCompletedEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if event.type == RunEventType.RUNNER_TOOL_CALLED:
        return RunnerToolCalledEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if event.type == RunEventType.RUNNER_CONTRACT_MISS:
        return RunnerContractMissEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if event.type == RunEventType.RUNNER_DECISION_COMPLETED:
        return RunnerDecisionCompletedEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if event.type in {
        RunEventType.ACTION_PROPOSED,
        RunEventType.ACTION_EXECUTION_STARTED,
        RunEventType.ACTION_EXECUTED,
        RunEventType.ACTION_EXECUTION_FAILED,
    }:
        return RunnerActionEventPayload.model_validate(payload).model_dump(mode="json")
    if event.type == RunEventType.RUN_STOPPED:
        return RunStoppedEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if event.type == RunEventType.RUN_FAILED:
        return RunFailedEventPayload.model_validate(payload).model_dump(mode="json", exclude_none=True)
    return payload


def run_event_step(event: RunEvent) -> int | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("step")
    return raw if isinstance(raw, int) else None


def run_event_action(event: RunEvent) -> str | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("action")
    return raw if isinstance(raw, str) else None


def run_event_summary(event: RunEvent) -> str | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("summary")
    return raw if isinstance(raw, str) else None


def run_event_reason(event: RunEvent) -> str | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("reason")
    return raw if isinstance(raw, str) else None


def run_event_attempt(event: RunEvent) -> int | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("attempt")
    return raw if isinstance(raw, int) else None


def run_event_element_count(event: RunEvent) -> int | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("element_count")
    return raw if isinstance(raw, int) else None


def run_event_seeded_element_count(event: RunEvent) -> int | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("seeded_element_count")
    return raw if isinstance(raw, int) else None


def run_event_duration_ms(event: RunEvent) -> int | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("duration_ms")
    return raw if isinstance(raw, int) else None


def run_event_error_type(event: RunEvent) -> str | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("error_type")
    return raw if isinstance(raw, str) else None


def run_event_error_message(event: RunEvent) -> str | None:
    payload = serialize_run_event_payload(event)
    raw = payload.get("error_message")
    return raw if isinstance(raw, str) else None


def run_event_will_retry(event: RunEvent) -> bool:
    payload = serialize_run_event_payload(event)
    raw = payload.get("will_retry")
    return raw is True


RunEventSink = Callable[[RunEvent], None]
