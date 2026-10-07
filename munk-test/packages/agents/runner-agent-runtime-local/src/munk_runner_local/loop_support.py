from __future__ import annotations

import logging
from dataclasses import replace

from munk.agent_base.action import Action, ActionType
from munk.agent_base.base import ActionObservation
from munk.device import CurrentAppState
from munk.services.events import (
    RunEventSink,
    RunStoppedEvent,
    StepStartedEvent,
    build_run_stopped_event_payload,
    build_step_started_event_payload,
)

from .context import RunContext

NO_EFFECT_WARNING_CODE = "device_call_succeeded_but_no_effect"

logger = logging.getLogger(__name__)


def decorate_last_observation(
    observation: ActionObservation,
    *,
    warning_code: str | None,
    action_type: ActionType,
    consecutive_count: int,
) -> ActionObservation:
    if warning_code != NO_EFFECT_WARNING_CODE or consecutive_count <= 0:
        return observation
    summary = f"warning={warning_code} action={action_type.value} count={consecutive_count}; {observation.summary}"
    return replace(observation, summary=summary)


def publish_step_started(event_sink: RunEventSink | None, step_index: int) -> None:
    if event_sink is None:
        return
    event_sink(
        StepStartedEvent(
            message=f"step {step_index} started",
            data=build_step_started_event_payload(step=step_index),
        )
    )


def publish_stop(event_sink: RunEventSink | None, step_index: int, reason: str | None) -> None:
    if event_sink is None:
        return
    event_sink(
        RunStoppedEvent(
            message=f"run stopped at step {step_index}",
            data=build_run_stopped_event_payload(step=step_index, reason=reason),
        )
    )


def begin_step_logs(context: RunContext, step_index: int) -> None:
    collector = context.log_collector
    if collector is None:
        return
    collector.begin_step(step_index)


def finish_step_logs(
    context: RunContext,
    step_index: int,
    *,
    target_identity: str | None = None,
    surface_identity: str | None = None,
) -> None:
    collector = context.log_collector
    if collector is None:
        return
    collector.finish_step(
        step_index,
        target_identity=target_identity,
        surface_identity=surface_identity,
    )


def safe_app_state(context: RunContext) -> CurrentAppState | None:
    try:
        return context.device.app_current()
    except Exception as exc:  # noqa: BLE001
        logger.warning("app_current_after_step_failed error=%s", exc)
        return None


def summarize_action(action: Action) -> dict[str, object]:
    payload: dict[str, object] = {"type": action.type.value}
    if action.summary:
        payload["summary"] = action.summary
    if action.point is not None:
        payload["point"] = action.point
    if action.box is not None:
        payload["box"] = action.box
    if action.start is not None:
        payload["start"] = action.start
    if action.end is not None:
        payload["end"] = action.end
    if action.duration is not None:
        payload["duration"] = action.duration
    if action.start_x_ratio is not None:
        payload["start_x_ratio"] = action.start_x_ratio
    if action.start_y_ratio is not None:
        payload["start_y_ratio"] = action.start_y_ratio
    if action.distance_ratio is not None:
        payload["distance_ratio"] = action.distance_ratio
    if action.distance_px is not None:
        payload["distance_px"] = action.distance_px
    if action.text is not None:
        payload["text"] = action.text
    if action.text_mode is not None:
        payload["text_mode"] = action.text_mode
    if action.match_type is not None:
        payload["match_type"] = action.match_type
    if action.match_texts is not None:
        payload["match_texts"] = list(action.match_texts)
    if action.max_attempts is not None:
        payload["max_attempts"] = action.max_attempts
    if action.direction is not None:
        payload["direction"] = action.direction
    if action.dismiss_keyboard is not None:
        payload["dismiss_keyboard"] = action.dismiss_keyboard
    return payload
