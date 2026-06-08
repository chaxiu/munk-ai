from __future__ import annotations

import math
from typing import Annotated, Literal

from munk.agent_base.llm import coerce_json_container_string
from pydantic import BaseModel, Field, field_validator, model_validator

from munk_runner_local.brain.pydantic_runner_models import ElementLocatorArgs


def _validate_non_empty(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


def _validate_finite_non_negative(value: float, *, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


class RunnerActionSubmissionBase(BaseModel):
    summary: str = Field(description="One-sentence action summary.")

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        return _validate_non_empty(value, field_name="summary")


class ClickActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["click"] = Field(default="click")
    target_id: int


class LongPressActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["long_press"] = Field(default="long_press")
    target_id: int
    duration_sec: float | None = Field(
        default=None,
        description="Optional hold duration in seconds. Uses the runtime default when omitted.",
    )

    @field_validator("duration_sec")
    @classmethod
    def validate_duration_sec(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("duration_sec must be finite")
        if value <= 0:
            raise ValueError("duration_sec must be positive")
        return value


class InputActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["input_text", "clear_and_input"] = Field(
        default="input_text",
        description="Input mode.",
    )
    target_id: int | None = Field(
        default=None,
        description="Required only for 'clear_and_input'.",
    )
    text: str
    dismiss_keyboard: bool | None = Field(
        default=None,
        description="Defaults to false for 'input_text' and true for 'clear_and_input'.",
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value, field_name="text")

    @model_validator(mode="after")
    def validate_input_shape(self) -> InputActionSubmission:
        if self.action_type == "clear_and_input":
            if self.target_id is None:
                raise ValueError("target_id is required for clear_and_input")
            if self.dismiss_keyboard is None:
                self.dismiss_keyboard = True
            return self
        if self.target_id is not None:
            raise ValueError("target_id must not be provided for input_text")
        if self.dismiss_keyboard is None:
            self.dismiss_keyboard = False
        return self


class ScrollActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["scroll"] = Field(default="scroll")
    direction: Literal["up", "down", "left", "right"] = Field(
        description="Content direction to reveal: down shows lower content, up moves toward higher content.",
    )
    distance_px: int = Field(description="Approximate content travel distance in pixels.")

    @field_validator("distance_px")
    @classmethod
    def validate_distance_px(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("distance_px must be positive")
        return value


class SwipeActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["swipe"] = Field(default="swipe")
    direction: Literal["up", "down", "left", "right"] = Field(
        description="Finger gesture direction: down drags downward, up swipes upward.",
    )
    distance_px: int = Field(description="Approximate finger travel distance in pixels.")

    @field_validator("distance_px")
    @classmethod
    def validate_distance_px(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("distance_px must be positive")
        return value


class SimpleActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal[
        "dismiss_soft_keyboard",
        "back",
        "home",
        "redetect",
        "stop",
    ] = Field(default="dismiss_soft_keyboard")


class LocatorWaitActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["wait_for_element", "wait_until_gone"] = Field(
        default="wait_for_element",
        description="Locator wait mode.",
    )
    locator: ElementLocatorArgs = Field(description="Structured locator object. Must be an object, not a JSON string.")
    timeout_sec: float

    @field_validator("locator", mode="before")
    @classmethod
    def coerce_locator(cls, value: object) -> object:
        return coerce_json_container_string(value)

    @field_validator("timeout_sec")
    @classmethod
    def validate_timeout_sec(cls, value: float) -> float:
        return _validate_finite_non_negative(value, field_name="timeout_sec")


class ScrollUntilVisibleActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["scroll_until_visible"] = Field(default="scroll_until_visible")
    locator: ElementLocatorArgs = Field(description="Structured locator object. Must be an object, not a JSON string.")
    direction: Literal["down", "up"] = Field(
        default="down",
        description="Content direction to reveal while searching for the locator.",
    )
    max_attempts: int = 5

    @field_validator("locator", mode="before")
    @classmethod
    def coerce_locator(cls, value: object) -> object:
        return coerce_json_container_string(value)

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_attempts must be positive")
        return value


class WaitActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["wait"] = Field(default="wait")
    duration: float

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        return _validate_finite_non_negative(value, field_name="duration")


RunnerActionOutput = Annotated[
    ClickActionSubmission
    | LongPressActionSubmission
    | InputActionSubmission
    | ScrollActionSubmission
    | SwipeActionSubmission
    | SimpleActionSubmission
    | LocatorWaitActionSubmission
    | ScrollUntilVisibleActionSubmission
    | WaitActionSubmission,
    Field(discriminator="action_type"),
]
RunnerActionOutputModels = (
    ClickActionSubmission,
    LongPressActionSubmission,
    InputActionSubmission,
    ScrollActionSubmission,
    SwipeActionSubmission,
    SimpleActionSubmission,
    LocatorWaitActionSubmission,
    ScrollUntilVisibleActionSubmission,
    WaitActionSubmission,
)
