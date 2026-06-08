from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from munk.agent_base.action import Action, ActionType
from munk.agent_base.base import ScreenState
from munk.app import AppTarget
from munk.perception.image import BgrImage

InteractiveSessionStatus = Literal[
    "created",
    "waiting_agent",
    "acting",
    "finalized",
    "aborted",
    "expired",
]
InteractiveStepKind = Literal["observation", "action"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class InteractiveTargetSummary:
    target_id: int
    label: str | None
    kind: str | None
    source: str
    box: tuple[int, int, int, int]
    resource_id: str | None = None
    text: str | None = None


@dataclass(frozen=True)
class InteractiveObservation:
    session_id: str
    captured_at: str
    screen: ScreenState
    targets: list[InteractiveTargetSummary]
    summary: str
    vl_max_side: int
    annotated_image_bgr: BgrImage | None = None


@dataclass(frozen=True)
class InteractiveActionRequest:
    action: Action
    target_id: int | None = None
    resource_id: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class InteractiveActionResult:
    session_id: str
    action: Action
    normalized_action: Action
    before: InteractiveObservation
    after: InteractiveObservation
    executed: bool
    timed_out: bool
    duration_ms: int
    effect_summary: str
    error_type: str | None = None
    error_message: str | None = None
    settle_status: str = "skipped"
    settle_timed_out: bool = False
    settle_elapsed_ms: int = 0
    settle_summary: str | None = None


@dataclass(frozen=True)
class InteractiveStepRecord:
    step_index: int
    kind: InteractiveStepKind
    timestamp: str
    summary: str
    observation: InteractiveObservation | None = None
    action_type: ActionType | None = None
    action_result: InteractiveActionResult | None = None


@dataclass(frozen=True)
class InteractiveFinalizeResult:
    session_id: str
    status: InteractiveSessionStatus
    platform: str
    device_ref: str | None
    step_count: int
    steps_summary: list[str]
    last_observation_summary: str | None
    agent_summary: str | None = None


@dataclass
class InteractiveSession:
    session_id: str
    platform: str
    app_target: AppTarget
    device_ref: str | None
    claim_owner_id: str
    status: InteractiveSessionStatus
    max_steps: int
    step_count: int = 0
    steps: list[InteractiveStepRecord] = field(default_factory=list)
    started_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    last_active_at: str = field(default_factory=now_iso)
    expires_at: str = field(default_factory=now_iso)
    idle_expires_at: str = field(default_factory=now_iso)
    last_observation: InteractiveObservation | None = None
    finalized_result: InteractiveFinalizeResult | None = None
