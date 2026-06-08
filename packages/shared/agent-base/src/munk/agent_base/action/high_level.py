from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from munk.core.observation import observe_action_result
from munk.device import (
    DeviceDriver,
    SupportsSoftKeyboardDismiss,
    SupportsSoftKeyboardVisibility,
    SupportsTextClear,
)

from ..base import ObservationSnapshotSource, RuntimeObservationSnapshot, ScreenState
from ..locator import ElementLocator, find_matching_elements, find_matching_tree_nodes
from ..types import Action, ActionType
from .executor import ActionExecutionError, ActionExecutionResult, ActionExecutor

ObservationRefresher = Callable[[ObservationSnapshotSource], RuntimeObservationSnapshot]

KEYBOARD_INPUT_CLASS_TOKENS = ("edittext", "textfield", "textinput")
HIGH_LEVEL_ACTION_TYPES = {
    ActionType.INPUT,
    ActionType.CLEAR_AND_INPUT,
    ActionType.DISMISS_SOFT_KEYBOARD,
    ActionType.WAIT_FOR_ELEMENT,
    ActionType.WAIT_UNTIL_GONE,
    ActionType.SCROLL_UNTIL_VISIBLE,
}


def uses_high_level_execution(action: Action) -> bool:
    return action.type in HIGH_LEVEL_ACTION_TYPES


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


class HighLevelActionService:
    def __init__(self, driver: DeviceDriver, executor: ActionExecutor) -> None:
        self._driver = driver
        self._executor = executor

    def execute(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        started = time.monotonic()
        try:
            if action.type == ActionType.INPUT:
                result = self._execute_input(action, screen, capture_observation)
            elif action.type == ActionType.CLEAR_AND_INPUT:
                result = self._execute_clear_and_input(action, screen, capture_observation)
            elif action.type == ActionType.DISMISS_SOFT_KEYBOARD:
                result = self._execute_dismiss_soft_keyboard(action, screen, capture_observation)
            elif action.type == ActionType.WAIT_FOR_ELEMENT:
                result = self._execute_wait_for_element(action, screen, capture_observation)
            elif action.type == ActionType.WAIT_UNTIL_GONE:
                result = self._execute_wait_until_gone(action, screen, capture_observation)
            elif action.type == ActionType.SCROLL_UNTIL_VISIBLE:
                result = self._execute_scroll_until_visible(action, screen, capture_observation)
            else:
                raise ActionExecutionError(f"unsupported high-level action: {action.type.value}")
        except ActionExecutionError as exc:
            duration_ms = int(round((time.monotonic() - started) * 1000.0))
            return HighLevelActionResult(
                executed=False,
                timed_out=False,
                action=action,
                normalized_action=action,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        duration_ms = int(round((time.monotonic() - started) * 1000.0))
        return HighLevelActionResult(
            executed=result.executed,
            timed_out=result.timed_out,
            action=result.action,
            normalized_action=result.normalized_action,
            duration_ms=duration_ms,
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

    def _from_atomic_result(
        self,
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

    def _execute_input(
        self,
        action: Action,
        _screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        execution = self._executor.execute(Action.input_text(action.text or "", summary=action.summary))
        if not execution.executed:
            return self._from_atomic_result(action, execution)
        keyboard_dismissed = None
        keyboard_summary = None
        if action.dismiss_keyboard:
            post_input_screen = capture_observation("post_action_final").screen
            dismissed = self._maybe_dismiss_keyboard(
                post_input_screen,
                capture_observation,
                recent_input=True,
            )
            keyboard_dismissed = dismissed.keyboard_dismissed
            keyboard_summary = dismissed.keyboard_dismiss_summary
            if dismissed.executed is False:
                return self._from_atomic_result(
                    action,
                    execution,
                    postcheck_passed=True,
                    postcheck_summary="input executed",
                    keyboard_dismissed=keyboard_dismissed,
                    keyboard_dismiss_summary=keyboard_summary,
                    warning_code="input_keyboard_still_visible_after_dismiss",
                    warning_message="keyboard remained visible after dismiss attempt",
                )
        return self._from_atomic_result(
            action,
            execution,
            postcheck_passed=True,
            postcheck_summary="input executed",
            keyboard_dismissed=keyboard_dismissed,
            keyboard_dismiss_summary=keyboard_summary,
        )

    def _execute_clear_and_input(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        click_action = Action.click(action.box, summary=action.summary) if action.box is not None else action
        target_box_on_screen = self._map_box_to_screen_space(action.box, screen_size=screen.screen_size)
        focus_execution = self._executor.execute(click_action)
        if not focus_execution.executed:
            return self._from_atomic_result(action, focus_execution)
        if self._input_target_has_text(screen, target_box_on_screen):
            self._clear_text()
        input_execution = self._executor.execute(
            Action.input_text(action.text or "", summary=action.summary)
        )
        if not input_execution.executed:
            return self._from_atomic_result(action, input_execution)
        if action.dismiss_keyboard is not False:
            self._dismiss_keyboard_once(screen, recent_input=True)
        snapshot = capture_observation("post_action_final")
        text_applied = self._screen_contains_text(snapshot.screen, action.text or "")
        keyboard_ok = self._keyboard_requirement_satisfied(
            snapshot.screen,
            dismiss_keyboard=action.dismiss_keyboard is not False,
        )
        recovery_attempted = False
        recovery_parts: list[str] = []
        if not text_applied or not keyboard_ok:
            recovery_attempted = True
            if not text_applied:
                retry_focus = self._executor.execute(click_action)
                if retry_focus.executed:
                    retry_target_box_on_screen = self._map_box_to_screen_space(
                        action.box,
                        screen_size=snapshot.screen.screen_size,
                    )
                    if self._input_target_has_text(snapshot.screen, retry_target_box_on_screen):
                        self._clear_text()
                    retry_input = self._executor.execute(
                        Action.input_text(action.text or "", summary=action.summary)
                    )
                    if retry_input.executed:
                        input_execution = retry_input
                        recovery_parts.append("refocus_and_retry")
            if action.dismiss_keyboard is not False and not keyboard_ok:
                dismiss_result = self._dismiss_keyboard_once(snapshot.screen, recent_input=True)
                if dismiss_result.keyboard_dismissed:
                    recovery_parts.append("dismiss_keyboard")
            snapshot = capture_observation("post_action_retry")
            text_applied = self._screen_contains_text(snapshot.screen, action.text or "")
            keyboard_ok = self._keyboard_requirement_satisfied(
                snapshot.screen,
                dismiss_keyboard=action.dismiss_keyboard is not False,
            )
        warning_code, warning_message = self._build_clear_and_input_warning(
            text_applied=text_applied,
            keyboard_ok=keyboard_ok,
            dismiss_keyboard=action.dismiss_keyboard is not False,
        )
        return self._from_atomic_result(
            action,
            input_execution,
            normalized_action_override=action,
            postcheck_passed=text_applied and keyboard_ok,
            postcheck_summary=self._build_clear_and_input_postcheck_summary(
                action.text or "",
                text_applied=text_applied,
                keyboard_ok=keyboard_ok,
                dismiss_keyboard=action.dismiss_keyboard is not False,
            ),
            recovery_attempted=recovery_attempted,
            recovery_summary=", ".join(recovery_parts) if recovery_parts else None,
            keyboard_dismissed=keyboard_ok if action.dismiss_keyboard is not False else False,
            keyboard_dismiss_summary=(
                "keyboard dismissed"
                if action.dismiss_keyboard is not False and keyboard_ok
                else "keyboard still visible"
                if action.dismiss_keyboard is not False
                else "keyboard dismissal skipped"
            ),
            warning_code=warning_code,
            warning_message=warning_message,
        )

    def _execute_dismiss_soft_keyboard(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        result = self._maybe_dismiss_keyboard(screen, capture_observation)
        return HighLevelActionResult(
            executed=result.executed,
            timed_out=False,
            action=action,
            normalized_action=action,
            duration_ms=result.duration_ms,
            postcheck_passed=result.postcheck_passed,
            postcheck_summary=result.postcheck_summary,
            keyboard_dismissed=result.keyboard_dismissed,
            keyboard_dismiss_summary=result.keyboard_dismiss_summary,
            error_type=result.error_type,
            error_message=result.error_message,
        )

    def _execute_wait_for_element(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        locator = self._require_locator(action)
        deadline = time.monotonic() + (action.duration or 0.0)
        current = screen
        while True:
            if self._screen_matches_locator(current, locator):
                return HighLevelActionResult(
                    executed=True,
                    timed_out=False,
                    action=action,
                    normalized_action=action,
                    duration_ms=0,
                    postcheck_passed=True,
                    postcheck_summary=f"element_found: {locator.summary()}",
                )
            if time.monotonic() >= deadline:
                raise ActionExecutionError(f"wait_for_element timed out: {locator.summary()}")
            time.sleep(0.2)
            current = capture_observation("post_action_retry").screen

    def _execute_wait_until_gone(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        locator = self._require_locator(action)
        deadline = time.monotonic() + (action.duration or 0.0)
        current = screen
        while True:
            if not self._screen_matches_locator(current, locator):
                return HighLevelActionResult(
                    executed=True,
                    timed_out=False,
                    action=action,
                    normalized_action=action,
                    duration_ms=0,
                    postcheck_passed=True,
                    postcheck_summary=f"element_gone: {locator.summary()}",
                )
            if time.monotonic() >= deadline:
                raise ActionExecutionError(f"wait_until_gone timed out: {locator.summary()}")
            time.sleep(0.2)
            current = capture_observation("post_action_retry").screen

    def _execute_scroll_until_visible(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        locator = self._require_locator(action)
        current = screen
        attempts = action.max_attempts or 1
        stagnant_rounds = 0
        for _ in range(attempts):
            if self._screen_matches_locator(current, locator):
                return HighLevelActionResult(
                    executed=True,
                    timed_out=False,
                    action=action,
                    normalized_action=action,
                    duration_ms=0,
                    postcheck_passed=True,
                    postcheck_summary=f"element_found_after_scroll: {locator.summary()}",
                )
            scroll_action = self._build_scroll_action(action.direction or "down")
            execution = self._executor.execute(scroll_action)
            if not execution.executed:
                return self._from_atomic_result(action, execution)
            next_screen = capture_observation("post_action_retry").screen
            observation = observe_action_result(current, next_screen)
            if not observation.screen_changed:
                stagnant_rounds += 1
                if stagnant_rounds >= 2:
                    raise ActionExecutionError("target_still_missing_after_scroll")
            else:
                stagnant_rounds = 0
            current = next_screen
        raise ActionExecutionError("target_still_missing_after_scroll")

    def _maybe_dismiss_keyboard(
        self,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
        *,
        recent_input: bool = False,
    ) -> HighLevelActionResult:
        if not self._keyboard_likely_visible(screen, recent_input=recent_input):
            return HighLevelActionResult(
                executed=True,
                timed_out=False,
                action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
                normalized_action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
                duration_ms=0,
                postcheck_passed=True,
                postcheck_summary="keyboard not detected; skip dismiss",
                keyboard_dismissed=False,
                keyboard_dismiss_summary="keyboard not detected; skip dismiss",
            )
        dismiss_driver = self._driver
        if not isinstance(dismiss_driver, SupportsSoftKeyboardDismiss):
            raise ActionExecutionError("driver does not support dismiss_soft_keyboard")
        dismiss_driver.dismiss_soft_keyboard()
        current = capture_observation("post_action_retry").screen
        still_visible = self._keyboard_likely_visible(current)
        return HighLevelActionResult(
            executed=not still_visible,
            timed_out=False,
            action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
            normalized_action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
            duration_ms=0,
            postcheck_passed=not still_visible,
            postcheck_summary="keyboard dismissed" if not still_visible else "keyboard still visible",
            keyboard_dismissed=not still_visible,
            keyboard_dismiss_summary="keyboard dismissed" if not still_visible else "keyboard still visible",
            error_type="ActionExecutionError" if still_visible else None,
            error_message="keyboard_not_dismissed_after_input" if still_visible else None,
        )

    def _clear_text(self) -> None:
        clear_driver = self._driver
        if not isinstance(clear_driver, SupportsTextClear):
            raise ActionExecutionError("driver does not support clear_text")
        clear_driver.clear_text()

    def _keyboard_requirement_satisfied(self, screen: ScreenState, *, dismiss_keyboard: bool) -> bool:
        if not dismiss_keyboard:
            return True
        return not self._keyboard_likely_visible(screen, recent_input=True)

    def _dismiss_keyboard_once(
        self,
        screen: ScreenState,
        *,
        recent_input: bool = False,
    ) -> HighLevelActionResult:
        if not self._keyboard_likely_visible(screen, recent_input=recent_input):
            return HighLevelActionResult(
                executed=True,
                timed_out=False,
                action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
                normalized_action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
                duration_ms=0,
                postcheck_passed=True,
                postcheck_summary="keyboard not detected; skip dismiss",
                keyboard_dismissed=False,
                keyboard_dismiss_summary="keyboard not detected; skip dismiss",
            )
        dismiss_driver = self._driver
        if not isinstance(dismiss_driver, SupportsSoftKeyboardDismiss):
            raise ActionExecutionError("driver does not support dismiss_soft_keyboard")
        dismiss_driver.dismiss_soft_keyboard()
        return HighLevelActionResult(
            executed=True,
            timed_out=False,
            action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
            normalized_action=Action.dismiss_soft_keyboard(summary="dismiss keyboard"),
            duration_ms=0,
            postcheck_passed=True,
            postcheck_summary="keyboard dismiss attempted",
            keyboard_dismissed=True,
            keyboard_dismiss_summary="keyboard dismiss attempted",
        )

    @classmethod
    def _build_clear_and_input_warning(
        cls,
        *,
        text_applied: bool,
        keyboard_ok: bool,
        dismiss_keyboard: bool,
    ) -> tuple[str | None, str | None]:
        if text_applied and (keyboard_ok or not dismiss_keyboard):
            return None, None
        if not text_applied and dismiss_keyboard and not keyboard_ok:
            return (
                "clear_and_input_text_not_applied_and_keyboard_still_visible_after_retry",
                "text was not applied and keyboard remained visible after local retry",
            )
        if not text_applied:
            return (
                "clear_and_input_text_not_applied_after_retry",
                "text was not applied after local retry",
            )
        return (
            "clear_and_input_keyboard_still_visible_after_retry",
            "keyboard remained visible after local retry",
        )

    @staticmethod
    def _build_clear_and_input_postcheck_summary(
        text: str,
        *,
        text_applied: bool,
        keyboard_ok: bool,
        dismiss_keyboard: bool,
    ) -> str:
        parts = [f"text_applied={text!r}" if text_applied else f"text_missing={text!r}"]
        if dismiss_keyboard:
            parts.append("keyboard_dismissed" if keyboard_ok else "keyboard_still_visible")
        return "; ".join(parts)

    @classmethod
    def _input_target_has_text(
        cls,
        screen: ScreenState,
        target_box: tuple[int, int, int, int] | None,
    ) -> bool:
        frame = screen.screen_frame
        if frame is not None:
            for node in frame.tree_nodes:
                semantic = (node.semantic_role or "").lower()
                class_name = (node.class_name or "").lower()
                is_input = semantic == "input" or any(
                    token in class_name for token in KEYBOARD_INPUT_CLASS_TOKENS
                )
                if not is_input:
                    continue
                if target_box is not None and not cls._boxes_overlap(node.bounds, target_box):
                    continue
                if (node.text or "").strip():
                    return True
        for element in screen.elements:
            if target_box is not None and not cls._boxes_overlap(element.box, target_box):
                continue
            if (element.text or "").strip():
                return True
        return False

    @staticmethod
    def _boxes_overlap(
        left: tuple[int, int, int, int],
        right: tuple[int, int, int, int],
    ) -> bool:
        return not (
            left[2] <= right[0]
            or right[2] <= left[0]
            or left[3] <= right[1]
            or right[3] <= left[1]
        )

    def _map_box_to_screen_space(
        self,
        target_box: tuple[int, int, int, int] | None,
        *,
        screen_size: tuple[int, int],
    ) -> tuple[int, int, int, int] | None:
        if target_box is None:
            return None
        device_w, device_h = self._driver.window_size()
        screen_w, screen_h = screen_size
        if device_w <= 0 or device_h <= 0 or screen_w <= 0 or screen_h <= 0:
            return target_box
        if device_w == screen_w and device_h == screen_h:
            return target_box
        scale_x = screen_w / float(device_w)
        scale_y = screen_h / float(device_h)
        left = int(round(target_box[0] * scale_x))
        top = int(round(target_box[1] * scale_y))
        right = int(round(target_box[2] * scale_x))
        bottom = int(round(target_box[3] * scale_y))
        left = max(0, min(screen_w - 1, left))
        top = max(0, min(screen_h - 1, top))
        right = max(0, min(screen_w - 1, right))
        bottom = max(0, min(screen_h - 1, bottom))
        if right <= left or bottom <= top:
            return None
        return (left, top, right, bottom)

    @staticmethod
    def _screen_contains_text(screen: ScreenState, text: str) -> bool:
        needle = _normalize_text_for_match(text)
        if not needle:
            return False
        for element in screen.elements:
            if needle in _normalize_text_for_match(element.text):
                return True
        frame = screen.screen_frame
        if frame is None:
            return False
        for node in frame.tree_nodes:
            if needle in _normalize_text_for_match(node.text):
                return True
        return False

    @staticmethod
    def _screen_likely_has_visible_keyboard(screen: ScreenState, *, recent_input: bool = False) -> bool:
        _ = recent_input
        frame = screen.screen_frame
        if frame is None:
            return False
        for node in frame.tree_nodes:
            semantic = (node.semantic_role or "").lower()
            class_name = (node.class_name or "").lower()
            is_input = semantic == "input" or any(token in class_name for token in KEYBOARD_INPUT_CLASS_TOKENS)
            if not is_input:
                continue
            if node.focused:
                return True
        # A visible input field alone is too weak to conclude the soft keyboard
        # remains shown; treat explicit focus as the fallback signal.
        return False

    def _keyboard_likely_visible(self, screen: ScreenState, *, recent_input: bool = False) -> bool:
        visibility_driver = self._driver
        if isinstance(visibility_driver, SupportsSoftKeyboardVisibility):
            visible = visibility_driver.is_soft_keyboard_visible()
            if visible is not None:
                return visible
        frame = screen.screen_frame
        if frame is not None and frame.keyboard_visible is not None:
            return frame.keyboard_visible
        return self._screen_likely_has_visible_keyboard(screen, recent_input=recent_input)

    @staticmethod
    def _screen_matches_locator(screen: ScreenState, locator: ElementLocator) -> bool:
        if find_matching_elements(screen.elements, locator):
            return True
        frame = screen.screen_frame
        if frame is None:
            return False
        return bool(find_matching_tree_nodes(frame.tree_nodes, locator))

    @staticmethod
    def _require_locator(action: Action) -> ElementLocator:
        if action.locator is None:
            raise ActionExecutionError(f"{action.type.value} requires locator")
        return action.locator

    def _build_scroll_action(self, direction: str) -> Action:
        _, height = self._driver.window_size()
        top = max(1, int(height * 0.25))
        bottom = max(1, int(height * 0.75))
        distance_px = max(bottom - top, 1)
        if direction.lower() == "up":
            return Action.scroll(direction="up", distance_px=distance_px, summary="scroll up")
        return Action.scroll(direction="down", distance_px=distance_px, summary="scroll down")


def _normalize_text_for_match(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.casefold() if ch.isalnum())
