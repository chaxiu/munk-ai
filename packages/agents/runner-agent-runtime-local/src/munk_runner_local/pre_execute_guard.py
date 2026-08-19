from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from munk.agent_base.action import Action, ActionType
from munk.agent_base.base import ScreenState
from munk.core.action_targets import TargetHandle, build_action_targets, find_action_target_by_box

from .context import RunContext
from .pre_execute_target_matcher import match_pre_execute_target
from .pre_execute_visual_fallback import match_visual_fallback_box, should_try_visual_fallback
from .step_observation import StepObservationState

_REBIND_HANDLE_UNSET = object()

PRE_EXECUTION_GUARDED_ACTION_TYPES = frozenset(
    {
        ActionType.CLICK,
        ActionType.LONG_PRESS,
        ActionType.EDIT_TEXT,
        ActionType.SET_VALUE,
    }
)


PRE_EXECUTE_STATUS_MATCHED = "matched"
PRE_EXECUTE_STATUS_PASSTHROUGH = "passthrough"
PRE_EXECUTE_STATUS_VISUAL_FALLBACK = "visual_fallback"
PRE_EXECUTE_STATUS_INVALIDATED = "invalidated"


@dataclass(frozen=True)
class PreExecuteGuardResult:
    action: Action
    state: StepObservationState
    rebound: bool = False
    invalidated: bool = False
    status: str | None = None
    stale_reason: str | None = None
    target_stable_key: str | None = None
    target_match_strategy: str | None = None


def guard_action_before_execution(
    *,
    context: RunContext,
    action: Action,
    decision_state: StepObservationState,
    refresh_state: Callable[[ScreenState | None], StepObservationState],
) -> PreExecuteGuardResult:
    if not should_guard_action_before_execution(action):
        return PreExecuteGuardResult(action=action, state=decision_state)
    if action.handle is not None and action.handle.kind == "dom":
        return _guard_dom_action_identity(
            action=action,
            decision_state=decision_state,
            refresh_state=refresh_state,
        )
    original_box = action.box
    if original_box is None:
        return PreExecuteGuardResult(action=action, state=decision_state)
    original_target = find_action_target_by_box(
        decision_state.screen,
        box=original_box,
        max_elements=context.params.runner_max_elements,
    )
    if original_target is None:
        return PreExecuteGuardResult(
            action=action,
            state=decision_state,
            status=PRE_EXECUTE_STATUS_PASSTHROUGH,
        )
    refreshed_state = refresh_state(decision_state.screen)
    refreshed_screen = refreshed_state.screen
    if refreshed_screen.entry_identity != decision_state.screen.entry_identity:
        return PreExecuteGuardResult(
            action=action,
            state=refreshed_state,
            invalidated=True,
            status=PRE_EXECUTE_STATUS_INVALIDATED,
            stale_reason="entry_identity_changed_before_execution",
            target_stable_key=original_target.stable_key,
        )
    if refreshed_screen.surface_identity != decision_state.screen.surface_identity:
        return PreExecuteGuardResult(
            action=action,
            state=refreshed_state,
            invalidated=True,
            status=PRE_EXECUTE_STATUS_INVALIDATED,
            stale_reason="surface_identity_changed_before_execution",
            target_stable_key=original_target.stable_key,
        )
    match_result = match_pre_execute_target(
        original_target=original_target,
        current_targets=build_action_targets(
            refreshed_screen,
            max_elements=context.params.runner_max_elements,
        ),
        action_type=action.type,
        screen_size=refreshed_screen.screen_size,
    )
    if match_result.resolved_target is not None and match_result.match_strategy is not None:
        rebound_target = match_result.resolved_target
        rebound_action = rebind_action_box(
            action,
            rebound_target.box,
            handle=rebound_target.handle,
        )
        return PreExecuteGuardResult(
            action=rebound_action,
            state=refreshed_state,
            rebound=rebound_target.box != original_box,
            status=PRE_EXECUTE_STATUS_MATCHED,
            target_stable_key=original_target.stable_key,
            target_match_strategy=match_result.match_strategy,
        )
    if should_try_visual_fallback(original_target=original_target, action_type=action.type):
        visual_result = match_visual_fallback_box(
            original_target=original_target,
            previous_image=decision_state.screen_bgr,
            current_image=refreshed_state.screen_bgr,
        )
        if visual_result.matched_box is not None:
            rebound_action = rebind_action_box(action, visual_result.matched_box)
            return PreExecuteGuardResult(
                action=rebound_action,
                state=refreshed_state,
                rebound=visual_result.matched_box != original_box,
                status=PRE_EXECUTE_STATUS_VISUAL_FALLBACK,
                target_stable_key=original_target.stable_key,
                target_match_strategy=visual_result.match_strategy,
            )
        return PreExecuteGuardResult(
            action=action,
            state=refreshed_state,
            invalidated=True,
            status=PRE_EXECUTE_STATUS_INVALIDATED,
            stale_reason=visual_result.stale_reason or match_result.stale_reason,
            target_stable_key=original_target.stable_key,
        )
    if match_result.resolved_target is not None:
        rebound_target = match_result.resolved_target
        rebound_action = rebind_action_box(
            action,
            rebound_target.box,
            handle=rebound_target.handle,
        )
        return PreExecuteGuardResult(
            action=rebound_action,
            state=refreshed_state,
            rebound=rebound_target.box != original_box,
            status=PRE_EXECUTE_STATUS_PASSTHROUGH,
            target_stable_key=original_target.stable_key,
            target_match_strategy=match_result.match_strategy,
        )
    if match_result.resolved_target is None:
        return PreExecuteGuardResult(
            action=action,
            state=refreshed_state,
            invalidated=True,
            status=PRE_EXECUTE_STATUS_INVALIDATED,
            stale_reason=match_result.stale_reason,
            target_stable_key=original_target.stable_key,
        )
    return PreExecuteGuardResult(action=action, state=refreshed_state)


def _guard_dom_action_identity(
    *,
    action: Action,
    decision_state: StepObservationState,
    refresh_state: Callable[[ScreenState | None], StepObservationState],
) -> PreExecuteGuardResult:
    # DOM selector identity must not be rebound to spatial boxes, but entry/surface
    # changes still invalidate the action before execution.
    refreshed_state = refresh_state(decision_state.screen)
    refreshed_screen = refreshed_state.screen
    if refreshed_screen.entry_identity != decision_state.screen.entry_identity:
        return PreExecuteGuardResult(
            action=action,
            state=refreshed_state,
            invalidated=True,
            status=PRE_EXECUTE_STATUS_INVALIDATED,
            stale_reason="entry_identity_changed_before_execution",
        )
    if refreshed_screen.surface_identity != decision_state.screen.surface_identity:
        return PreExecuteGuardResult(
            action=action,
            state=refreshed_state,
            invalidated=True,
            status=PRE_EXECUTE_STATUS_INVALIDATED,
            stale_reason="surface_identity_changed_before_execution",
        )
    return PreExecuteGuardResult(
        action=action,
        state=refreshed_state,
        status=PRE_EXECUTE_STATUS_PASSTHROUGH,
    )


def should_guard_action_before_execution(action: Action) -> bool:
    if action.type not in PRE_EXECUTION_GUARDED_ACTION_TYPES:
        return False
    if action.handle is not None and action.handle.kind == "dom":
        return True
    return action.box is not None


def rebind_action_box(
    action: Action,
    box: tuple[int, int, int, int],
    *,
    handle: TargetHandle | None | object = _REBIND_HANDLE_UNSET,
) -> Action:
    rebound_handle = action.handle if handle is _REBIND_HANDLE_UNSET else handle
    if action.type == ActionType.CLICK:
        return Action.click(
            box,
            summary=action.summary,
            handle=rebound_handle,  # type: ignore[arg-type]
            target_ref=action.target_ref,
        )
    if action.type == ActionType.LONG_PRESS:
        return Action.long_press(
            box,
            duration=action.duration,
            summary=action.summary,
            handle=rebound_handle,  # type: ignore[arg-type]
            target_ref=action.target_ref,
        )
    if action.type == ActionType.EDIT_TEXT:
        return Action.edit_text(
            text=action.text or "",
            mode=action.text_mode or "append",
            target_box=box,
            dismiss_keyboard=action.dismiss_keyboard,
            summary=action.summary,
            handle=rebound_handle,  # type: ignore[arg-type]
            target_ref=action.target_ref,
        )
    if action.type == ActionType.SET_VALUE:
        if not isinstance(rebound_handle, TargetHandle):
            return action
        updated_handle = rebound_handle if rebound_handle.box == box else replace(rebound_handle, box=box)
        return Action.set_value(
            value=action.text or "",
            handle=updated_handle,
            target_ref=action.target_ref or "",
            summary=action.summary,
        )
    return action
