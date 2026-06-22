from __future__ import annotations

import logging
import time

from munk.agent_base.action import Action, ActionType
from munk.agent_base.base import ObservationSnapshotSource, RuntimeObservationSnapshot
from munk.agent_base.web_platform_context import build_web_platform_context
from munk.device import CurrentAppState, SupportsSoftKeyboardBounds, SupportsSoftKeyboardVisibility
from munk.perception import ObservationTree
from munk.perception.image import BgrImage
from munk.services.screen_state_builder import build_runtime_observation_snapshot
from munk.services.settle import (
    GenericSettleStrategy,
    SettleAppState,
    SettleComparableSnapshot,
    SettleProfile,
    SettleResult,
    build_settle_snapshot,
    diff_settle_snapshot,
    fixed_delay_settle,
    ratio_settle_profile,
    ready_settle_profile,
    strict_settle_profile,
)

from .context import RunContext
from .loop_debug import debug_report_cold_start_settle

POST_ACTION_DELAY_SEC = 0.2
POST_ACTION_SKIP_WAIT_TYPES = frozenset(
    {
        ActionType.EDIT_TEXT,
        ActionType.WAIT_FOR_TEXT,
        ActionType.SCROLL_UNTIL_TEXT,
        ActionType.WAIT,
    }
)

logger = logging.getLogger(__name__)


def _capture_timed_initial_ready_snapshot(
    *,
    context: RunContext,
    phase: str,
    attempt_index: int,
) -> SettleComparableSnapshot:
    total_started = time.monotonic()

    stage_started = time.monotonic()
    device_size = context.device.window_size()
    window_ms = int(round((time.monotonic() - stage_started) * 1000.0))

    stage_started = time.monotonic()
    screen_bgr = context.device.screenshot_bgr()
    screenshot_ms = int(round((time.monotonic() - stage_started) * 1000.0))

    observation_tree = None
    tree_ms = 0
    if not context.params.settle_ocr_only:
        stage_started = time.monotonic()
        observation_tree = _capture_observation_tree(context)
        tree_ms = int(round((time.monotonic() - stage_started) * 1000.0))

    capture_metrics: dict[str, object] = {}
    snapshot = capture_settle_snapshot(
        context=context,
        screen_bgr=screen_bgr,
        observation_tree=observation_tree,
        device_size=device_size,
        debug_metrics=capture_metrics,
    )
    total_ms = int(round((time.monotonic() - total_started) * 1000.0))

    debug_report_cold_start_settle(
        hypothesis_id="B" if phase == "baseline" else "C",
        location="packages/agents/runner-agent-runtime-local/src/munk_runner_local/loop_observation.py:initial_ready_capture",
        msg="[DEBUG] runner initial ready capture timing",
        data={
            "phase": phase,
            "attempt_index": attempt_index,
            "window_ms": window_ms,
            "screenshot_ms": screenshot_ms,
            "tree_ms": tree_ms,
            "total_ms": total_ms,
            "tree_present": observation_tree is not None,
            **capture_metrics,
        },
    )
    return snapshot


def settle_after_action(
    *,
    context: RunContext,
    action: Action,
    before: SettleComparableSnapshot,
) -> SettleResult:
    if should_skip_post_action_wait(action):
        return skipped_post_action_wait_result(before=before, action=action)
    if not should_use_post_action_settle(action):
        return fixed_delay_settle(
            before=before,
            capture=lambda: before,
            delay_sec=POST_ACTION_DELAY_SEC,
        )
    strategy = GenericSettleStrategy(
        poll_interval_sec=context.params.interval,
        profile=ratio_settle_profile(change_threshold=context.params.settle_ratio_threshold),
    )
    return strategy.settle(
        before=before,
        capture=lambda: capture_settle_snapshot(
            context=context,
            screen_bgr=context.device.screenshot_bgr(),
            observation_tree=_capture_settle_observation_tree(context),
            device_size=context.device.window_size(),
        ),
        timeout_sec=context.params.settle_timeout,
    )


def should_skip_post_action_wait(action: Action) -> bool:
    return action.type in POST_ACTION_SKIP_WAIT_TYPES


def should_use_post_action_settle(action: Action) -> bool:
    return action.type in {ActionType.CLICK, ActionType.PULL_TO_REFRESH, ActionType.RESTART_APP}


def skipped_post_action_wait_result(
    *,
    before: SettleComparableSnapshot,
    action: Action,
) -> SettleResult:
    baseline_diff = diff_settle_snapshot(before, before)
    return SettleResult(
        status="skipped",
        timed_out=False,
        attempts=0,
        elapsed_ms=0,
        final_snapshot=before,
        before_to_final=baseline_diff,
        previous_to_final=None,
        summary=(
            "settle=skipped; "
            f"reason=post_action_wait_disabled_for_{action.type.value}; "
            f"before_diff={baseline_diff.summary}"
        ),
    )


def wait_until_initial_screen_ready(
    *,
    context: RunContext,
) -> SettleResult | None:
    timeout_sec = max(0.0, context.params.initial_ready_timeout_sec)
    poll_interval_sec = max(0.0, context.params.interval)
    profile = _settle_profile_for_context(context, initial=True)
    mode_name = context.params.settle_mode if context.params.settle_mode == "delay" else profile.name
    debug_report_cold_start_settle(
        hypothesis_id="A",
        location="packages/agents/runner-agent-runtime-local/src/munk_runner_local/loop_observation.py:wait_until_initial_screen_ready:start",
        msg="[DEBUG] runner initial ready start",
        data={
            "mode": mode_name,
            "settle_mode": context.params.settle_mode,
            "timeout_sec": timeout_sec,
            "poll_interval_sec": poll_interval_sec,
            "stable_rounds": profile.stable_rounds,
        },
    )
    if timeout_sec <= 0.0:
        logger.info(
            "runner_initial_ready_result mode=%s status=skipped timed_out=False attempts=0 elapsed_ms=0 summary=disabled",
            mode_name,
        )
        return None
    baseline = _capture_timed_initial_ready_snapshot(
        context=context,
        phase="baseline",
        attempt_index=0,
    )
    logger.info(
        "runner_initial_ready_start mode=%s timeout_sec=%s poll_interval_sec=%s baseline_tree_present=%s baseline_surface=%s",
        mode_name,
        timeout_sec,
        poll_interval_sec,
        baseline.tree_signature is not None,
        baseline.app_state.surface_identity if baseline.app_state is not None else None,
    )
    if context.params.settle_mode == "delay":
        capture_attempt = 0

        def capture_delay_snapshot() -> SettleComparableSnapshot:
            nonlocal capture_attempt
            capture_attempt += 1
            return _capture_timed_initial_ready_snapshot(
                context=context,
                phase="delay_attempt",
                attempt_index=capture_attempt,
            )

        result = fixed_delay_settle(
            before=baseline,
            capture=capture_delay_snapshot,
            delay_sec=context.params.settle_delay_sec,
        )
        logger.info(
            "runner_initial_ready_result mode=%s status=%s timed_out=%s attempts=%s elapsed_ms=%s summary=%s",
            mode_name,
            result.status,
            result.timed_out,
            result.attempts,
            result.elapsed_ms,
            result.summary,
        )
        debug_report_cold_start_settle(
            hypothesis_id="D",
            location="packages/agents/runner-agent-runtime-local/src/munk_runner_local/loop_observation.py:wait_until_initial_screen_ready:delay_result",
            msg="[DEBUG] runner initial ready settle result",
            data={
                "mode": mode_name,
                "status": result.status,
                "timed_out": result.timed_out,
                "attempts": result.attempts,
                "elapsed_ms": result.elapsed_ms,
                "summary": result.summary,
            },
        )
        return result
    strategy = GenericSettleStrategy(
        poll_interval_sec=poll_interval_sec,
        profile=profile,
    )
    capture_attempt = 0

    def capture_attempt_snapshot() -> SettleComparableSnapshot:
        nonlocal capture_attempt
        capture_attempt += 1
        return _capture_timed_initial_ready_snapshot(
            context=context,
            phase="attempt",
            attempt_index=capture_attempt,
        )

    result = strategy.settle(
        before=baseline,
        capture=capture_attempt_snapshot,
        timeout_sec=timeout_sec,
    )
    logger.info(
        "runner_initial_ready_result mode=%s status=%s timed_out=%s attempts=%s elapsed_ms=%s summary=%s",
        mode_name,
        result.status,
        result.timed_out,
        result.attempts,
        result.elapsed_ms,
        result.summary,
    )
    debug_report_cold_start_settle(
        hypothesis_id="D",
        location="packages/agents/runner-agent-runtime-local/src/munk_runner_local/loop_observation.py:wait_until_initial_screen_ready:result",
        msg="[DEBUG] runner initial ready settle result",
        data={
            "mode": mode_name,
            "status": result.status,
            "timed_out": result.timed_out,
            "attempts": result.attempts,
            "elapsed_ms": result.elapsed_ms,
            "summary": result.summary,
        },
    )
    return result


def _settle_profile_for_context(
    context: RunContext,
    *,
    initial: bool = False,
) -> SettleProfile:
    mode = context.params.settle_mode
    if mode == "ratio":
        return ratio_settle_profile(change_threshold=context.params.settle_ratio_threshold)
    if mode == "strict":
        return strict_settle_profile()
    if initial:
        return ready_settle_profile()
    return strict_settle_profile()


def capture_settle_snapshot(
    *,
    context: RunContext,
    screen_bgr: BgrImage,
    observation_tree: ObservationTree | None,
    device_size: tuple[int, int],
    debug_metrics: dict[str, object] | None = None,
) -> SettleComparableSnapshot:
    total_started = time.monotonic()
    effective_observation_tree = None if context.params.settle_ocr_only else observation_tree
    app_info = None
    app_state_ms = 0
    if not context.params.settle_ocr_only:
        stage_started = time.monotonic()
        app_info = context.device.app_current()
        app_state_ms = int(round((time.monotonic() - stage_started) * 1000.0))
    stage_started = time.monotonic()
    _, keyboard_bounds, _ = _read_soft_keyboard_state(context)
    keyboard_ms = int(round((time.monotonic() - stage_started) * 1000.0))
    image_size = (int(screen_bgr.shape[1]), int(screen_bgr.shape[0]))
    keyboard_bounds = _scale_bounds_to_image(
        keyboard_bounds,
        device_size=device_size,
        image_size=image_size,
    )
    stage_started = time.monotonic()
    texts = context.perception.analyze_text(
        screen_bgr,
        excluded_regions=[keyboard_bounds] if keyboard_bounds is not None else None,
    )
    ocr_ms = int(round((time.monotonic() - stage_started) * 1000.0))
    stage_started = time.monotonic()
    snapshot = build_settle_snapshot(
        observation_tree=effective_observation_tree,
        texts=texts,
        app_state=_build_settle_app_state(app_info),
    )
    build_ms = int(round((time.monotonic() - stage_started) * 1000.0))
    if debug_metrics is not None:
        debug_metrics.update(
            {
                "app_state_ms": app_state_ms,
                "keyboard_ms": keyboard_ms,
                "ocr_ms": ocr_ms,
                "build_ms": build_ms,
                "capture_total_ms": int(round((time.monotonic() - total_started) * 1000.0)),
                "text_count": len(texts),
            }
        )
    return snapshot


def _capture_settle_observation_tree(context: RunContext) -> ObservationTree | None:
    if context.params.settle_ocr_only:
        return None
    return _capture_observation_tree(context)


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
    app_info: CurrentAppState,
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


def _build_settle_app_state(app_info: CurrentAppState | None) -> SettleAppState | None:
    if app_info is None:
        return None
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
