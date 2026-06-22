from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    CLICK = "click"
    LONG_PRESS = "long_press"
    INPUT = "input"
    EDIT_TEXT = "edit_text"
    SCROLL = "scroll"
    SWIPE = "swipe"
    DRAG = "drag"
    PULL_TO_REFRESH = "pull_to_refresh"
    DISMISS_SOFT_KEYBOARD = "dismiss_soft_keyboard"
    WAIT_FOR_TEXT = "wait_for_text"
    SCROLL_UNTIL_TEXT = "scroll_until_text"
    BACK = "back"
    HOME = "home"
    RESTART_APP = "restart_app"
    WAIT = "wait"
    REDETECT = "redetect"
    STOP = "stop"


@dataclass(frozen=True)
class Action:
    type: ActionType
    box: tuple[int, int, int, int] | None = None
    point: tuple[int, int] | None = None
    text: str | None = None
    text_mode: str | None = None
    start: tuple[int, int] | None = None
    end: tuple[int, int] | None = None
    duration: float | None = None
    match_type: str | None = None
    match_texts: tuple[str, ...] | None = None
    max_attempts: int | None = None
    direction: str | None = None
    start_x_ratio: float | None = None
    start_y_ratio: float | None = None
    distance_ratio: float | None = None
    distance_px: int | None = None
    dismiss_keyboard: bool | None = None
    summary: str | None = None

    @staticmethod
    def click(box: tuple[int, int, int, int], summary: str | None = None) -> "Action":
        return Action(type=ActionType.CLICK, box=box, summary=summary)

    @staticmethod
    def click_point(point: tuple[int, int], summary: str | None = None) -> "Action":
        return Action(type=ActionType.CLICK, point=point, summary=summary)

    @staticmethod
    def long_press(
        box: tuple[int, int, int, int],
        *,
        duration: float | None = None,
        summary: str | None = None,
    ) -> "Action":
        return Action(type=ActionType.LONG_PRESS, box=box, duration=duration, summary=summary)

    @staticmethod
    def long_press_point(
        point: tuple[int, int],
        *,
        duration: float | None = None,
        summary: str | None = None,
    ) -> "Action":
        return Action(type=ActionType.LONG_PRESS, point=point, duration=duration, summary=summary)

    @staticmethod
    def input_text(
        text: str,
        summary: str | None = None,
        *,
        dismiss_keyboard: bool | None = None,
    ) -> "Action":
        return Action(type=ActionType.INPUT, text=text, dismiss_keyboard=dismiss_keyboard, summary=summary)

    @staticmethod
    def edit_text(
        *,
        text: str,
        mode: str,
        target_box: tuple[int, int, int, int] | None = None,
        dismiss_keyboard: bool | None = None,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.EDIT_TEXT,
            box=target_box,
            text=text,
            text_mode=mode,
            dismiss_keyboard=dismiss_keyboard,
            summary=summary,
        )

    @staticmethod
    def scroll(
        *,
        direction: str,
        start_x_ratio: float,
        start_y_ratio: float,
        distance_ratio: float,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.SCROLL,
            direction=direction,
            start_x_ratio=start_x_ratio,
            start_y_ratio=start_y_ratio,
            distance_ratio=distance_ratio,
            summary=summary,
        )

    @staticmethod
    def swipe(
        *,
        direction: str,
        start_x_ratio: float,
        start_y_ratio: float,
        distance_ratio: float,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.SWIPE,
            direction=direction,
            start_x_ratio=start_x_ratio,
            start_y_ratio=start_y_ratio,
            distance_ratio=distance_ratio,
            summary=summary,
        )

    @staticmethod
    def drag(
        *,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.DRAG,
            start=start,
            end=end,
            duration=duration,
            summary=summary,
        )

    @staticmethod
    def pull_to_refresh(
        *,
        start_x_ratio: float | None = None,
        start_y_ratio: float | None = None,
        distance_ratio: float | None = None,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.PULL_TO_REFRESH,
            start_x_ratio=start_x_ratio,
            start_y_ratio=start_y_ratio,
            distance_ratio=distance_ratio,
            summary=summary,
        )

    @staticmethod
    def dismiss_soft_keyboard(summary: str | None = None) -> "Action":
        return Action(type=ActionType.DISMISS_SOFT_KEYBOARD, summary=summary)

    @staticmethod
    def wait_for_text(
        *,
        match_type: str,
        texts: list[str] | tuple[str, ...],
        timeout_sec: float,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.WAIT_FOR_TEXT,
            match_type=match_type,
            match_texts=tuple(texts),
            duration=timeout_sec,
            summary=summary,
        )

    @staticmethod
    def scroll_until_text(
        *,
        match_type: str,
        texts: list[str] | tuple[str, ...],
        direction: str,
        max_attempts: int,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.SCROLL_UNTIL_TEXT,
            match_type=match_type,
            match_texts=tuple(texts),
            direction=direction,
            max_attempts=max_attempts,
            summary=summary,
        )

    @staticmethod
    def back(summary: str | None = None) -> "Action":
        return Action(type=ActionType.BACK, summary=summary)

    @staticmethod
    def home(summary: str | None = None) -> "Action":
        return Action(type=ActionType.HOME, summary=summary)

    @staticmethod
    def restart_app(summary: str | None = None) -> "Action":
        return Action(type=ActionType.RESTART_APP, summary=summary)

    @staticmethod
    def wait(duration: float, summary: str | None = None) -> "Action":
        return Action(type=ActionType.WAIT, duration=duration, summary=summary)

    @staticmethod
    def redetect(summary: str | None = None) -> "Action":
        return Action(type=ActionType.REDETECT, summary=summary)

    @staticmethod
    def stop(summary: str | None = None) -> "Action":
        return Action(type=ActionType.STOP, summary=summary)
