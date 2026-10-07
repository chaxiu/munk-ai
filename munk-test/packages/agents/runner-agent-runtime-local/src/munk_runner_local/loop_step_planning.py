from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
from munk.agent_base.action import Action, ActionExecutionError, ActionType
from munk.agent_base.action_annotation import annotate_action_targets
from munk.agent_base.base import ActionFeedback, RuntimeObservationSnapshot, ScreenState
from munk.core import observe_action_result, redetect_icon_conf
from munk.core.action_targets import build_canonical_target_parts
from munk.perception import ObservationTree
from munk.perception.image import BgrImage
from munk.services.events import (
    ActionProposedEvent,
    PerceptionCompletedEvent,
    RunEventSink,
    RunStoppedEvent,
    build_perception_completed_event_payload,
    build_run_stopped_event_payload,
    build_runner_action_event_payload,
)
from munk.services.settle import SettleComparableSnapshot

from munk_runner_local.brain.runner_view import build_action_targets

from .context import RunContext
from .loop_support import NO_EFFECT_WARNING_CODE, decorate_last_observation
from .pre_execute_guard import guard_action_before_execution
from .step_observation import StepObservationState, refresh_step_observation_state, write_observation_artifacts

NO_EFFECT_THRESHOLD_ERROR = "device_call_succeeded_but_no_effect_threshold_exceeded"
NO_EFFECT_THRESHOLD = 3

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NoEffectTrackingState:
    action_type: ActionType | None = None
    count: int = 0


@dataclass(frozen=True)
class PreparedStepAction:
    action: Action
    screen: ScreenState
    screen_bgr: BgrImage
    settle_before: SettleComparableSnapshot
    device_size: tuple[int, int]
    image_w: int
    image_h: int
    raw_path: Path
    annotated_path: Path
    last_target_identity: str | None
    last_surface_identity: str | None
    no_effect_state: NoEffectTrackingState
    pre_execute_rebound: bool
    pre_execute_status: str | None
    pre_execute_target_stable_key: str | None
    pre_execute_target_match_strategy: str | None


@dataclass(frozen=True)
class StepPreparationStop:
    reason: str
    last_target_identity: str | None
    last_surface_identity: str | None


CaptureScreenState = Callable[..., RuntimeObservationSnapshot]
CaptureSettleSnapshot = Callable[..., SettleComparableSnapshot]


def prepare_step_action(
    *,
    context: RunContext,
    event_sink: RunEventSink | None,
    step_index: int,
    min_redetect_conf: float,
    previous_screen: ScreenState | None,
    previous_action: Action | None,
    previous_action_feedback: ActionFeedback | None,
    no_effect_state: NoEffectTrackingState,
    capture_screen_state: CaptureScreenState,
    capture_settle_snapshot: CaptureSettleSnapshot,
) -> PreparedStepAction | StepPreparationStop:
    screen_bgr = context.device.screenshot_bgr()
    image_h = int(screen_bgr.shape[0])
    image_w = int(screen_bgr.shape[1])
    device_size = context.device.window_size()
    raw_path = context.paths.raw_dir / f"step_{step_index:04d}.png"
    cv2.imwrite(str(raw_path), screen_bgr)
    redetect_index = 0
    stale_replan_attempted = False
    pre_execute_rebound = False
    pre_execute_status: str | None = None
    pre_execute_target_stable_key: str | None = None
    pre_execute_target_match_strategy: str | None = None

    while True:
        current_conf = redetect_icon_conf(
            context.params.icon_conf,
            redetect_index,
            min_conf=min_redetect_conf,
        )
        snapshot = capture_screen_state(
            context=context,
            screen_bgr=screen_bgr,
            icon_conf=current_conf,
            source="step_pre_action",
            device_size=device_size,
        )
        screen = snapshot.screen
        observation_tree = snapshot.observation_tree
        _publish_perception_completed(event_sink, step_index, screen, current_conf)
        last_target_identity = screen.entry_identity
        last_surface_identity = screen.surface_identity

        updated_screen, no_effect_state, threshold_stop = _apply_previous_observation(
            event_sink=event_sink,
            step_index=step_index,
            screen=screen,
            previous_screen=previous_screen,
            previous_action=previous_action,
            previous_action_feedback=previous_action_feedback,
            no_effect_state=no_effect_state,
        )
        if threshold_stop is not None:
            return threshold_stop
        screen = updated_screen
        screen = replace(
            screen,
            action_target_parts=build_canonical_target_parts(screen),
        )
        write_observation_artifacts(context, step_index, screen, observation_tree)
        settle_before = capture_settle_snapshot(
            context=context,
            screen_bgr=screen_bgr,
            observation_tree=observation_tree,
            device_size=device_size,
        )
        annotated_path = _write_annotated_step_image(
            context=context,
            step_index=step_index,
            screen=screen,
            screen_bgr=screen_bgr,
        )
        action: Action = context.brain.next_action(screen)
        _publish_action_proposed(
            event_sink=event_sink,
            step_index=step_index,
            action=action,
            redetect_index=redetect_index,
        )
        if action.type == ActionType.REDETECT:
            next_conf = redetect_icon_conf(
                context.params.icon_conf,
                redetect_index + 1,
                min_conf=min_redetect_conf,
            )
            if next_conf == current_conf:
                break
            redetect_index += 1
            logger.info("redetect_step=%s icon_conf=%s", redetect_index, next_conf)
            continue
        decision_state = StepObservationState(
            screen_bgr=screen_bgr,
            screen=screen,
            settle_before=settle_before,
            device_size=device_size,
        )
        guard_result = guard_action_before_execution(
            context=context,
            action=action,
            decision_state=decision_state,
            refresh_state=lambda preserve_feedback_from: refresh_step_observation_state(
                context=context,
                step_index=step_index,
                icon_conf=current_conf,
                raw_path=raw_path,
                capture_screen_state=capture_screen_state,
                capture_settle_snapshot=capture_settle_snapshot,
                preserve_feedback_from=preserve_feedback_from,
            ),
        )
        if guard_result.invalidated:
            _log_and_publish_invalidated_action(
                event_sink=event_sink,
                step_index=step_index,
                action=action,
                status=guard_result.status,
                stale_reason=guard_result.stale_reason,
                target_stable_key=guard_result.target_stable_key,
                target_match_strategy=guard_result.target_match_strategy,
            )
            if stale_replan_attempted:
                raise ActionExecutionError(
                    guard_result.stale_reason
                    or f"{action.type.value} invalidated before execution after fresh replan"
                )
            stale_replan_attempted = True
            screen_bgr = guard_result.state.screen_bgr
            screen = guard_result.state.screen
            settle_before = guard_result.state.settle_before
            device_size = guard_result.state.device_size
            image_h = int(screen_bgr.shape[0])
            image_w = int(screen_bgr.shape[1])
            continue
        action = guard_result.action
        screen_bgr = guard_result.state.screen_bgr
        screen = guard_result.state.screen
        settle_before = guard_result.state.settle_before
        device_size = guard_result.state.device_size
        image_h = int(screen_bgr.shape[0])
        image_w = int(screen_bgr.shape[1])
        pre_execute_rebound = guard_result.rebound
        pre_execute_status = guard_result.status
        pre_execute_target_stable_key = guard_result.target_stable_key
        pre_execute_target_match_strategy = guard_result.target_match_strategy
        if pre_execute_rebound:
            logger.info(
                "pre_execute_rebound step=%s action=%s stable_key=%s match_strategy=%s rebound_box=%s",
                step_index,
                action.type.value,
                pre_execute_target_stable_key,
                pre_execute_target_match_strategy,
                action.box,
            )
        break

    return PreparedStepAction(
        action=action,
        screen=screen,
        screen_bgr=screen_bgr,
        settle_before=settle_before,
        device_size=device_size,
        image_w=image_w,
        image_h=image_h,
        raw_path=raw_path,
        annotated_path=annotated_path,
        last_target_identity=last_target_identity,
        last_surface_identity=last_surface_identity,
        no_effect_state=no_effect_state,
        pre_execute_rebound=pre_execute_rebound,
        pre_execute_status=pre_execute_status,
        pre_execute_target_stable_key=pre_execute_target_stable_key,
        pre_execute_target_match_strategy=pre_execute_target_match_strategy,
    )


def _publish_perception_completed(
    event_sink: RunEventSink | None,
    step_index: int,
    screen: ScreenState,
    current_conf: float,
) -> None:
    if event_sink is None:
        return
    event_sink(
        PerceptionCompletedEvent(
            message=f"perception completed for step {step_index}",
            data=build_perception_completed_event_payload(
                step=step_index,
                element_count=len(screen.elements),
                icon_conf=current_conf,
                tree_available=screen.screen_frame.tree_available if screen.screen_frame is not None else False,
                tree_node_count=len(screen.screen_frame.tree_nodes) if screen.screen_frame is not None else 0,
            ),
        )
    )


def _apply_previous_observation(
    *,
    event_sink: RunEventSink | None,
    step_index: int,
    screen: ScreenState,
    previous_screen: ScreenState | None,
    previous_action: Action | None,
    previous_action_feedback: ActionFeedback | None,
    no_effect_state: NoEffectTrackingState,
) -> tuple[ScreenState, NoEffectTrackingState, StepPreparationStop | None]:
    if previous_screen is None or previous_action is None:
        return screen, no_effect_state, None
    observation = observe_action_result(previous_screen, screen)
    warning_code: str | None = None
    warning_count = 0
    if not observation.screen_changed:
        warning_code = NO_EFFECT_WARNING_CODE
        no_effect_state = _update_no_effect_state(no_effect_state, previous_action.type)
        warning_count = no_effect_state.count
    else:
        no_effect_state = NoEffectTrackingState()
    observation = decorate_last_observation(
        observation,
        warning_code=warning_code,
        action_type=previous_action.type,
        consecutive_count=warning_count,
    )
    screen = replace(
        screen,
        last_action_observation=observation,
        last_action_feedback=previous_action_feedback,
    )
    if warning_code == NO_EFFECT_WARNING_CODE and warning_count >= NO_EFFECT_THRESHOLD:
        _publish_no_effect_threshold_stop(event_sink, step_index, previous_action, warning_code, warning_count)
        return (
            screen,
            no_effect_state,
            StepPreparationStop(
                reason=NO_EFFECT_THRESHOLD_ERROR,
                last_target_identity=screen.entry_identity,
                last_surface_identity=screen.surface_identity,
            ),
        )
    return screen, no_effect_state, None


def _update_no_effect_state(
    no_effect_state: NoEffectTrackingState,
    action_type: ActionType,
) -> NoEffectTrackingState:
    if no_effect_state.action_type == action_type:
        return NoEffectTrackingState(action_type=action_type, count=no_effect_state.count + 1)
    return NoEffectTrackingState(action_type=action_type, count=1)


def _publish_no_effect_threshold_stop(
    event_sink: RunEventSink | None,
    step_index: int,
    action: Action,
    warning_code: str,
    warning_count: int,
) -> None:
    if event_sink is None:
        return
    event_sink(
        RunStoppedEvent(
            message=f"run stopped after stable no-effect threshold at step {step_index}",
            data=build_run_stopped_event_payload(
                step=step_index,
                action=action.type.value,
                summary=action.summary,
                reason=NO_EFFECT_THRESHOLD_ERROR,
                warning_code=warning_code,
                consecutive_no_effect_count=warning_count,
            ),
        )
    )


def _write_annotated_step_image(
    *,
    context: RunContext,
    step_index: int,
    screen: ScreenState,
    screen_bgr: BgrImage,
) -> Path:
    annotated_targets = build_action_targets(
        screen,
        max_elements=context.params.runner_max_elements,
    )
    annotated = annotate_action_targets(screen_bgr, annotated_targets)
    annotated_path = context.paths.annotated_dir / f"step_{step_index:04d}.png"
    cv2.imwrite(str(annotated_path), annotated)
    return annotated_path


def _publish_action_proposed(
    *,
    event_sink: RunEventSink | None,
    step_index: int,
    action: Action,
    redetect_index: int,
) -> None:
    if event_sink is None:
        return
    event_sink(
        ActionProposedEvent(
            message=f"action proposed for step {step_index}",
            data=build_runner_action_event_payload(
                step=step_index,
                action=action.type.value,
                summary=action.summary,
                redetect_index=redetect_index,
            ),
        )
    )


def _log_and_publish_invalidated_action(
    *,
    event_sink: RunEventSink | None,
    step_index: int,
    action: Action,
    status: str,
    stale_reason: str | None,
    target_stable_key: str | None,
    target_match_strategy: str | None,
) -> None:
    logger.info(
        "pre_execute_invalidated step=%s action=%s stale_reason=%s stable_key=%s",
        step_index,
        action.type.value,
        stale_reason,
        target_stable_key,
    )
    if event_sink is None:
        return
    invalidated_payload: dict[str, object] = {
        "pre_execute_status": status,
        "pre_execute_invalidated": True,
        "stale_reason": stale_reason,
    }
    if target_stable_key is not None:
        invalidated_payload["target_stable_key"] = target_stable_key
    if target_match_strategy is not None:
        invalidated_payload["target_match_strategy"] = target_match_strategy
    event_sink(
        ActionProposedEvent(
            message=f"action invalidated before execution for step {step_index}",
            data=build_runner_action_event_payload(
                step=step_index,
                action=action.type.value,
                summary=action.summary,
                **invalidated_payload,
            ),
        )
    )
