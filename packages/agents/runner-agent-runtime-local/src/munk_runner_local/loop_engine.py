from __future__ import annotations

import logging
import time
from collections.abc import Callable

from munk.agent_base.action import Action, ActionExecutionError, ActionExecutionTimeoutError, ActionType
from munk.agent_base.action.high_level import (
    SCROLL_UNTIL_TEXT_NOT_FOUND_ERROR,
    SCROLL_UNTIL_TEXT_STAGNATED_ERROR,
    uses_high_level_execution,
)
from munk.agent_base.action.high_level_common import from_atomic_result
from munk.agent_base.base import ActionFeedback, ObservationSnapshotSource, RuntimeObservationSnapshot, ScreenState
from munk.core import map_action_to_device
from munk.services.events import (
    ActionExecutedEvent,
    ActionExecutionFailedEvent,
    ActionExecutionStartedEvent,
    RunEventSink,
    build_runner_action_event_payload,
)
from munk.services.models import RunnerKernelResult
from munk.services.settle import SettleComparableSnapshot, SettleResult

from .action_feedback import (
    augment_runner_action_feedback,
    build_failed_runner_action_feedback,
    build_runner_action_feedback,
)
from .context import RunContext
from .loop_engine_support import build_run_result, ensure_context_prep_ready
from .loop_step_planning import (
    NoEffectTrackingState,
    PreparedStepAction,
    StepPreparationStop,
    prepare_step_action,
)
from .loop_support import begin_step_logs, finish_step_logs, safe_app_state, summarize_action

RECOVERABLE_SCROLL_UNTIL_TEXT_ERRORS = {
    SCROLL_UNTIL_TEXT_NOT_FOUND_ERROR,
    SCROLL_UNTIL_TEXT_STAGNATED_ERROR,
}

logger = logging.getLogger(__name__)

CaptureScreenState = Callable[..., RuntimeObservationSnapshot]
CaptureSettleSnapshot = Callable[..., SettleComparableSnapshot]
WaitUntilInitialScreenReady = Callable[..., SettleResult | None]
SettleAfterAction = Callable[..., SettleResult]
PublishStepStarted = Callable[[RunEventSink | None, int], None]
PublishStop = Callable[[RunEventSink | None, int, str | None], None]


def execute_run_loop(
    *,
    context: RunContext,
    event_sink: RunEventSink | None,
    should_stop: Callable[[], bool],
    wait_until_initial_screen_ready: WaitUntilInitialScreenReady,
    capture_screen_state: CaptureScreenState,
    capture_settle_snapshot: CaptureSettleSnapshot,
    settle_after_action: SettleAfterAction,
    publish_step_started: PublishStepStarted,
    publish_stop: PublishStop,
) -> RunnerKernelResult:
    run_started_at = time.monotonic()
    on_run_started = getattr(context.brain, "on_run_started", None)
    if callable(on_run_started):
        on_run_started(run_started_at)
    min_redetect_conf = 0.01
    step_index = 0
    previous_screen: ScreenState | None = None
    previous_action: Action | None = None
    previous_action_feedback: ActionFeedback | None = None
    last_action_summary: str | None = None
    last_target_identity: str | None = None
    last_surface_identity: str | None = None
    no_effect_state = NoEffectTrackingState()

    logger.info(
        "runner_case case_id=%s title=%s",
        context.request.case.case_id,
        context.request.case.title,
    )
    initial_ready_checked = False

    while True:
        if should_stop():
            stop_reason = "stop_requested"
            logger.info("run stopped: %s", stop_reason)
            publish_stop(event_sink, step_index, stop_reason)
            return build_run_result(
                step_index=step_index,
                stop_reason=stop_reason,
                status="incomplete",
                last_action_summary=last_action_summary,
                last_target_identity=last_target_identity,
                last_surface_identity=last_surface_identity,
            )
        if not initial_ready_checked:
            wait_until_initial_screen_ready(context=context)
            ensure_context_prep_ready(context)
            initial_ready_checked = True

        on_step_started = getattr(context.brain, "on_step_started", None)
        if callable(on_step_started):
            on_step_started(step_index)
        publish_step_started(event_sink, step_index)
        begin_step_logs(context, step_index)

        prepared_or_stop = prepare_step_action(
            context=context,
            event_sink=event_sink,
            step_index=step_index,
            min_redetect_conf=min_redetect_conf,
            previous_screen=previous_screen,
            previous_action=previous_action,
            previous_action_feedback=previous_action_feedback,
            no_effect_state=no_effect_state,
            capture_screen_state=capture_screen_state,
            capture_settle_snapshot=capture_settle_snapshot,
        )
        if isinstance(prepared_or_stop, StepPreparationStop):
            finish_step_logs(context, step_index)
            return build_run_result(
                step_index=step_index,
                stop_reason=prepared_or_stop.reason,
                status="incomplete",
                last_action_summary=last_action_summary,
                last_target_identity=prepared_or_stop.last_target_identity,
                last_surface_identity=prepared_or_stop.last_surface_identity,
            )
        prepared = prepared_or_stop
        no_effect_state = prepared.no_effect_state
        last_target_identity = prepared.last_target_identity
        last_surface_identity = prepared.last_surface_identity

        action = prepared.action
        if action.type == ActionType.REDETECT:
            action = Action.wait(0.5, summary="等待")

        mapped_action = map_action_to_device(
            action,
            (prepared.image_w, prepared.image_h),
            prepared.device_size,
        )
        on_action_committed = getattr(context.brain, "on_action_committed", None)
        if callable(on_action_committed):
            on_action_committed(action)

        _log_selected_action(prepared, action, mapped_action, step_index)
        if action.type == ActionType.STOP:
            stop_reason = "agent_stop"
            last_action_summary = action.summary
            finish_step_logs(
                context,
                step_index,
                target_identity=prepared.screen.entry_identity,
                surface_identity=prepared.screen.surface_identity,
            )
            publish_stop(event_sink, step_index, stop_reason)
            return build_run_result(
                step_index=step_index + 1,
                stop_reason=stop_reason,
                status="completed",
                last_action_summary=last_action_summary,
                last_target_identity=last_target_identity,
                last_surface_identity=last_surface_identity,
            )

        _publish_action_execution_started(event_sink, step_index, prepared, mapped_action)
        execution = _execute_action(
            context=context,
            mapped_action=mapped_action,
            screen=prepared.screen,
            device_size=prepared.device_size,
            capture_screen_state=capture_screen_state,
        )
        normalized_action = execution.normalized_action
        last_action_summary = normalized_action.summary
        if not execution.executed:
            should_continue, previous_action_feedback = _handle_failed_execution(
                context=context,
                event_sink=event_sink,
                step_index=step_index,
                mapped_action=mapped_action,
                normalized_action=normalized_action,
                execution=execution,
                screen=prepared.screen,
            )
            if should_continue:
                previous_screen = prepared.screen
                previous_action = normalized_action
                last_app_state = safe_app_state(context)
                last_target_identity = last_app_state.entry_identity if last_app_state is not None else None
                last_surface_identity = last_app_state.surface_identity if last_app_state is not None else None
                step_index += 1
                continue
            raise ActionExecutionError(
                execution.error_message or f"{mapped_action.type.value} execution failed"
            )

        settle_result = settle_after_action(
            context=context,
            action=normalized_action,
            before=prepared.settle_before,
        )
        _publish_action_executed(
            event_sink=event_sink,
            step_index=step_index,
            normalized_action=normalized_action,
            execution=execution,
            settle_result=settle_result,
        )
        logger.info(
            "step=%s action_execution_completed action=%s duration_ms=%s warning_code=%s normalized=%s settle_status=%s",
            step_index,
            normalized_action.type.value,
            execution.duration_ms,
            execution.warning_code,
            summarize_action(normalized_action),
            settle_result.status,
        )
        previous_screen = prepared.screen
        previous_action = action
        previous_action_feedback = augment_runner_action_feedback(
            normalized_action,
            feedback=build_runner_action_feedback(normalized_action),
            duration_ms=execution.duration_ms,
            changes=settle_result.changes,
        )

        current_app_state = safe_app_state(context)
        finish_step_logs(
            context,
            step_index,
            target_identity=current_app_state.entry_identity if current_app_state is not None else None,
            surface_identity=current_app_state.surface_identity if current_app_state is not None else None,
        )
        result = context.monitor.on_step(current_app_state or context.device.app_current())
        if result.should_stop:
            logger.info("run stopped: %s", result.reason)
            publish_stop(event_sink, step_index, result.reason)
            return build_run_result(
                step_index=step_index + 1,
                stop_reason=result.reason,
                status="incomplete",
                last_action_summary=last_action_summary,
                last_target_identity=last_target_identity,
                last_surface_identity=last_surface_identity,
            )

        step_index += 1


def _log_selected_action(
    prepared: PreparedStepAction,
    action: Action,
    mapped_action: Action,
    step_index: int,
) -> None:
    logger.info(
        "step=%s action=%s target_identity=%s elements=%s raw=%s annotated=%s",
        step_index,
        action.type.value,
        prepared.screen.entry_identity,
        len(prepared.screen.elements),
        prepared.raw_path.name,
        prepared.annotated_path.name,
    )
    logger.info(
        "screen_size=%sx%s device_size=%sx%s",
        prepared.image_w,
        prepared.image_h,
        prepared.device_size[0],
        prepared.device_size[1],
    )
    if action.type == ActionType.CLICK and action.box:
        logger.info("click_box=%s mapped_box=%s", action.box, mapped_action.box)
        return
    if (
        action.type in {ActionType.SCROLL, ActionType.SWIPE}
        and action.direction
        and action.start_x_ratio is not None
        and action.start_y_ratio is not None
        and action.distance_ratio is not None
    ):
        logger.info(
            "%s_direction=%s %s_start_x_ratio=%s %s_start_y_ratio=%s %s_distance_ratio=%s mapped_start=%s mapped_end=%s",
            action.type.value,
            action.direction,
            action.type.value,
            action.start_x_ratio,
            action.type.value,
            action.start_y_ratio,
            action.type.value,
            action.distance_ratio,
            mapped_action.start,
            mapped_action.end,
        )
        return
    if action.type == ActionType.DRAG and action.start is not None and action.end is not None:
        logger.info(
            "drag_start=%s drag_end=%s drag_duration=%s mapped_start=%s mapped_end=%s",
            action.start,
            action.end,
            action.duration,
            mapped_action.start,
            mapped_action.end,
        )


def _publish_action_execution_started(
    event_sink: RunEventSink | None,
    step_index: int,
    prepared: PreparedStepAction,
    mapped_action: Action,
) -> None:
    if event_sink is None:
        return
    execution_started_payload: dict[str, object] = {
        "normalized_action": summarize_action(mapped_action),
    }
    if prepared.pre_execute_status is not None:
        execution_started_payload["pre_execute_status"] = prepared.pre_execute_status
    if prepared.pre_execute_rebound:
        execution_started_payload["pre_execute_rebound"] = True
    if prepared.pre_execute_target_stable_key is not None:
        execution_started_payload["target_stable_key"] = prepared.pre_execute_target_stable_key
    if prepared.pre_execute_target_match_strategy is not None:
        execution_started_payload["target_match_strategy"] = prepared.pre_execute_target_match_strategy
    event_sink(
        ActionExecutionStartedEvent(
            message=f"action execution started for step {step_index}",
            data=build_runner_action_event_payload(
                step=step_index,
                action=mapped_action.type.value,
                summary=mapped_action.summary,
                **execution_started_payload,
            ),
        )
    )
    logger.info(
        "step=%s action_execution_started action=%s normalized=%s",
        step_index,
        mapped_action.type.value,
        summarize_action(mapped_action),
    )


def _execute_action(
    *,
    context: RunContext,
    mapped_action: Action,
    screen: ScreenState,
    device_size: tuple[int, int],
    capture_screen_state: CaptureScreenState,
):
    def capture_observation(source: ObservationSnapshotSource) -> RuntimeObservationSnapshot:
        return capture_screen_state(
            context=context,
            screen_bgr=context.device.screenshot_bgr(),
            icon_conf=context.params.icon_conf,
            source=source,
            device_size=device_size,
        )

    if uses_high_level_execution(mapped_action):
        return context.high_level_actions.execute(
            mapped_action,
            screen,
            capture_observation,
        )
    atomic = context.executor.execute(mapped_action)
    return from_atomic_result(mapped_action, atomic)


def _handle_failed_execution(
    *,
    context: RunContext,
    event_sink: RunEventSink | None,
    step_index: int,
    mapped_action: Action,
    normalized_action: Action,
    execution,
    screen: ScreenState,
) -> tuple[bool, ActionFeedback]:
    current_app_state = safe_app_state(context)
    finish_step_logs(
        context,
        step_index,
        target_identity=current_app_state.entry_identity if current_app_state is not None else None,
        surface_identity=current_app_state.surface_identity if current_app_state is not None else None,
    )
    error_type = execution.error_type
    error_message = execution.error_message
    logger.error(
        "step=%s action_execution_failed action=%s timeout=%s duration_ms=%s error_type=%s error=%s warning_code=%s normalized=%s",
        step_index,
        mapped_action.type.value,
        execution.timed_out,
        execution.duration_ms,
        error_type,
        error_message,
        execution.warning_code,
        summarize_action(normalized_action),
    )
    if event_sink is not None:
        event_sink(
            ActionExecutionFailedEvent(
                message=f"action execution failed for step {step_index}",
                data=build_runner_action_event_payload(
                    step=step_index,
                    action=mapped_action.type.value,
                    summary=mapped_action.summary,
                    duration_ms=execution.duration_ms,
                    timed_out=execution.timed_out,
                    error_type=error_type,
                    error_message=error_message,
                    normalized_action=summarize_action(normalized_action),
                    postcheck_passed=execution.postcheck_passed,
                    postcheck_summary=execution.postcheck_summary,
                    recovery_attempted=execution.recovery_attempted,
                    recovery_summary=execution.recovery_summary,
                    keyboard_dismissed=execution.keyboard_dismissed,
                    keyboard_dismiss_summary=execution.keyboard_dismiss_summary,
                    warning_code=execution.warning_code,
                    warning_message=execution.warning_message,
                ),
            )
        )
    if execution.timed_out:
        raise ActionExecutionTimeoutError(
            execution.error_message or f"{mapped_action.type.value} execution timed out"
        )
    if not _is_recoverable_action_failure(normalized_action, execution.error_message):
        return False, build_failed_runner_action_feedback(
            action_type=normalized_action.type.value,
            arguments=summarize_action(normalized_action),
            error_type=error_type or "ActionExecutionError",
            error_message=error_message or f"{mapped_action.type.value} execution failed",
        )
    return True, build_failed_runner_action_feedback(
        action_type=normalized_action.type.value,
        arguments=summarize_action(normalized_action),
        error_type=error_type or "ActionExecutionError",
        error_message=error_message or f"{mapped_action.type.value} execution failed",
    )


def _publish_action_executed(
    *,
    event_sink: RunEventSink | None,
    step_index: int,
    normalized_action: Action,
    execution,
    settle_result: SettleResult,
) -> None:
    if event_sink is None:
        return
    event_sink(
        ActionExecutedEvent(
            message=f"action executed for step {step_index}",
            data=build_runner_action_event_payload(
                step=step_index,
                action=normalized_action.type.value,
                summary=normalized_action.summary,
                duration_ms=execution.duration_ms,
                timed_out=False,
                normalized_action=summarize_action(normalized_action),
                postcheck_passed=execution.postcheck_passed,
                postcheck_summary=execution.postcheck_summary,
                recovery_attempted=execution.recovery_attempted,
                recovery_summary=execution.recovery_summary,
                keyboard_dismissed=execution.keyboard_dismissed,
                keyboard_dismiss_summary=execution.keyboard_dismiss_summary,
                warning_code=execution.warning_code,
                warning_message=execution.warning_message,
                settle_status=settle_result.status,
                settle_summary=settle_result.summary,
                settle_timed_out=settle_result.timed_out,
            ),
        )
    )
def _is_recoverable_action_failure(action: Action, error_message: str | None) -> bool:
    return action.type == ActionType.SCROLL_UNTIL_TEXT and error_message in RECOVERABLE_SCROLL_UNTIL_TEXT_ERRORS
