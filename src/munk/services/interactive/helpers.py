from __future__ import annotations

from munk.agent_base.action import ActionExecutionResult, ActionType
from munk.agent_base.action.high_level import HighLevelActionResult
from munk.agent_base.action_annotation import annotate_action_targets
from munk.agent_base.base import ObservationSnapshotSource, RuntimeObservationSnapshot, ScreenState
from munk.agent_base.web_platform_context import build_web_platform_context
from munk.config.resolve import resolve_runtime_config
from munk.core import observe_action_result
from munk.core.action_targets import build_action_targets
from munk.device import CurrentAppState, SupportsSoftKeyboardBounds, SupportsSoftKeyboardVisibility
from munk.services.screen_state_builder import build_runtime_observation_snapshot

from .models import (
    InteractiveActionResult,
    InteractiveObservation,
    InteractiveSession,
    InteractiveStepRecord,
    InteractiveTargetSummary,
    now_iso,
)
from .session_context import InteractiveSessionContext


def capture_interactive_observation(
    *,
    session_id: str,
    context: InteractiveSessionContext,
) -> InteractiveObservation:
    screen = capture_screen_state(context).screen
    action_targets = build_action_targets(screen, max_elements=context.max_elements)
    targets = [
        InteractiveTargetSummary(
            target_id=target.target_id,
            label=target.label,
            kind=target.kind,
            source=target.source,
            box=target.box,
            resource_id=target.resource_id,
            text=target.text,
        )
        for target in action_targets
    ]
    annotated_image_bgr = None
    if screen.image_bgr is not None:
        annotated_image_bgr = annotate_action_targets(screen.image_bgr, action_targets)
    return InteractiveObservation(
        session_id=session_id,
        captured_at=now_iso(),
        screen=screen,
        targets=targets,
        summary=build_observation_summary(screen, targets),
        vl_max_side=resolve_runtime_config(context.resolved_config.config).vl_max_side,
        annotated_image_bgr=annotated_image_bgr,
    )


def capture_runtime_observation(
    *,
    context: InteractiveSessionContext,
    source: ObservationSnapshotSource,
) -> RuntimeObservationSnapshot:
    return capture_screen_state(context, source=source)


def capture_screen_state(
    context: InteractiveSessionContext,
    *,
    source: ObservationSnapshotSource = "step_pre_action",
) -> RuntimeObservationSnapshot:
    screen_bgr = context.device.screenshot_bgr()
    observation_tree = _capture_observation_tree(context)
    app_info = context.device.app_current()
    keyboard_visible, keyboard_bounds, keyboard_source = _read_soft_keyboard_state(context)
    image_h = int(screen_bgr.shape[0])
    image_w = int(screen_bgr.shape[1])
    keyboard_bounds = _scale_bounds_to_image(
        keyboard_bounds,
        device_size=context.device.window_size(),
        image_size=(image_w, image_h),
    )
    return build_runtime_observation_snapshot(
        perception=context.perception,
        screen_bgr=screen_bgr,
        observation_tree=observation_tree,
        entry_identity=app_info.entry_identity,
        surface_identity=app_info.surface_identity,
        platform=app_info.platform,
        icon_conf=context.icon_conf,
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


def build_observation_summary(
    screen: ScreenState,
    targets: list[InteractiveTargetSummary],
) -> str:
    entry = screen.entry_identity or "unknown"
    surface = screen.surface_identity or "unknown"
    return f"entry={entry}; surface={surface}; targets={len(targets)}"


def append_observation_step(
    session: InteractiveSession,
    observation: InteractiveObservation,
) -> InteractiveStepRecord:
    step = InteractiveStepRecord(
        step_index=session.step_count,
        kind="observation",
        timestamp=observation.captured_at,
        summary=observation.summary,
        observation=observation,
    )
    session.steps.append(step)
    session.step_count += 1
    session.updated_at = observation.captured_at
    session.last_observation = observation
    return step


def append_action_step(
    session: InteractiveSession,
    *,
    timestamp: str,
    summary: str,
    action_type: ActionType,
    action_result: InteractiveActionResult,
) -> InteractiveStepRecord:
    step = InteractiveStepRecord(
        step_index=session.step_count,
        kind="action",
        timestamp=timestamp,
        summary=summary,
        action_type=action_type,
        action_result=action_result,
    )
    session.steps.append(step)
    session.step_count += 1
    session.updated_at = timestamp
    session.last_observation = action_result.after
    return step


def summarize_action_execution(
    *,
    execution: HighLevelActionResult | ActionExecutionResult,
    before,
    after,
) -> str:
    if not execution.executed:
        error = execution.error_message or "action failed"
        return f"executed=no; error={error}"
    observation = observe_action_result(before.screen, after.screen)
    summary = observation.summary
    warning_code = getattr(execution, "warning_code", None)
    if warning_code:
        summary = f"{summary}; warning={warning_code}"
    return summary


def close_interactive_context(context: InteractiveSessionContext) -> None:
    device = context.device
    close = getattr(device, "close", None)
    if callable(close):
        close()


def _capture_observation_tree(context: InteractiveSessionContext):
    try:
        return context.device.capture_observation_tree()
    except Exception:
        return None


def _build_platform_context(
    *,
    app_info: CurrentAppState,
    observation_tree,
    keyboard_visible: bool | None,
    keyboard_bounds: tuple[int, int, int, int] | None,
    keyboard_source: str | None,
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


def _read_soft_keyboard_state(
    context: InteractiveSessionContext,
) -> tuple[bool | None, tuple[int, int, int, int] | None, str | None]:
    keyboard_visible: bool | None = None
    keyboard_bounds: tuple[int, int, int, int] | None = None
    keyboard_source: str | None = None
    if isinstance(context.device, SupportsSoftKeyboardVisibility):
        try:
            keyboard_visible = context.device.is_soft_keyboard_visible()
        except Exception:
            keyboard_visible = None
    if isinstance(context.device, SupportsSoftKeyboardBounds):
        try:
            keyboard_bounds = context.device.get_soft_keyboard_bounds()
            if keyboard_bounds is not None:
                keyboard_source = "device"
                if keyboard_visible is None:
                    keyboard_visible = True
        except Exception:
            keyboard_bounds = None
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
    return (left, top, right, bottom)
