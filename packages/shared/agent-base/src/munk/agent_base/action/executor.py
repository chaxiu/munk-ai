from __future__ import annotations

import math
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import cast

from munk.device import DeviceDriver, SupportsThreadBoundDeviceCalls

from ..types import Action, ActionType

DEFAULT_ACTION_TIMEOUT_SEC = 10.0
DEFAULT_LONG_PRESS_DURATION_SEC = 1.0
DEFAULT_SCROLL_DURATION_SEC = 0.5
MAX_WAIT_DURATION_SEC = 10.0
GESTURE_HORIZONTAL_EDGE_MARGIN_RATIO = 0.1
GESTURE_VERTICAL_EDGE_MARGIN_RATIO = 0.15


class ActionExecutionError(RuntimeError):
    """Raised when an action cannot be executed safely."""


class ActionExecutionTimeoutError(ActionExecutionError):
    """Raised when a device-side action does not finish before the deadline."""


@dataclass(frozen=True)
class ActionExecutionResult:
    executed: bool
    timed_out: bool
    action: Action
    normalized_action: Action
    duration_ms: int
    error_type: str | None = None
    error_message: str | None = None


class ActionExecutor:
    def __init__(self, device: DeviceDriver, action_timeout_sec: float = DEFAULT_ACTION_TIMEOUT_SEC) -> None:
        self.device = device
        self.action_timeout_sec = max(action_timeout_sec, 0.0)

    def execute(self, action: Action) -> ActionExecutionResult:
        started = time.monotonic()
        normalized_action = action
        try:
            normalized_action = self._normalize_action(action)
            self._execute_normalized(normalized_action)
        except ActionExecutionTimeoutError as exc:
            duration_ms = self._elapsed_ms(started)
            return ActionExecutionResult(
                executed=False,
                timed_out=True,
                action=action,
                normalized_action=normalized_action,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        except ActionExecutionError as exc:
            duration_ms = self._elapsed_ms(started)
            return ActionExecutionResult(
                executed=False,
                timed_out=False,
                action=action,
                normalized_action=normalized_action,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        duration_ms = self._elapsed_ms(started)
        return ActionExecutionResult(
            executed=True,
            timed_out=False,
            action=action,
            normalized_action=normalized_action,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int(round((time.monotonic() - started) * 1000.0))

    def _normalize_action(self, action: Action) -> Action:
        if action.type == ActionType.CLICK:
            return self._normalize_click(action)
        if action.type == ActionType.LONG_PRESS:
            return self._normalize_long_press(action)
        if action.type == ActionType.SCROLL:
            return self._normalize_scroll(action)
        if action.type == ActionType.SWIPE:
            return self._normalize_swipe(action)
        if action.type == ActionType.INPUT:
            return self._normalize_input(action)
        if action.type == ActionType.WAIT:
            return self._normalize_wait(action)
        if action.type in {ActionType.BACK, ActionType.HOME}:
            return action
        raise ActionExecutionError(f"unsupported executable action: {action.type.value}")

    def _normalize_click(self, action: Action) -> Action:
        if action.box is not None:
            return action
        if action.point is None:
            raise ActionExecutionError("click action requires box or point")
        width, height = self.device.window_size()
        x, y = action.point
        if width > 0 and height > 0:
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
        return Action.click_point((x, y), summary=action.summary)

    def _normalize_long_press(self, action: Action) -> Action:
        duration = action.duration if action.duration is not None else DEFAULT_LONG_PRESS_DURATION_SEC
        if not math.isfinite(duration):
            raise ActionExecutionError("long_press duration must be finite")
        if duration <= 0:
            raise ActionExecutionError("long_press duration must be positive")
        if action.box is not None:
            return Action.long_press(action.box, duration=duration, summary=action.summary)
        if action.point is None:
            raise ActionExecutionError("long_press action requires box or point")
        width, height = self.device.window_size()
        x, y = action.point
        if width > 0 and height > 0:
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
        return Action.long_press_point((x, y), duration=duration, summary=action.summary)

    def _normalize_scroll(self, action: Action) -> Action:
        if action.direction is None or action.distance_px is None:
            raise ActionExecutionError("scroll action requires direction and distance_px")
        width, height = self.device.window_size()
        start, end, distance_px = self._resolve_scroll_points(
            action.direction,
            action.distance_px,
            width,
            height,
        )
        return Action(
            type=ActionType.SCROLL,
            direction=action.direction,
            distance_px=distance_px,
            start=start,
            end=end,
            duration=DEFAULT_SCROLL_DURATION_SEC,
            summary=action.summary,
        )

    def _normalize_swipe(self, action: Action) -> Action:
        if action.direction is None or action.distance_px is None:
            raise ActionExecutionError("swipe action requires direction and distance_px")
        width, height = self.device.window_size()
        start, end, distance_px = self._resolve_swipe_points(
            action.direction,
            action.distance_px,
            width,
            height,
        )
        return Action(
            type=ActionType.SWIPE,
            direction=action.direction,
            distance_px=distance_px,
            start=start,
            end=end,
            duration=DEFAULT_SCROLL_DURATION_SEC,
            summary=action.summary,
        )

    def _normalize_input(self, action: Action) -> Action:
        text = (action.text or "").strip()
        if not text:
            raise ActionExecutionError("input action requires non-empty text")
        return Action.input_text(text, summary=action.summary)

    def _normalize_wait(self, action: Action) -> Action:
        duration = action.duration or 0.0
        if not math.isfinite(duration):
            raise ActionExecutionError("wait duration must be finite")
        duration = min(max(duration, 0.0), MAX_WAIT_DURATION_SEC)
        return Action.wait(duration, summary=action.summary)

    @staticmethod
    def _clamp_point(point: tuple[int, int], width: int, height: int) -> tuple[int, int]:
        x, y = point
        if width > 0 and height > 0:
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
        return (x, y)

    def _resolve_scroll_points(
        self,
        direction: str,
        distance_px: int,
        width: int,
        height: int,
    ) -> tuple[tuple[int, int], tuple[int, int], int]:
        return self._resolve_gesture_points(
            direction,
            distance_px,
            width,
            height,
            invert_vertical=True,
            invert_horizontal=True,
        )

    def _resolve_swipe_points(
        self,
        direction: str,
        distance_px: int,
        width: int,
        height: int,
    ) -> tuple[tuple[int, int], tuple[int, int], int]:
        return self._resolve_gesture_points(
            direction,
            distance_px,
            width,
            height,
            invert_vertical=False,
            invert_horizontal=False,
        )

    def _resolve_gesture_points(
        self,
        direction: str,
        distance_px: int,
        width: int,
        height: int,
        *,
        invert_vertical: bool,
        invert_horizontal: bool,
    ) -> tuple[tuple[int, int], tuple[int, int], int]:
        if not math.isfinite(float(distance_px)):
            raise ActionExecutionError("gesture distance_px must be finite")
        if distance_px <= 0:
            raise ActionExecutionError("gesture distance_px must be positive")
        if width <= 0 or height <= 0:
            raise ActionExecutionError("gesture action requires positive window size")

        min_x = int(round(width * GESTURE_HORIZONTAL_EDGE_MARGIN_RATIO))
        max_x = int(round(width * (1.0 - GESTURE_HORIZONTAL_EDGE_MARGIN_RATIO)))
        min_y = int(round(height * GESTURE_VERTICAL_EDGE_MARGIN_RATIO))
        max_y = int(round(height * (1.0 - GESTURE_VERTICAL_EDGE_MARGIN_RATIO)))
        resolved_direction = direction.lower()
        if resolved_direction == "down":
            if invert_vertical:
                start = (int(round(width * 0.5)), max_y)
                end_limit = min(start[1], min_y)
                end = (start[0], max(start[1] - distance_px, end_limit))
            else:
                start = (int(round(width * 0.5)), min_y)
                end_limit = max(start[1], max_y)
                end = (start[0], min(start[1] + distance_px, end_limit))
        elif resolved_direction == "up":
            if invert_vertical:
                start = (int(round(width * 0.5)), min_y)
                end_limit = max(start[1], max_y)
                end = (start[0], min(start[1] + distance_px, end_limit))
            else:
                start = (int(round(width * 0.5)), max_y)
                end_limit = min(start[1], min_y)
                end = (start[0], max(start[1] - distance_px, end_limit))
        elif resolved_direction == "right":
            if invert_horizontal:
                start = (max_x, int(round(height * 0.5)))
                end_limit = min(start[0], min_x)
                end = (max(start[0] - distance_px, end_limit), start[1])
            else:
                start = (min_x, int(round(height * 0.5)))
                end_limit = max(start[0], max_x)
                end = (min(start[0] + distance_px, end_limit), start[1])
        elif resolved_direction == "left":
            if invert_horizontal:
                start = (min_x, int(round(height * 0.5)))
                end_limit = max(start[0], max_x)
                end = (min(start[0] + distance_px, end_limit), start[1])
            else:
                start = (max_x, int(round(height * 0.5)))
                end_limit = min(start[0], min_x)
                end = (max(start[0] - distance_px, end_limit), start[1])
        else:
            raise ActionExecutionError("gesture direction must be one of: up, down, left, right")

        start = self._clamp_point(start, width, height)
        end = self._clamp_point(end, width, height)
        resolved_distance = abs(end[1] - start[1]) if start[0] == end[0] else abs(end[0] - start[0])
        return start, end, max(resolved_distance, 1)

    def _execute_normalized(self, action: Action) -> None:
        if action.type in {ActionType.CLICK, ActionType.LONG_PRESS}:
            if action.box is not None:
                x1, y1, x2, y2 = action.box
                cx = int(round((x1 + x2) / 2.0))
                cy = int(round((y1 + y2) / 2.0))
                if action.type == ActionType.CLICK:
                    self._run_device_call(self._click, action, cx, cy)
                else:
                    self._run_device_call(self._long_press, action, cx, cy, action.duration)
                return
            if action.point is None:
                raise ActionExecutionError(f"{action.type.value} action requires box or point")
            point = cast(tuple[int, int], action.point)
            point_x, point_y = point
            if action.type == ActionType.CLICK:
                self._run_device_call(self._click, action, point_x, point_y)
            else:
                self._run_device_call(self._long_press, action, point_x, point_y, action.duration)
            return
        if action.type in {ActionType.SCROLL, ActionType.SWIPE}:
            if action.start is None or action.end is None:
                raise ActionExecutionError(f"{action.type.value} action requires start and end")
            start = cast(tuple[int, int], action.start)
            end = cast(tuple[int, int], action.end)
            duration = action.duration
            self._run_device_call(self._scroll, action, start, end, duration)
            return
        if action.type == ActionType.INPUT:
            if not action.text:
                raise ActionExecutionError("input action requires non-empty text")
            text = cast(str, action.text)
            self._run_device_call(self._input_text, action, text)
            return
        if action.type == ActionType.BACK:
            self._run_device_call(self._press, action, "back")
            return
        if action.type == ActionType.HOME:
            self._run_device_call(self._press, action, "home")
            return
        if action.type == ActionType.WAIT:
            time.sleep(action.duration or 0.0)
            return
        raise ActionExecutionError(f"unsupported executable action: {action.type.value}")

    def _run_device_call(self, fn: Callable[..., None], action: Action, *args: object) -> None:
        timeout = self.action_timeout_sec
        if timeout <= 0 or self._must_run_device_call_inline():
            try:
                fn(*args)
            except Exception as exc:  # noqa: BLE001
                raise ActionExecutionError(str(exc)) from exc
            return
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="munk-action")
        try:
            future: Future[None] = executor.submit(fn, *args)
            try:
                future.result(timeout=timeout)
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, FutureTimeoutError):
                    raise ActionExecutionTimeoutError(
                        f"{action.type.value} action exceeded timeout {timeout:g}s"
                    ) from exc
                raise ActionExecutionError(str(exc)) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _must_run_device_call_inline(self) -> bool:
        device = self.device
        if isinstance(device, SupportsThreadBoundDeviceCalls):
            return not device.device_calls_thread_safe
        return False

    def _click(self, x: int, y: int) -> None:
        self.device.click(x, y)

    def _long_press(self, x: int, y: int, duration: float | None) -> None:
        self.device.long_press(x, y, duration)

    def _scroll(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None,
    ) -> None:
        self.device.scroll(start, end, duration)

    def _input_text(self, text: str) -> None:
        self.device.input_text(text)

    def _press(self, key: str) -> None:
        self.device.press(key)
