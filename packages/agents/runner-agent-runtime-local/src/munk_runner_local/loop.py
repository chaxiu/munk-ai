from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Callable

import cv2
from munk.agent_base.action import Action, ActionExecutionError, ActionExecutionTimeoutError, ActionType
from munk.agent_base.action.high_level import uses_high_level_execution
from munk.agent_base.action_annotation import annotate_action_targets
from munk.agent_base.base import (
    ActionFeedback,
    ActionObservation,
    ObservationSnapshotSource,
    RuntimeObservationSnapshot,
    ScreenState,
)
from munk.agent_base.web_platform_context import build_web_platform_context
from munk.device import CurrentAppState, SupportsSoftKeyboardBounds, SupportsSoftKeyboardVisibility
from munk.perception import ObservationTree, to_json_dict
from munk.perception.image import BgrImage

from munk.core import map_action_to_device, observe_action_result, redetect_icon_conf
from munk.services.events import (
    ActionExecutedEvent,
    ActionExecutionFailedEvent,
    ActionExecutionStartedEvent,
    ActionProposedEvent,
    PerceptionCompletedEvent,
    RunEventSink,
    RunStoppedEvent,
    StepStartedEvent,
)
from munk.services.models import RunnerKernelResult
from munk.services.screen_state_builder import build_runtime_observation_snapshot
from munk.services.settle import (
    GenericSettleStrategy,
    SettleAppState,
    SettleComparableSnapshot,
    SettleResult,
    build_settle_snapshot,
    ready_settle_profile,
    strict_settle_profile,
)
from munk_runner_local.brain.runner_view import build_action_targets

from .action_feedback import build_runner_action_feedback
from .context import RunContext, prepare_runner_context

NO_EFFECT_WARNING_CODE = "device_call_succeeded_but_no_effect"
NO_EFFECT_THRESHOLD_ERROR = "device_call_succeeded_but_no_effect_threshold_exceeded"
NO_EFFECT_THRESHOLD = 3

logger = logging.getLogger(__name__)


def execute_run_loop(
    context: RunContext,
    event_sink: RunEventSink | None,
    should_stop: Callable[[], bool],
) -> RunnerKernelResult:
    min_redetect_conf = 0.01
    step_index = 0
    previous_screen: ScreenState | None = None
    previous_action: Action | None = None
    previous_action_feedback: ActionFeedback | None = None
    last_action_summary: str | None = None
    last_target_identity: str | None = None
    last_surface_identity: str | None = None
    consecutive_no_effect_action_type: ActionType | None = None
    consecutive_no_effect_count = 0

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
            return RunnerKernelResult(
                steps_completed=step_index,
                stop_reason=stop_reason,
                status="incomplete",
                last_action_summary=last_action_summary,
                last_target_identity=last_target_identity,
                last_surface_identity=last_surface_identity,
            )
        if not initial_ready_checked:
            wait_until_initial_screen_ready(context=context)
            _ensure_context_prep_ready(context)
            initial_ready_checked = True

        on_step_started = getattr(context.brain, "on_step_started", None)
        if callable(on_step_started):
            on_step_started(step_index)
        publish_step_started(event_sink, step_index)
        _begin_step_logs(context, step_index)
        screen_bgr = context.device.screenshot_bgr()
        image_h = int(screen_bgr.shape[0])
        image_w = int(screen_bgr.shape[1])
        device_size = context.device.window_size()
        raw_path = context.paths.raw_dir / f"step_{step_index:04d}.png"
        cv2.imwrite(str(raw_path), screen_bgr)
        redetect_index = 0

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
            if event_sink is not None:
                event_sink(
                    PerceptionCompletedEvent(
                        message=f"perception completed for step {step_index}",
                        data={
                            "step": step_index,
                            "element_count": len(screen.elements),
                            "icon_conf": current_conf,
                            "tree_available": screen.screen_frame.tree_available if screen.screen_frame is not None else False,
                            "tree_node_count": len(screen.screen_frame.tree_nodes) if screen.screen_frame is not None else 0,
                        },
                    )
                )
            last_target_identity = screen.entry_identity
            last_surface_identity = screen.surface_identity
            if previous_screen is not None and previous_action is not None:
                observation = observe_action_result(previous_screen, screen)
                warning_code = None
                warning_count = 0
                if not observation.screen_changed:
                    warning_code = NO_EFFECT_WARNING_CODE
                    if previous_action.type == consecutive_no_effect_action_type:
                        consecutive_no_effect_count += 1
                    else:
                        consecutive_no_effect_action_type = previous_action.type
                        consecutive_no_effect_count = 1
                    warning_count = consecutive_no_effect_count
                else:
                    consecutive_no_effect_action_type = None
                    consecutive_no_effect_count = 0
                observation = decorate_last_observation(
                    observation,
                    warning_code=warning_code,
                    action_type=previous_action.type,
                    consecutive_count=warning_count,
                )
                screen = ScreenState(
                    elements=screen.elements,
                    screen_size=screen.screen_size,
                    entry_identity=screen.entry_identity,
                    surface_identity=screen.surface_identity,
                    image_bgr=screen.image_bgr,
                    last_action_observation=observation,
                    last_action_feedback=previous_action_feedback,
                    screen_frame=screen.screen_frame,
                    platform=screen.platform,
                    platform_context=screen.platform_context,
                )
                if warning_code == NO_EFFECT_WARNING_CODE and warning_count >= NO_EFFECT_THRESHOLD:
                    _finish_step_logs(context, step_index)
                    if event_sink is not None:
                        event_sink(
                            RunStoppedEvent(
                                message=f"run stopped after stable no-effect threshold at step {step_index}",
                                data={
                                    "step": step_index,
                                    "action": previous_action.type.value,
                                    "summary": previous_action.summary,
                                    "reason": NO_EFFECT_THRESHOLD_ERROR,
                                    "warning_code": warning_code,
                                    "consecutive_no_effect_count": warning_count,
                                },
                            )
                        )
                    return RunnerKernelResult(
                        steps_completed=step_index,
                        stop_reason=NO_EFFECT_THRESHOLD_ERROR,
                        status="incomplete",
                        last_action_summary=last_action_summary,
                        last_target_identity=last_target_identity,
                        last_surface_identity=last_surface_identity,
                    )
            write_observation_artifacts(context, step_index, screen, observation_tree)
            settle_before = capture_settle_snapshot(
                context=context,
                screen_bgr=screen_bgr,
                observation_tree=observation_tree,
                device_size=device_size,
            )
            action = context.brain.next_action(screen)
            if event_sink is not None:
                event_sink(
                    ActionProposedEvent(
                        message=f"action proposed for step {step_index}",
                        data={
                            "step": step_index,
                            "action": action.type.value,
                            "summary": action.summary,
                            "redetect_index": redetect_index,
                        },
                    )
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
            break

        if action.type == ActionType.REDETECT:
            action = Action.wait(0.5, summary="等待")

        annotated_targets = build_action_targets(
            screen,
            max_elements=context.params.runner_max_elements,
        )
        annotated = annotate_action_targets(screen_bgr, annotated_targets)
        annotated_path = context.paths.annotated_dir / f"step_{step_index:04d}.png"
        cv2.imwrite(str(annotated_path), annotated)
        mapped_action = map_action_to_device(action, (image_w, image_h), device_size)

        logger.info(
            "step=%s action=%s target_identity=%s elements=%s raw=%s annotated=%s",
            step_index,
            action.type.value,
            screen.entry_identity,
            len(screen.elements),
            raw_path.name,
            annotated_path.name,
        )
        logger.info(
            "screen_size=%sx%s device_size=%sx%s",
            image_w,
            image_h,
            device_size[0],
            device_size[1],
        )
        if action.type == ActionType.CLICK and action.box:
            logger.info("click_box=%s mapped_box=%s", action.box, mapped_action.box)
        elif action.type in {ActionType.SCROLL, ActionType.SWIPE} and action.direction and action.distance_px is not None:
            logger.info(
                "%s_direction=%s %s_distance_px=%s mapped_start=%s mapped_end=%s",
                action.type.value,
                action.direction,
                action.type.value,
                action.distance_px,
                mapped_action.start,
                mapped_action.end,
            )

        if action.type == ActionType.STOP:
            stop_reason = "agent_stop"
            last_action_summary = action.summary
            _finish_step_logs(
                context,
                step_index,
                target_identity=screen.entry_identity,
                surface_identity=screen.surface_identity,
            )
            publish_stop(event_sink, step_index, stop_reason)
            return RunnerKernelResult(
                steps_completed=step_index + 1,
                stop_reason=stop_reason,
                status="completed",
                last_action_summary=last_action_summary,
                last_target_identity=last_target_identity,
                last_surface_identity=last_surface_identity,
            )

        normalized_action = mapped_action
        if event_sink is not None:
            event_sink(
                ActionExecutionStartedEvent(
                    message=f"action execution started for step {step_index}",
                    data={
                        "step": step_index,
                        "action": mapped_action.type.value,
                        "summary": mapped_action.summary,
                        "normalized_action": summarize_action(mapped_action),
                    },
                )
            )
        logger.info(
            "step=%s action_execution_started action=%s normalized=%s",
            step_index,
            mapped_action.type.value,
            summarize_action(mapped_action),
        )

        def capture_observation(source: ObservationSnapshotSource) -> RuntimeObservationSnapshot:
            return capture_screen_state(
                context=context,
                screen_bgr=context.device.screenshot_bgr(),
                icon_conf=context.params.icon_conf,
                source=source,
                device_size=device_size,
            )
        if uses_high_level_execution(mapped_action):
            execution = context.high_level_actions.execute(
                mapped_action,
                screen,
                capture_observation,
            )
        else:
            atomic = context.executor.execute(mapped_action)
            execution = context.high_level_actions._from_atomic_result(mapped_action, atomic)
        normalized_action = execution.normalized_action
        last_action_summary = normalized_action.summary
        if not execution.executed:
            current_app_state = _safe_app_state(context)
            _finish_step_logs(
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
                        data={
                            "step": step_index,
                            "action": mapped_action.type.value,
                            "summary": mapped_action.summary,
                            "duration_ms": execution.duration_ms,
                            "timed_out": execution.timed_out,
                            "error_type": error_type,
                            "error_message": error_message,
                            "normalized_action": summarize_action(normalized_action),
                            "postcheck_passed": execution.postcheck_passed,
                            "postcheck_summary": execution.postcheck_summary,
                            "recovery_attempted": execution.recovery_attempted,
                            "recovery_summary": execution.recovery_summary,
                            "keyboard_dismissed": execution.keyboard_dismissed,
                            "keyboard_dismiss_summary": execution.keyboard_dismiss_summary,
                            "warning_code": execution.warning_code,
                            "warning_message": execution.warning_message,
                        },
                    )
                )
            if execution.timed_out:
                raise ActionExecutionTimeoutError(
                    execution.error_message or f"{mapped_action.type.value} execution timed out"
                )
            raise ActionExecutionError(
                error_message or f"{mapped_action.type.value} execution failed"
            )
        settle_result: SettleResult = settle_after_action(
            context=context,
            before=settle_before,
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
        if event_sink is not None:
            event_sink(
                ActionExecutedEvent(
                    message=f"action executed for step {step_index}",
                    data={
                        "step": step_index,
                        "action": normalized_action.type.value,
                        "summary": normalized_action.summary,
                        "duration_ms": execution.duration_ms,
                        "timed_out": False,
                        "normalized_action": summarize_action(normalized_action),
                        "postcheck_passed": execution.postcheck_passed,
                        "postcheck_summary": execution.postcheck_summary,
                        "recovery_attempted": execution.recovery_attempted,
                        "recovery_summary": execution.recovery_summary,
                        "keyboard_dismissed": execution.keyboard_dismissed,
                        "keyboard_dismiss_summary": execution.keyboard_dismiss_summary,
                        "warning_code": execution.warning_code,
                        "warning_message": execution.warning_message,
                        "settle_status": settle_result.status,
                        "settle_summary": settle_result.summary,
                        "settle_timed_out": settle_result.timed_out,
                    },
                )
            )
        previous_screen = screen
        previous_action = action
        previous_action_feedback = build_runner_action_feedback(normalized_action)

        current_app_state = _safe_app_state(context)
        _finish_step_logs(
            context,
            step_index,
            target_identity=current_app_state.entry_identity if current_app_state is not None else None,
            surface_identity=current_app_state.surface_identity if current_app_state is not None else None,
        )
        result = context.monitor.on_step(current_app_state or context.device.app_current())
        if result.should_stop:
            logger.info("run stopped: %s", result.reason)
            publish_stop(event_sink, step_index, result.reason)
            return RunnerKernelResult(
                steps_completed=step_index + 1,
                stop_reason=result.reason,
                status="incomplete",
                last_action_summary=last_action_summary,
                last_target_identity=last_target_identity,
                last_surface_identity=last_surface_identity,
            )

        step_index += 1


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
            data={"step": step_index},
        )
    )


def publish_stop(event_sink: RunEventSink | None, step_index: int, reason: str | None) -> None:
    if event_sink is None:
        return
    event_sink(
        RunStoppedEvent(
            message=f"run stopped at step {step_index}",
            data={"step": step_index, "reason": reason},
        )
    )


def _begin_step_logs(context: RunContext, step_index: int) -> None:
    collector = context.log_collector
    if collector is None:
        return
    collector.begin_step(step_index)


def _finish_step_logs(
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


def _safe_app_state(context: RunContext) -> CurrentAppState | None:
    try:
        return context.device.app_current()
    except Exception as exc:  # noqa: BLE001
        logger.warning("app_current_after_step_failed error=%s", exc)
        return None


def _ensure_context_prep_ready(context: RunContext) -> None:
    if context.context_prep_output is None:
        future = context.context_prep_future
        if future is not None:
            try:
                context.context_prep_output = future.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("context_prep_future_failed error=%s", exc)
                context.context_prep_output = prepare_runner_context(context)
        else:
            context.context_prep_output = prepare_runner_context(context)
    apply_context_prep = getattr(context.brain, "apply_context_prep_output", None)
    if callable(apply_context_prep) and context.context_prep_output is not None:
        apply_context_prep(
            context.context_prep_output,
            knowledge_bundle=context.prepared_knowledge_bundle,
        )


def settle_after_action(
    *,
    context: RunContext,
    before: SettleComparableSnapshot,
) -> SettleResult:
    profile = strict_settle_profile()
    strategy = GenericSettleStrategy(
        poll_interval_sec=context.params.interval,
        profile=profile,
    )
    return strategy.settle(
        before=before,
        capture=lambda: capture_settle_snapshot(
            context=context,
            screen_bgr=context.device.screenshot_bgr(),
            observation_tree=_capture_observation_tree(context),
                device_size=context.device.window_size(),
        ),
        timeout_sec=context.params.settle_timeout,
    )


def wait_until_initial_screen_ready(
    *,
    context: RunContext,
) -> SettleResult | None:
    timeout_sec = max(0.0, context.params.initial_ready_timeout_sec)
    poll_interval_sec = max(0.0, context.params.interval)
    profile = ready_settle_profile()
    if timeout_sec <= 0.0:
        logger.info(
            "runner_initial_ready_result mode=%s status=skipped timed_out=False attempts=0 elapsed_ms=0 summary=disabled",
            profile.name,
        )
        return None
    device_size = context.device.window_size()
    baseline_screen_bgr = context.device.screenshot_bgr()
    baseline_observation_tree = _capture_observation_tree(context)
    baseline = capture_settle_snapshot(
        context=context,
        screen_bgr=baseline_screen_bgr,
        observation_tree=baseline_observation_tree,
        device_size=device_size,
    )
    logger.info(
        "runner_initial_ready_start mode=%s timeout_sec=%s poll_interval_sec=%s baseline_tree_present=%s baseline_surface=%s",
        profile.name,
        timeout_sec,
        poll_interval_sec,
        baseline.tree_signature is not None,
        baseline.app_state.surface_identity if baseline.app_state is not None else None,
    )
    strategy = GenericSettleStrategy(
        poll_interval_sec=poll_interval_sec,
        profile=profile,
    )
    result = strategy.settle(
        before=baseline,
        capture=lambda: capture_settle_snapshot(
            context=context,
            screen_bgr=context.device.screenshot_bgr(),
            observation_tree=_capture_observation_tree(context),
            device_size=context.device.window_size(),
        ),
        timeout_sec=timeout_sec,
    )
    logger.info(
        "runner_initial_ready_result mode=%s status=%s timed_out=%s attempts=%s elapsed_ms=%s summary=%s",
        profile.name,
        result.status,
        result.timed_out,
        result.attempts,
        result.elapsed_ms,
        result.summary,
    )
    return result


def capture_settle_snapshot(
    *,
    context: RunContext,
    screen_bgr: BgrImage,
    observation_tree: ObservationTree | None,
    device_size: tuple[int, int],
) -> SettleComparableSnapshot:
    app_info = context.device.app_current()
    _, keyboard_bounds, _ = _read_soft_keyboard_state(context)
    image_size = (int(screen_bgr.shape[1]), int(screen_bgr.shape[0]))
    keyboard_bounds = _scale_bounds_to_image(
        keyboard_bounds,
        device_size=device_size,
        image_size=image_size,
    )
    texts = context.perception.analyze_text(
        screen_bgr,
        excluded_regions=[keyboard_bounds] if keyboard_bounds is not None else None,
    )
    return build_settle_snapshot(
        observation_tree=observation_tree,
        texts=texts,
        app_state=_build_settle_app_state(app_info),
    )


def capture_screen_state(
    *,
    context: RunContext,
    screen_bgr: BgrImage,
    icon_conf: float,
    source: ObservationSnapshotSource,
    device_size: tuple[int, int],
) -> RuntimeObservationSnapshot:
    app_info = context.device.app_current()
    observation_tree = _capture_observation_tree(context)
    keyboard_visible, keyboard_bounds, keyboard_source = _read_soft_keyboard_state(context)
    image_h = int(screen_bgr.shape[0])
    image_w = int(screen_bgr.shape[1])
    keyboard_bounds = _scale_bounds_to_image(
        keyboard_bounds,
        device_size=device_size,
        image_size=(image_w, image_h),
    )
    return build_runtime_observation_snapshot(
        perception=context.perception,
        screen_bgr=screen_bgr,
        observation_tree=observation_tree,
        entry_identity=app_info.entry_identity,
        surface_identity=app_info.surface_identity,
        platform=app_info.platform,
        icon_conf=icon_conf,
        source=source,
        keyboard_visible=keyboard_visible,
        keyboard_bounds=keyboard_bounds,
        keyboard_source=keyboard_source,
        platform_context=_build_platform_context(
            app_info=app_info,
            observation_tree=observation_tree,
            keyboard_visible=keyboard_visible,
            keyboard_bounds=keyboard_bounds,
            keyboard_source=keyboard_source,
        ),
    )


def _capture_observation_tree(context: RunContext) -> ObservationTree | None:
    observation_tree = None
    try:
        observation_tree = context.device.capture_observation_tree()
    except Exception as exc:  # noqa: BLE001
        logger.warning("tree_dump_failed error=%s", exc)
    return observation_tree


def _build_platform_context(
    *,
    app_info,
    observation_tree: ObservationTree | None,
    keyboard_visible: bool | None = None,
    keyboard_bounds: tuple[int, int, int, int] | None = None,
    keyboard_source: str | None = None,
) -> dict[str, object] | None:
    if app_info.platform == "web":
        return build_web_platform_context(app_info=app_info, observation_tree=observation_tree)
    if app_info.platform == "ios":
        return {
            "keyboard_visible": keyboard_visible,
            "keyboard_bounds": list(keyboard_bounds) if keyboard_bounds is not None else None,
            "keyboard_source": keyboard_source,
        }
    return None


def _build_settle_app_state(app_info: CurrentAppState) -> SettleAppState | None:
    if app_info.surface_identity is None and app_info.load_state is None and app_info.title is None:
        return None
    return SettleAppState(
        surface_identity=app_info.surface_identity,
        load_state=app_info.load_state,
        title=app_info.title,
    )


def _read_soft_keyboard_state(
    context: RunContext,
) -> tuple[bool | None, tuple[int, int, int, int] | None, str | None]:
    keyboard_visible: bool | None = None
    keyboard_bounds: tuple[int, int, int, int] | None = None
    keyboard_source: str | None = None
    visibility_driver = context.device
    if isinstance(visibility_driver, SupportsSoftKeyboardVisibility):
        try:
            keyboard_visible = visibility_driver.is_soft_keyboard_visible()
        except Exception as exc:  # noqa: BLE001
            logger.warning("keyboard_visibility_failed error=%s", exc)
    bounds_driver = context.device
    if isinstance(bounds_driver, SupportsSoftKeyboardBounds):
        try:
            keyboard_bounds = bounds_driver.get_soft_keyboard_bounds()
            if keyboard_bounds is not None:
                keyboard_source = "device"
                if keyboard_visible is None:
                    keyboard_visible = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("keyboard_bounds_failed error=%s", exc)
    return keyboard_visible, keyboard_bounds, keyboard_source


def _scale_bounds_to_image(
    bounds: tuple[int, int, int, int] | None,
    *,
    device_size: tuple[int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    if bounds is None:
        return None
    device_w, device_h = device_size
    image_w, image_h = image_size
    if device_w <= 0 or device_h <= 0 or image_w <= 0 or image_h <= 0:
        return bounds
    if device_w == image_w and device_h == image_h:
        return bounds
    scale_x = image_w / float(device_w)
    scale_y = image_h / float(device_h)
    left = int(round(bounds[0] * scale_x))
    top = int(round(bounds[1] * scale_y))
    right = int(round(bounds[2] * scale_x))
    bottom = int(round(bounds[3] * scale_y))
    left = max(0, min(image_w - 1, left))
    top = max(0, min(image_h - 1, top))
    right = max(0, min(image_w - 1, right))
    bottom = max(0, min(image_h - 1, bottom))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


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
    if action.distance_px is not None:
        payload["distance_px"] = action.distance_px
    if action.text is not None:
        payload["text"] = action.text
    if action.locator is not None:
        payload["locator"] = action.locator.to_dict()
    if action.max_attempts is not None:
        payload["max_attempts"] = action.max_attempts
    if action.direction is not None:
        payload["direction"] = action.direction
    if action.dismiss_keyboard is not None:
        payload["dismiss_keyboard"] = action.dismiss_keyboard
    return payload


def write_observation_artifacts(
    context: RunContext,
    step_index: int,
    screen: ScreenState,
    observation_tree: ObservationTree | None,
) -> None:
    frame_dir = context.paths.observation_frames_dir
    diff_dir = context.paths.observation_diffs_dir
    tree_dir = context.paths.observation_tree_dir
    if frame_dir is not None and screen.screen_frame is not None:
        frame_path = frame_dir / f"step_{step_index:04d}.json"
        frame_path.write_text(
            json.dumps(to_json_dict(screen.screen_frame), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if diff_dir is not None and screen.last_action_observation is not None and screen.last_action_observation.screen_diff is not None:
        diff_path = diff_dir / f"step_{step_index:04d}.json"
        diff_path.write_text(
            json.dumps(to_json_dict(screen.last_action_observation.screen_diff), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if tree_dir is not None and observation_tree is not None:
        suffix = {
            "xml": ".xml",
            "json": ".json",
            "html": ".html",
        }[observation_tree.content_type]
        tree_path = tree_dir / f"step_{step_index:04d}{suffix}"
        tree_path.write_text(observation_tree.payload, encoding="utf-8")
