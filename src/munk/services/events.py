from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


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


RunEventSink = Callable[[RunEvent], None]
