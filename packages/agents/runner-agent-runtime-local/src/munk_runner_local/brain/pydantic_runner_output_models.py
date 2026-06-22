from __future__ import annotations

import math
from typing import Annotated, Literal

from munk.agent_base.llm import coerce_json_container_string
from pydantic import BaseModel, Field, field_validator, model_validator

from munk_runner_local.brain.pydantic_runner_models import TextMatchArgs


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


class EditTextActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["edit_text"] = Field(default="edit_text")
    mode: Literal["append", "replace"] = Field(
        description="Use 'append' to type into the current focus or an optional target. Use 'replace' to focus a target, clear it, then type the new text.",
    )
    target_id: int | None = Field(
        default=None,
        description="Required for 'replace'. Optional for 'append'.",
    )
    text: str
    dismiss_keyboard: bool | None = Field(
        default=None,
        description="Defaults to false for 'append' and true for 'replace'.",
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value, field_name="text")

    @model_validator(mode="after")
    def validate_input_shape(self) -> "EditTextActionSubmission":
        if self.mode == "replace":
            if self.target_id is None:
                raise ValueError("target_id is required for replace mode")
            if self.dismiss_keyboard is None:
                self.dismiss_keyboard = True
            return self
        if self.dismiss_keyboard is None:
            self.dismiss_keyboard = False
        return self


class AnchoredGestureActionSubmissionBase(RunnerActionSubmissionBase):
    anchor_target_id: int | None = Field(
        default=None,
        description="Optional visible target id used to anchor the gesture start near that control.",
    )
    distance: float | None = Field(
        default=None,
        description="Optional normalized gesture travel ratio in the range (0.0, 1.0].",
    )

    @field_validator("anchor_target_id")
    @classmethod
    def validate_anchor_target_id(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("anchor_target_id must be positive")
        return value

    @field_validator("distance")
    @classmethod
    def validate_distance(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("distance must be finite")
        if value <= 0 or value > 1.0:
            raise ValueError("distance must be between 0.0 and 1.0")
        return value


class RevealMoreActionSubmission(AnchoredGestureActionSubmissionBase):
    action_type: Literal["reveal_more"] = Field(default="reveal_more")
    direction: Literal["up", "down"] = Field(
        description="Content direction to reveal: down shows lower content, up moves toward higher content.",
    )
    start_y_ratio: float | None = Field(
        default=None,
        description="Optional normalized vertical gesture start ratio in the range [0.0, 1.0].",
    )

    @field_validator("start_y_ratio")
    @classmethod
    def validate_start_y_ratio(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("start_y_ratio must be finite")
        if not (0.0 <= value <= 1.0):
            raise ValueError("start_y_ratio must be between 0.0 and 1.0")
        return value


class SwipeActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["swipe"] = Field(default="swipe")
    direction: Literal["left", "right"] = Field(
        description="Horizontal finger gesture direction: left swipes leftward, right swipes rightward.",
    )
    distance: float | None = Field(
        default=None,
        description="Optional normalized gesture travel ratio in the range (0.0, 1.0].",
    )
    start_x_ratio: float | None = Field(
        default=None,
        description="Optional normalized horizontal gesture start ratio in the range [0.0, 1.0].",
    )

    @field_validator("distance")
    @classmethod
    def validate_distance(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("distance must be finite")
        if value <= 0 or value > 1.0:
            raise ValueError("distance must be between 0.0 and 1.0")
        return value

    @field_validator("start_x_ratio")
    @classmethod
    def validate_start_x_ratio(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("start_x_ratio must be finite")
        if not (0.0 <= value <= 1.0):
            raise ValueError("start_x_ratio must be between 0.0 and 1.0")
        return value


class DragActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["drag"] = Field(default="drag")
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration_sec: float | None = Field(
        default=None,
        description="Optional drag duration in seconds. Uses the runtime default when omitted.",
    )

    @field_validator("duration_sec")
    @classmethod
    def validate_duration_sec(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return _validate_finite_non_negative(value, field_name="duration_sec")


class PullToRefreshActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["pull_to_refresh"] = Field(default="pull_to_refresh")
    start_x_ratio: float | None = Field(default=None, description="Optional normalized screen start x ratio in the range [0.0, 1.0].")
    start_y_ratio: float | None = Field(default=None, description="Optional normalized screen start y ratio in the range [0.0, 1.0].")
    distance_ratio: float | None = Field(
        default=None,
        description="Optional normalized gesture travel along the vertical axis in the range (0.0, 1.0].",
    )

    @field_validator("start_x_ratio", "start_y_ratio")
    @classmethod
    def validate_start_ratio(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("start ratio values must be finite")
        if not (0.0 <= value <= 1.0):
            raise ValueError("start ratio values must be between 0.0 and 1.0")
        return value

    @field_validator("distance_ratio")
    @classmethod
    def validate_distance_ratio(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("distance_ratio must be finite")
        if value <= 0 or value > 1.0:
            raise ValueError("distance_ratio must be between 0.0 and 1.0")
        return value


class SimpleActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal[
        "dismiss_soft_keyboard",
        "back",
        "home",
        "restart_app",
        "redetect",
        "stop",
    ] = Field(default="dismiss_soft_keyboard")


class WaitForTextActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["wait_for_text"] = Field(default="wait_for_text")
    match_type: Literal["any_of_texts", "all_texts", "none_of_texts"] = Field(
        description="Whole-screen text match mode. Choose any_of_texts, all_texts, or none_of_texts.",
    )
    texts: list[str] = Field(
        description="Stable visible texts to match against the whole-screen text snapshot. Use a short string list, not one long sentence.",
    )
    timeout_sec: float

    @field_validator("texts", mode="before")
    @classmethod
    def coerce_texts(cls, value: object) -> object:
        return coerce_json_container_string(value)

    @field_validator("timeout_sec")
    @classmethod
    def validate_timeout_sec(cls, value: float) -> float:
        return _validate_finite_non_negative(value, field_name="timeout_sec")

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, value: list[str]) -> list[str]:
        return TextMatchArgs(match_type="any_of_texts", texts=value).texts

    def to_text_match_args(self) -> TextMatchArgs:
        return TextMatchArgs(match_type=self.match_type, texts=self.texts)


class ScrollUntilTextActionSubmission(RunnerActionSubmissionBase):
    action_type: Literal["scroll_until_text"] = Field(default="scroll_until_text")
    match_type: Literal["any_of_texts", "all_texts", "none_of_texts"] = Field(
        description="Whole-screen text match mode. Choose any_of_texts, all_texts, or none_of_texts.",
    )
    texts: list[str] = Field(
        description="Stable visible texts to match against the whole-screen text snapshot. Use a short string list, not one long sentence.",
    )
    direction: Literal["down", "up"] = Field(
        default="down",
        description="Content direction to reveal while searching for the whole-screen text match.",
    )
    max_attempts: int = 8

    @field_validator("texts", mode="before")
    @classmethod
    def coerce_texts(cls, value: object) -> object:
        return coerce_json_container_string(value)

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_attempts must be positive")
        return value

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, value: list[str]) -> list[str]:
        return TextMatchArgs(match_type="any_of_texts", texts=value).texts

    def to_text_match_args(self) -> TextMatchArgs:
        return TextMatchArgs(match_type=self.match_type, texts=self.texts)


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
    | EditTextActionSubmission
    | RevealMoreActionSubmission
    | SwipeActionSubmission
    | DragActionSubmission
    | PullToRefreshActionSubmission
    | SimpleActionSubmission
    | WaitForTextActionSubmission
    | ScrollUntilTextActionSubmission
    | WaitActionSubmission,
    Field(discriminator="action_type"),
]
RunnerActionOutputModels = (
    ClickActionSubmission,
    LongPressActionSubmission,
    EditTextActionSubmission,
    RevealMoreActionSubmission,
    SwipeActionSubmission,
    DragActionSubmission,
    PullToRefreshActionSubmission,
    SimpleActionSubmission,
    WaitForTextActionSubmission,
    ScrollUntilTextActionSubmission,
    WaitActionSubmission,
)
