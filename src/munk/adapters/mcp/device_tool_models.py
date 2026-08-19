from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from munk.core.action_target_refs import normalize_target_ref


class DevicesListInput(BaseModel):
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform filter.",
    )


class DeviceStateInput(BaseModel):
    device_ref: str = Field(description="Device reference.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform disambiguator.",
    )


class DeviceUnlockInput(BaseModel):
    device_ref: str = Field(description="Device reference.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform disambiguator.",
    )
    strategy: Literal["swipe"] = Field(
        default="swipe",
        description="Unlock strategy. V1: swipe only.",
    )


class SharedAppIdentityFields(BaseModel):
    """Flat app identity fields shared by lifecycle / session_start (Agent-facing, not nested)."""

    app_id: str = Field(description="App identifier.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform override (android→package, ios→bundle_id, web→base_url/origin).",
    )
    device_ref: str | None = Field(default=None, description="Optional device reference.")
    package: str | None = Field(default=None, description="Optional Android package.")
    bundle_id: str | None = Field(default=None, description="Optional iOS bundle id.")


class SharedAppLifecycleFields(SharedAppIdentityFields):
    """Full flat lifecycle target fields including web overrides."""

    base_url: str | None = Field(default=None, description="Optional web base URL.")
    origin: str | None = Field(default=None, description="Optional web origin.")
    headless: bool = Field(default=False, description="Launch web runtime headlessly.")


class SharedAppLifecycleWithAssets(SharedAppLifecycleFields):
    assets_root: Path | None = Field(
        default=None,
        description="Optional assets root (apps/, plans/).",
    )


class AppLaunchInput(SharedAppLifecycleWithAssets):
    pass


class AppStopInput(SharedAppLifecycleWithAssets):
    pass


class AppInstallInput(SharedAppIdentityFields):
    """Android-primary install surface; web launch fields are intentionally omitted."""

    model_config = ConfigDict(extra="forbid")

    artifact_path: Path = Field(description="Host path to the install artifact.")
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform override. V1 install is Android-primary.",
    )
    bundle_id: str | None = Field(
        default=None,
        description="Optional iOS bundle id (not V1 primary).",
    )
    assets_root: Path | None = Field(
        default=None,
        description="Optional assets root (apps/, plans/).",
    )


class SessionStartInput(SharedAppLifecycleFields):
    app_id: str = Field(description="App identifier.")
    device_ref: str | None = Field(
        default=None,
        description="Optional device to claim.",
    )
    config_path: Path | None = Field(
        default=None,
        description="Optional workspace config path.",
    )


class SessionGetInput(BaseModel):
    session_id: str = Field(description="Session id.")


class SessionObserveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session id.")
    match: str | None = Field(
        default=None,
        description="Keyword bypass hit region; does not rewrite targets_text.",
    )
    include_screenshot: bool = Field(
        default=False,
        description="Return an MCP image block (vision). Default false.",
    )


class SessionListTargetsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session id.")
    source: Literal["all", "vision", "tree"] = Field(
        default="all",
        description="Channel filter. all applies offset/limit per channel.",
    )
    offset: int = Field(default=0, ge=0, description="Pagination offset per channel.")
    limit: int | None = Field(
        default=None,
        description="Page size. Default 40.",
    )


class SessionsListInput(BaseModel):
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform filter.",
    )
    device_ref: str | None = Field(
        default=None,
        description="Optional device filter.",
    )
    app_id: str | None = Field(
        default=None,
        description="Optional app filter.",
    )


class SessionActionInput(BaseModel):
    type: Literal[
        "click",
        "long_press",
        "edit_text",
        "set_value",
        "scroll",
        "swipe",
        "pull_to_refresh",
        "wait",
        "back",
        "home",
    ] = Field(
        description="Action type. edit_text for typing; set_value for structured #t* controls.",
    )
    target_ref: str | None = Field(
        default=None,
        description="Target ref from observe (vN or tN).",
    )
    resource_id: str | None = Field(
        default=None,
        description="resource_id fallback.",
    )
    label: str | None = Field(
        default=None,
        description="Unique label fallback.",
    )
    box: tuple[int, int, int, int] | None = Field(
        default=None,
        description="Box as left, top, right, bottom.",
    )
    point: tuple[int, int] | None = Field(default=None, description="Point as x, y.")
    text: str | None = Field(
        default=None,
        description="edit_text payload only. set_value must use value.",
    )
    value: str | None = Field(
        default=None,
        description="set_value payload only (requires tN).",
    )
    text_mode: Literal["append", "replace"] | None = Field(
        default=None,
        description="edit_text mode: append or replace.",
    )
    direction: Literal["up", "down", "left", "right"] | None = Field(
        default=None,
        description="scroll=content direction; swipe=finger direction.",
    )
    start_x_ratio: float | None = Field(
        default=None,
        description="Gesture start x ratio [0,1].",
    )
    start_y_ratio: float | None = Field(
        default=None,
        description="Gesture start y ratio [0,1].",
    )
    distance_ratio: float | None = Field(
        default=None,
        description="Gesture travel ratio (0,1].",
    )
    duration: float | None = Field(
        default=None,
        description="Seconds for wait / long_press hold.",
    )
    dismiss_keyboard: bool | None = Field(
        default=None,
        description="Dismiss keyboard after edit_text.",
    )
    summary: str | None = Field(default=None, description="Optional action summary.")

    @model_validator(mode="before")
    @classmethod
    def normalize_shorthand_action(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "type" in data:
            return data
        if len(data) != 1:
            return data
        shorthand, value = next(iter(data.items()))
        if shorthand == "click":
            if isinstance(value, int):
                raise ValueError(
                    "click shorthand must use target_ref string such as 'v12' or '#t3'; "
                    f"got int {value}"
                )
            if isinstance(value, str):
                return {"type": "click", "target_ref": normalize_target_ref(value)}
            raise ValueError("click shorthand requires a target_ref string such as 'v12' or '#t3'")
        if shorthand in {"back", "home"} and value is True:
            return {"type": shorthand}
        if shorthand == "wait" and isinstance(value, (int, float)):
            return {"type": "wait", "duration": float(value)}
        return data

    @field_validator("target_ref")
    @classmethod
    def validate_target_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_target_ref(value)

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
    def validate_gesture_shape(self) -> "SessionActionInput":  # noqa: C901, PLR0912, PLR0912
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
        if self.type == "set_value":
            if self.target_ref is None:
                raise ValueError("target_ref is required for set_value")
            if not self.target_ref.startswith("t"):
                raise ValueError("set_value requires a tree target_ref (tN)")
            if self.text is not None:
                raise ValueError("text must not be provided for set_value; use value")
            if self.value is None or not str(self.value).strip():
                raise ValueError("value is required for set_value")
            if self.text_mode is not None:
                raise ValueError("text_mode must not be provided for set_value")
            if self.dismiss_keyboard is not None:
                raise ValueError("dismiss_keyboard must not be provided for set_value")
        if self.type == "edit_text" and self.value is not None:
            raise ValueError("value must not be provided for edit_text; use text")
        return self


class SessionActInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session id.")
    action: SessionActionInput = Field(description="One action request.")
    timeout_sec: float | None = Field(
        default=None,
        description="Post-action settle timeout seconds. Default 6.",
    )


class SessionFinalizeInput(BaseModel):
    session_id: str = Field(description="Session id.")
    summary: str | None = Field(default=None, description="Optional agent summary.")


class SessionAbortInput(BaseModel):
    session_id: str = Field(description="Session id.")
