from __future__ import annotations

import time

from munk.device import DeviceDriver, SupportsAppLifecycle

from ..base import ScreenState
from ..types import Action, ActionType
from .executor import ActionExecutionError, ActionExecutor
from .high_level_common import (
    HIGH_LEVEL_ACTION_TYPES,
    KEYBOARD_INPUT_CLASS_TOKENS,
    ObservationRefresher,
    SCROLL_UNTIL_TEXT_NOT_FOUND_ERROR,
    SCROLL_UNTIL_TEXT_STAGNATED_ERROR,
    TEXT_RECENTER_EPSILON_RATIO,
    TEXT_RECENTER_MAX_DISTANCE_RATIO,
    TEXT_RECENTER_START_Y_RATIO,
    TEXT_RECENTER_TARGET_RATIO,
    HighLevelActionResult,
    uses_high_level_execution,
)
from .high_level_input import HighLevelInputHandler
from .high_level_text import HighLevelTextHandler

__all__ = [
    "HIGH_LEVEL_ACTION_TYPES",
    "KEYBOARD_INPUT_CLASS_TOKENS",
    "TEXT_RECENTER_TARGET_RATIO",
    "TEXT_RECENTER_EPSILON_RATIO",
    "TEXT_RECENTER_MAX_DISTANCE_RATIO",
    "TEXT_RECENTER_START_Y_RATIO",
    "SCROLL_UNTIL_TEXT_NOT_FOUND_ERROR",
    "SCROLL_UNTIL_TEXT_STAGNATED_ERROR",
    "ObservationRefresher",
    "HighLevelActionResult",
    "HighLevelActionService",
    "uses_high_level_execution",
]


class HighLevelActionService:
    def __init__(
        self,
        driver: DeviceDriver,
        executor: ActionExecutor,
        *,
        app_entry_identity: str | None = None,
    ) -> None:
        self._driver = driver
        self._app_entry_identity = app_entry_identity
        self._input_handler = HighLevelInputHandler(driver, executor)
        self._text_handler = HighLevelTextHandler(executor)

    def execute(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        started = time.monotonic()
        try:
            if action.type == ActionType.EDIT_TEXT:
                result = self._input_handler.execute_edit_text(action, screen, capture_observation)
            elif action.type == ActionType.DISMISS_SOFT_KEYBOARD:
                result = self._input_handler.execute_dismiss_soft_keyboard(
                    action,
                    screen,
                    capture_observation,
                )
            elif action.type == ActionType.RESTART_APP:
                result = self._execute_restart_app(action)
            elif action.type == ActionType.WAIT_FOR_TEXT:
                result = self._text_handler.execute_wait_for_text(
                    action,
                    screen,
                    capture_observation,
                )
            elif action.type == ActionType.SCROLL_UNTIL_TEXT:
                result = self._text_handler.execute_scroll_until_text(
                    action,
                    screen,
                    capture_observation,
                )
            else:
                raise ActionExecutionError(f"unsupported high-level action: {action.type.value}")
        except ActionExecutionError as exc:
            return HighLevelActionResult(
                executed=False,
                timed_out=False,
                action=action,
                normalized_action=action,
                duration_ms=self._elapsed_ms(started),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        return HighLevelActionResult(
            executed=result.executed,
            timed_out=result.timed_out,
            action=result.action,
            normalized_action=result.normalized_action,
            duration_ms=self._elapsed_ms(started),
            postcheck_passed=result.postcheck_passed,
            postcheck_summary=result.postcheck_summary,
            recovery_attempted=result.recovery_attempted,
            recovery_summary=result.recovery_summary,
            keyboard_dismissed=result.keyboard_dismissed,
            keyboard_dismiss_summary=result.keyboard_dismiss_summary,
            warning_code=result.warning_code,
            warning_message=result.warning_message,
            error_type=result.error_type,
            error_message=result.error_message,
        )

    def _execute_restart_app(self, action: Action) -> HighLevelActionResult:
        lifecycle_driver = self._driver
        if not isinstance(lifecycle_driver, SupportsAppLifecycle):
            raise ActionExecutionError("driver does not support app lifecycle")
        entry_identity = (self._app_entry_identity or "").strip()
        if not entry_identity:
            raise ActionExecutionError("restart_app requires a configured app entry_identity")
        lifecycle_driver.app_stop(entry_identity)
        lifecycle_driver.app_start(entry_identity)
        return HighLevelActionResult(
            executed=True,
            timed_out=False,
            action=action,
            normalized_action=action,
            duration_ms=0,
            postcheck_passed=True,
            postcheck_summary=f"app restarted: {entry_identity}",
        )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int(round((time.monotonic() - started) * 1000.0))
