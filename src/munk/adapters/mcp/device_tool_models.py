from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DevicesListInput(BaseModel):
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform filter for discovered devices.",
    )


class DeviceStateInput(BaseModel):
    device_ref: str = Field(description="Target device reference to inspect.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional explicit platform filter used to disambiguate the device reference.",
    )


class DeviceUnlockInput(BaseModel):
    device_ref: str = Field(description="Target device reference to unlock.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional explicit platform filter used to disambiguate the device reference.",
    )
    strategy: Literal["swipe"] = Field(
        default="swipe",
        description="Device unlock strategy. V1 supports swipe only.",
    )


class AppLaunchInput(BaseModel):
    app_id: str = Field(description="Application identifier associated with the lifecycle action.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional explicit platform override used to derive the app target.",
    )
    device_ref: str | None = Field(default=None, description="Optional target device reference.")
    package: str | None = Field(default=None, description="Optional Android package name override.")
    bundle_id: str | None = Field(default=None, description="Optional iOS bundle identifier override.")
    base_url: str | None = Field(default=None, description="Optional web base URL override.")
    origin: str | None = Field(default=None, description="Optional web origin override.")
    headless: bool = Field(default=False, description="Whether to launch the web runtime headlessly.")
    assets_root: Path | None = Field(
        default=None,
        description="Optional assets root containing apps/ and plans/ for app target resolution.",
    )


class AppStopInput(BaseModel):
    app_id: str = Field(description="Application identifier associated with the lifecycle action.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional explicit platform override used to derive the app target.",
    )
    device_ref: str | None = Field(default=None, description="Optional target device reference.")
    package: str | None = Field(default=None, description="Optional Android package name override.")
    bundle_id: str | None = Field(default=None, description="Optional iOS bundle identifier override.")
    base_url: str | None = Field(default=None, description="Optional web base URL override.")
    origin: str | None = Field(default=None, description="Optional web origin override.")
    headless: bool = Field(default=False, description="Whether to launch the web runtime headlessly.")
    assets_root: Path | None = Field(
        default=None,
        description="Optional assets root containing apps/ and plans/ for app target resolution.",
    )


class AppInstallInput(BaseModel):
    app_id: str = Field(description="Application identifier associated with the lifecycle action.")
    artifact_path: Path = Field(
        description="Host workspace path to the application artifact to install. Android runtime stages it to a device tmp path before install.",
    )
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional explicit platform override used to derive the app target.",
    )
    device_ref: str | None = Field(default=None, description="Optional target device reference.")
    package: str | None = Field(default=None, description="Optional Android package name override.")
    bundle_id: str | None = Field(default=None, description="Optional iOS bundle identifier override.")
    base_url: str | None = Field(default=None, description="Optional web base URL override.")
    origin: str | None = Field(default=None, description="Optional web origin override.")
    headless: bool = Field(default=False, description="Whether to launch the web runtime headlessly.")
    assets_root: Path | None = Field(
        default=None,
        description="Optional assets root containing apps/ and plans/ for app target resolution.",
    )


class SessionStartInput(BaseModel):
    app_id: str = Field(description="Application identifier associated with the interactive session.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional explicit platform override used to derive the app target.",
    )
    device_ref: str | None = Field(default=None, description="Optional device reference to claim for the session.")
    package: str | None = Field(default=None, description="Optional Android package name override.")
    bundle_id: str | None = Field(default=None, description="Optional iOS bundle identifier override.")
    base_url: str | None = Field(default=None, description="Optional web base URL override.")
    origin: str | None = Field(default=None, description="Optional web origin override.")
    headless: bool = Field(default=False, description="Whether to launch the web runtime headlessly.")
    config_path: Path | None = Field(
        default=None,
        description="Optional path to an existing config file in the workspace. Leave unset to use default config resolution.",
    )


class SessionGetInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier.")


class SessionObserveInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier to observe.")
    detail: Literal["compact", "full"] = Field(
        default="compact",
        description="Observation payload detail level. Use compact by default and full for complete debugging payloads.",
    )
    include_screenshot: bool = Field(
        default=False,
        description="Whether to include the current observation screenshot as a saved PNG path.",
    )


class SessionsListInput(BaseModel):
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform filter for active interactive sessions.",
    )
    device_ref: str | None = Field(
        default=None,
        description="Optional device reference filter for active interactive sessions.",
    )
    app_id: str | None = Field(
        default=None,
        description="Optional app identifier filter for active interactive sessions.",
    )


class SessionActionInput(BaseModel):
    type: Literal[
        "click",
        "long_press",
        "input",
        "edit_text",
        "scroll",
        "swipe",
        "pull_to_refresh",
        "wait",
        "back",
        "home",
    ] = Field(
        description="Allowed interactive action type.",
    )
    target_id: int | None = Field(
        default=None,
        description="Optional target identifier from the latest session_observe result.",
    )
    resource_id: str | None = Field(
        default=None,
        description="Optional resource identifier fallback from the latest session_observe result.",
    )
    label: str | None = Field(
        default=None,
        description="Optional unique target label fallback from the latest session_observe result.",
    )
    box: tuple[int, int, int, int] | None = Field(
        default=None,
        description="Optional target box as left, top, right, bottom.",
    )
    point: tuple[int, int] | None = Field(default=None, description="Optional click point as x, y.")
    text: str | None = Field(default=None, description="Optional input text payload.")
    text_mode: Literal["append", "replace"] | None = Field(
        default=None,
        description="Optional edit_text mode. Use append to type into the current focus or target, replace to clear a target then type.",
    )
    direction: Literal["up", "down", "left", "right"] | None = Field(
        default=None,
        description="Optional direction. For scroll it means content direction; for swipe it means finger gesture direction.",
    )
    start_x_ratio: float | None = Field(default=None, description="Optional normalized gesture start x ratio in the range [0.0, 1.0].")
    start_y_ratio: float | None = Field(default=None, description="Optional normalized gesture start y ratio in the range [0.0, 1.0].")
    distance_ratio: float | None = Field(
        default=None,
        description="Optional normalized gesture travel along the primary axis in the range (0.0, 1.0].",
    )
    duration: float | None = Field(
        default=None,
        description="Optional duration in seconds. Used by wait and can override the default hold time for long_press.",
    )
    dismiss_keyboard: bool | None = Field(default=None, description="Optional keyboard dismissal flag for input actions.")
    summary: str | None = Field(default=None, description="Optional concise action summary.")

    @model_validator(mode="before")
    @classmethod
    def normalize_shorthand_action(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "type" in data:
            return data
        if len(data) != 1:
            return data
        shorthand, value = next(iter(data.items()))
        if shorthand == "click" and isinstance(value, int):
            return {"type": "click", "target_id": value}
        if shorthand in {"back", "home"} and value is True:
            return {"type": shorthand}
        if shorthand == "wait" and isinstance(value, (int, float)):
            return {"type": "wait", "duration": float(value)}
        return data

    @field_validator("start_x_ratio", "start_y_ratio")
    @classmethod
    def validate_start_ratio(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not (0.0 <= value <= 1.0):
            raise ValueError("start ratio values must be between 0.0 and 1.0")
        return value

    @field_validator("distance_ratio")
    @classmethod
    def validate_distance_ratio(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0.0 or value > 1.0:
            raise ValueError("distance_ratio must be between 0.0 and 1.0")
        return value

    @model_validator(mode="after")
    def validate_gesture_shape(self) -> "SessionActionInput":
        if self.type in {"scroll", "swipe"}:
            if self.direction is None:
                raise ValueError("direction is required for scroll and swipe")
            if self.start_x_ratio is None:
                raise ValueError("start_x_ratio is required for scroll and swipe")
            if self.start_y_ratio is None:
                raise ValueError("start_y_ratio is required for scroll and swipe")
            if self.distance_ratio is None:
                raise ValueError("distance_ratio is required for scroll and swipe")
        if self.type == "pull_to_refresh" and self.direction is not None:
            raise ValueError("direction must not be provided for pull_to_refresh")
        return self


class SessionActInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier to act on.")
    action: SessionActionInput = Field(description="One allowed interactive action request.")
    detail: Literal["summary", "compact", "full"] = Field(
        default="summary",
        description="Action result payload detail level. Use summary by default, compact for post-action targets, and full for complete before/after payloads.",
    )
    timeout_sec: float | None = Field(
        default=None,
        description="Optional post-action timeout in seconds while waiting for the screen to settle. Defaults to 6.0 for interactive sessions.",
    )


class SessionFinalizeInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier to finalize.")
    summary: str | None = Field(default=None, description="Optional agent-authored summary attached to finalize result.")


class SessionAbortInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier to abort.")
