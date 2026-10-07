from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from munk.app import AppTarget


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


class DeviceInstallRequest(BaseModel):
    device_ref: str
    artifact_path: Path
    app_target: AppTarget


class DeviceInstallData(BaseModel):
    operation_id: str
    action: str
    app_id: str
    platform: str
    device_ref: str
    entry_identity: str
    artifact_path: str | None = None
