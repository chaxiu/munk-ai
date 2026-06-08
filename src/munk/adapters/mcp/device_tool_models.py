from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DevicesListInput(BaseModel):
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform filter for discovered devices.",
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
    type: Literal["click", "long_press", "input", "clear_and_input", "scroll", "swipe", "wait", "back", "home"] = Field(
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
    direction: Literal["up", "down", "left", "right"] | None = Field(
        default=None,
        description="Optional direction. For scroll it means content direction; for swipe it means finger gesture direction.",
    )
    distance_px: int | None = Field(default=None, gt=0, description="Optional gesture travel distance in pixels.")
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


class SessionActInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier to act on.")
    action: SessionActionInput = Field(description="One allowed interactive action request.")
    detail: Literal["compact", "full"] = Field(
        default="compact",
        description="Action result payload detail level. Use compact by default and full for complete before/after payloads.",
    )
    settle_timeout_sec: float | None = Field(
        default=None,
        description="Optional post-action settle timeout in seconds. Defaults to 6.0 for interactive sessions.",
    )


class SessionFinalizeInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier to finalize.")
    summary: str | None = Field(default=None, description="Optional agent-authored summary attached to finalize result.")


class SessionAbortInput(BaseModel):
    session_id: str = Field(description="Interactive session identifier to abort.")
