from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeviceDescriptorData(BaseModel):
    platform: str
    device_ref: str
    display_name: str
    kind: str
    availability: str
    is_booted: bool | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class DeviceListData(BaseModel):
    items: list[DeviceDescriptorData] = Field(default_factory=list)


class DeviceStateData(BaseModel):
    platform: str
    device_ref: str
    display_name: str
    kind: str
    availability: str
    is_booted: bool | None = None
    is_locked: bool | None = None
    is_screen_on: bool | None = None
    automation_ready: bool = False
    unlock_strategies: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class DeviceUnlockData(BaseModel):
    platform: str
    device_ref: str
    strategy: str
    success: bool
    changed: bool
    message: str
    before: DeviceStateData
    after: DeviceStateData
