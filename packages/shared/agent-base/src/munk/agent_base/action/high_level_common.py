from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..base import ObservationSnapshotSource, RuntimeObservationSnapshot
from ..types import Action, ActionType
from .executor import ActionExecutionResult

ObservationRefresher = Callable[[ObservationSnapshotSource], RuntimeObservationSnapshot]

KEYBOARD_INPUT_CLASS_TOKENS = ("edittext", "textfield", "textinput")
TEXT_RECENTER_TARGET_RATIO = 0.5
TEXT_RECENTER_EPSILON_RATIO = 0.02
TEXT_RECENTER_MAX_DISTANCE_RATIO = 0.5
TEXT_RECENTER_START_Y_RATIO = 0.5
SCROLL_UNTIL_TEXT_NOT_FOUND_ERROR = "text_not_found_after_scroll_attempts"
SCROLL_UNTIL_TEXT_STAGNATED_ERROR = "scroll_stagnated_before_text_match"
HIGH_LEVEL_ACTION_TYPES = {
    ActionType.EDIT_TEXT,
    ActionType.DISMISS_SOFT_KEYBOARD,
    ActionType.RESTART_APP,
    ActionType.WAIT_FOR_TEXT,
    ActionType.SCROLL_UNTIL_TEXT,
}


@dataclass(frozen=True)
class HighLevelActionResult:
    executed: bool
    timed_out: bool
    action: Action
    normalized_action: Action
    duration_ms: int
    postcheck_passed: bool | None = None
    postcheck_summary: str | None = None
    recovery_attempted: bool = False
    recovery_summary: str | None = None
    keyboard_dismissed: bool | None = None
    keyboard_dismiss_summary: str | None = None
    warning_code: str | None = None
    warning_message: str | None = None
    error_type: str | None = None
    error_message: str | None = None


def uses_high_level_execution(action: Action) -> bool:
    return action.type in HIGH_LEVEL_ACTION_TYPES


def from_atomic_result(
    action: Action,
    result: ActionExecutionResult,
    *,
    normalized_action_override: Action | None = None,
    executed_override: bool | None = None,
    postcheck_passed: bool | None = None,
    postcheck_summary: str | None = None,
    recovery_attempted: bool = False,
    recovery_summary: str | None = None,
    keyboard_dismissed: bool | None = None,
    keyboard_dismiss_summary: str | None = None,
    warning_code: str | None = None,
    warning_message: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> HighLevelActionResult:
    return HighLevelActionResult(
        executed=result.executed if executed_override is None else executed_override,
        timed_out=result.timed_out,
        action=action,
        normalized_action=(
            result.normalized_action
            if normalized_action_override is None
            else normalized_action_override
        ),
        duration_ms=result.duration_ms,
        postcheck_passed=postcheck_passed,
        postcheck_summary=postcheck_summary,
        recovery_attempted=recovery_attempted,
        recovery_summary=recovery_summary,
        keyboard_dismissed=keyboard_dismissed,
        keyboard_dismiss_summary=keyboard_dismiss_summary,
        warning_code=warning_code,
        warning_message=warning_message,
        error_type=error_type if error_type is not None else result.error_type,
        error_message=error_message if error_message is not None else result.error_message,
    )
