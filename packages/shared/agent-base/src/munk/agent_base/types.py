from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .locator import ElementLocator


class ActionType(str, Enum):
    CLICK = "click"
    LONG_PRESS = "long_press"
    INPUT = "input"
    SCROLL = "scroll"
    SWIPE = "swipe"
    CLEAR_AND_INPUT = "clear_and_input"
    DISMISS_SOFT_KEYBOARD = "dismiss_soft_keyboard"
    WAIT_FOR_ELEMENT = "wait_for_element"
    WAIT_UNTIL_GONE = "wait_until_gone"
    SCROLL_UNTIL_VISIBLE = "scroll_until_visible"
    BACK = "back"
    HOME = "home"
    WAIT = "wait"
    REDETECT = "redetect"
    STOP = "stop"


@dataclass(frozen=True)
class Action:
    type: ActionType
    box: tuple[int, int, int, int] | None = None
    point: tuple[int, int] | None = None
    text: str | None = None
    start: tuple[int, int] | None = None
    end: tuple[int, int] | None = None
    duration: float | None = None
    locator: ElementLocator | None = None
    max_attempts: int | None = None
    direction: str | None = None
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
    def scroll(
        *,
        direction: str,
        distance_px: int,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.SCROLL,
            direction=direction,
            distance_px=distance_px,
            summary=summary,
        )

    @staticmethod
    def swipe(
        *,
        direction: str,
        distance_px: int,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.SWIPE,
            direction=direction,
            distance_px=distance_px,
            summary=summary,
        )

    @staticmethod
    def clear_and_input(
        box: tuple[int, int, int, int],
        text: str,
        *,
        dismiss_keyboard: bool = True,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.CLEAR_AND_INPUT,
            box=box,
            text=text,
            dismiss_keyboard=dismiss_keyboard,
            summary=summary,
        )

    @staticmethod
    def dismiss_soft_keyboard(summary: str | None = None) -> "Action":
        return Action(type=ActionType.DISMISS_SOFT_KEYBOARD, summary=summary)

    @staticmethod
    def wait_for_element(
        locator: ElementLocator,
        timeout_sec: float,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.WAIT_FOR_ELEMENT,
            locator=locator,
            duration=timeout_sec,
            summary=summary,
        )

    @staticmethod
    def wait_until_gone(
        locator: ElementLocator,
        timeout_sec: float,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.WAIT_UNTIL_GONE,
            locator=locator,
            duration=timeout_sec,
            summary=summary,
        )

    @staticmethod
    def scroll_until_visible(
        locator: ElementLocator,
        *,
        direction: str,
        max_attempts: int,
        summary: str | None = None,
    ) -> "Action":
        return Action(
            type=ActionType.SCROLL_UNTIL_VISIBLE,
            locator=locator,
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
    def wait(duration: float, summary: str | None = None) -> "Action":
        return Action(type=ActionType.WAIT, duration=duration, summary=summary)

    @staticmethod
    def redetect(summary: str | None = None) -> "Action":
        return Action(type=ActionType.REDETECT, summary=summary)

    @staticmethod
    def stop(summary: str | None = None) -> "Action":
        return Action(type=ActionType.STOP, summary=summary)
