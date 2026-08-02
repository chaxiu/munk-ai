from __future__ import annotations

from munk.device import (
    DeviceDriver,
    SupportsSoftKeyboardDismiss,
    SupportsSoftKeyboardVisibility,
    SupportsTextClear,
)

from ..base import ScreenState
from ..types import Action
from .executor import ActionExecutor, ActionExecutionError
from .high_level_common import HighLevelActionResult, ObservationRefresher, from_atomic_result
from .high_level_screen import (
    input_target_has_text,
    map_box_to_screen_space,
    screen_contains_text,
    screen_likely_has_visible_keyboard,
)


class HighLevelInputHandler:
    def __init__(self, driver: DeviceDriver, executor: ActionExecutor) -> None:
        self._driver = driver
        self._executor = executor

    def execute_edit_text(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        mode = self._require_edit_text_mode(action)
        if mode == "append":
            return self._execute_edit_text_append(action, capture_observation)
        return self._execute_edit_text_replace(action, screen, capture_observation)

    def execute_dismiss_soft_keyboard(
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

    def _execute_edit_text_append(
        self,
        action: Action,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        if action.box is not None:
            focus_execution = self._executor.execute(Action.click(action.box, summary=action.summary))
            if not focus_execution.executed:
                return from_atomic_result(action, focus_execution)
        execution = self._executor.execute(
            Action.input_text(
                action.text or "",
                summary=action.summary,
                dismiss_keyboard=action.dismiss_keyboard,
            )
        )
        if not execution.executed:
            return from_atomic_result(action, execution)
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
                return from_atomic_result(
                    action,
                    execution,
                    postcheck_passed=True,
                    postcheck_summary="input executed",
                    keyboard_dismissed=keyboard_dismissed,
                    keyboard_dismiss_summary=keyboard_summary,
                    warning_code="input_keyboard_still_visible_after_dismiss",
                    warning_message="keyboard remained visible after dismiss attempt",
                )
        return from_atomic_result(
            action,
            execution,
            postcheck_passed=True,
            postcheck_summary="text appended",
            keyboard_dismissed=keyboard_dismissed,
            keyboard_dismiss_summary=keyboard_summary,
        )

    def _execute_edit_text_replace(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        if action.box is None:
            raise ActionExecutionError("edit_text replace requires target box")
        click_action = Action.click(action.box, summary=action.summary)
        target_box_on_screen = map_box_to_screen_space(
            action.box,
            device_size=self._driver.window_size(),
            screen_size=screen.screen_size,
        )
        focus_execution = self._executor.execute(click_action)
        if not focus_execution.executed:
            return from_atomic_result(action, focus_execution)
        if input_target_has_text(screen, target_box_on_screen):
            self._clear_text()
        input_execution = self._executor.execute(
            Action.input_text(action.text or "", summary=action.summary)
        )
        if not input_execution.executed:
            return from_atomic_result(action, input_execution)
        dismiss_requested = action.dismiss_keyboard is not False
        soft_keyboard_applicable = self._supports_soft_keyboard_dismiss()
        if dismiss_requested and soft_keyboard_applicable:
            self._dismiss_keyboard_once(screen, recent_input=True)
        snapshot = capture_observation("post_action_final")
        text_applied = screen_contains_text(snapshot.screen, action.text or "")
        keyboard_ok = self._keyboard_requirement_satisfied(
            snapshot.screen,
            dismiss_keyboard=dismiss_requested,
        )
        recovery_attempted = False
        recovery_parts: list[str] = []
        if not text_applied or not keyboard_ok:
            recovery_attempted = True
            if not text_applied:
                retry_focus = self._executor.execute(click_action)
                if retry_focus.executed:
                    retry_target_box = map_box_to_screen_space(
                        action.box,
                        device_size=self._driver.window_size(),
                        screen_size=snapshot.screen.screen_size,
                    )
                    if input_target_has_text(snapshot.screen, retry_target_box):
                        self._clear_text()
                    retry_input = self._executor.execute(
                        Action.input_text(action.text or "", summary=action.summary)
                    )
                    if retry_input.executed:
                        input_execution = retry_input
                        recovery_parts.append("refocus_and_retry")
            if dismiss_requested and soft_keyboard_applicable and not keyboard_ok:
                dismiss_result = self._dismiss_keyboard_once(snapshot.screen, recent_input=True)
                if dismiss_result.keyboard_dismissed:
                    recovery_parts.append("dismiss_keyboard")
            snapshot = capture_observation("post_action_retry")
            text_applied = screen_contains_text(snapshot.screen, action.text or "")
            keyboard_ok = self._keyboard_requirement_satisfied(
                snapshot.screen,
                dismiss_keyboard=dismiss_requested,
            )
        warning_code, warning_message = self._build_edit_text_replace_warning(
            text_applied=text_applied,
            keyboard_ok=keyboard_ok,
            dismiss_keyboard=dismiss_requested and soft_keyboard_applicable,
        )
        return from_atomic_result(
            action,
            input_execution,
            normalized_action_override=action,
            postcheck_passed=text_applied and keyboard_ok,
            postcheck_summary=self._build_edit_text_replace_postcheck_summary(
                action.text or "",
                text_applied=text_applied,
                keyboard_ok=keyboard_ok,
                dismiss_keyboard=dismiss_requested,
                soft_keyboard_applicable=soft_keyboard_applicable,
            ),
            recovery_attempted=recovery_attempted,
            recovery_summary=", ".join(recovery_parts) if recovery_parts else None,
            keyboard_dismissed=(
                keyboard_ok if dismiss_requested and soft_keyboard_applicable else False
            ),
            keyboard_dismiss_summary=self._build_edit_text_replace_keyboard_summary(
                dismiss_keyboard=dismiss_requested,
                soft_keyboard_applicable=soft_keyboard_applicable,
                keyboard_ok=keyboard_ok,
            ),
            warning_code=warning_code,
            warning_message=warning_message,
        )

    def _maybe_dismiss_keyboard(
        self,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
        *,
        recent_input: bool = False,
    ) -> HighLevelActionResult:
        unsupported = self._unsupported_soft_keyboard_dismiss_result()
        if unsupported is not None:
            return unsupported
        if not self._keyboard_likely_visible(screen, recent_input=recent_input):
            return self._build_keyboard_result(
                executed=True,
                postcheck_passed=True,
                postcheck_summary="keyboard not detected; skip dismiss",
                keyboard_dismissed=False,
                keyboard_dismiss_summary="keyboard not detected; skip dismiss",
            )
        self._invoke_dismiss_soft_keyboard()
        current = capture_observation("post_action_retry").screen
        still_visible = self._keyboard_likely_visible(current)
        return self._build_keyboard_result(
            executed=not still_visible,
            postcheck_passed=not still_visible,
            postcheck_summary="keyboard dismissed" if not still_visible else "keyboard still visible",
            keyboard_dismissed=not still_visible,
            keyboard_dismiss_summary="keyboard dismissed" if not still_visible else "keyboard still visible",
            error_type="ActionExecutionError" if still_visible else None,
            error_message="keyboard_not_dismissed_after_input" if still_visible else None,
        )

    def _build_keyboard_result(
        self,
        *,
        executed: bool,
        postcheck_passed: bool,
        postcheck_summary: str,
        keyboard_dismissed: bool,
        keyboard_dismiss_summary: str,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> HighLevelActionResult:
        dismiss_action = Action.dismiss_soft_keyboard(summary="dismiss keyboard")
        return HighLevelActionResult(
            executed=executed,
            timed_out=False,
            action=dismiss_action,
            normalized_action=dismiss_action,
            duration_ms=0,
            postcheck_passed=postcheck_passed,
            postcheck_summary=postcheck_summary,
            keyboard_dismissed=keyboard_dismissed,
            keyboard_dismiss_summary=keyboard_dismiss_summary,
            error_type=error_type,
            error_message=error_message,
        )

    def _clear_text(self) -> None:
        clear_driver = self._driver
        if not isinstance(clear_driver, SupportsTextClear):
            raise ActionExecutionError("driver does not support clear_text")
        clear_driver.clear_text()

    def _keyboard_requirement_satisfied(self, screen: ScreenState, *, dismiss_keyboard: bool) -> bool:
        if not dismiss_keyboard:
            return True
        if not self._supports_soft_keyboard_dismiss():
            # Desktop/web drivers have no soft-keyboard contract; do not fail edit_text on it.
            return True
        return not self._keyboard_likely_visible(screen, recent_input=True)

    def _dismiss_keyboard_once(
        self,
        screen: ScreenState,
        *,
        recent_input: bool = False,
    ) -> HighLevelActionResult:
        unsupported = self._unsupported_soft_keyboard_dismiss_result()
        if unsupported is not None:
            return unsupported
        if not self._keyboard_likely_visible(screen, recent_input=recent_input):
            return self._build_keyboard_result(
                executed=True,
                postcheck_passed=True,
                postcheck_summary="keyboard not detected; skip dismiss",
                keyboard_dismissed=False,
                keyboard_dismiss_summary="keyboard not detected; skip dismiss",
            )
        self._invoke_dismiss_soft_keyboard()
        return self._build_keyboard_result(
            executed=True,
            postcheck_passed=True,
            postcheck_summary="keyboard dismiss attempted",
            keyboard_dismissed=True,
            keyboard_dismiss_summary="keyboard dismiss attempted",
        )

    def _supports_soft_keyboard_dismiss(self) -> bool:
        return isinstance(self._driver, SupportsSoftKeyboardDismiss)

    def _invoke_dismiss_soft_keyboard(self) -> None:
        dismiss_driver = self._driver
        if not isinstance(dismiss_driver, SupportsSoftKeyboardDismiss):
            raise ActionExecutionError("driver does not support dismiss_soft_keyboard")
        dismiss_driver.dismiss_soft_keyboard()

    def _unsupported_soft_keyboard_dismiss_result(self) -> HighLevelActionResult | None:
        if self._supports_soft_keyboard_dismiss():
            return None
        return self._build_keyboard_result(
            executed=True,
            postcheck_passed=True,
            postcheck_summary="soft keyboard dismiss not supported by driver",
            keyboard_dismissed=False,
            keyboard_dismiss_summary="soft keyboard dismiss not supported by driver",
        )

    @staticmethod
    def _build_edit_text_replace_warning(
        *,
        text_applied: bool,
        keyboard_ok: bool,
        dismiss_keyboard: bool,
    ) -> tuple[str | None, str | None]:
        if text_applied and (keyboard_ok or not dismiss_keyboard):
            return None, None
        if not text_applied and dismiss_keyboard and not keyboard_ok:
            return (
                "edit_text_replace_text_not_applied_and_keyboard_still_visible_after_retry",
                "text was not applied and keyboard remained visible after local retry",
            )
        if not text_applied:
            return (
                "edit_text_replace_text_not_applied_after_retry",
                "text was not applied after local retry",
            )
        return (
            "edit_text_replace_keyboard_still_visible_after_retry",
            "keyboard remained visible after local retry",
        )

    @staticmethod
    def _build_edit_text_replace_postcheck_summary(
        text: str,
        *,
        text_applied: bool,
        keyboard_ok: bool,
        dismiss_keyboard: bool,
        soft_keyboard_applicable: bool,
    ) -> str:
        parts = [f"text_applied={text!r}" if text_applied else f"text_missing={text!r}"]
        if dismiss_keyboard and soft_keyboard_applicable:
            parts.append("keyboard_dismissed" if keyboard_ok else "keyboard_still_visible")
        elif dismiss_keyboard:
            parts.append("keyboard_dismiss_not_applicable")
        return "; ".join(parts)

    @staticmethod
    def _build_edit_text_replace_keyboard_summary(
        *,
        dismiss_keyboard: bool,
        soft_keyboard_applicable: bool,
        keyboard_ok: bool,
    ) -> str:
        if not dismiss_keyboard:
            return "keyboard dismissal skipped"
        if not soft_keyboard_applicable:
            return "soft keyboard dismiss not supported by driver"
        if keyboard_ok:
            return "keyboard dismissed"
        return "keyboard still visible"

    def _keyboard_likely_visible(self, screen: ScreenState, *, recent_input: bool = False) -> bool:
        visibility_driver = self._driver
        if isinstance(visibility_driver, SupportsSoftKeyboardVisibility):
            visible = visibility_driver.is_soft_keyboard_visible()
            if visible is not None:
                return visible
        frame = screen.screen_frame
        if frame is not None and frame.keyboard_visible is not None:
            return frame.keyboard_visible
        return screen_likely_has_visible_keyboard(screen, recent_input=recent_input)

    @staticmethod
    def _require_edit_text_mode(action: Action) -> str:
        mode = (action.text_mode or "").strip().lower()
        if mode not in {"append", "replace"}:
            raise ActionExecutionError("edit_text requires text_mode of append or replace")
        return mode
