from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from munk.app import AppPlatform

RuntimeLogLevel = Literal["debug", "info", "warning", "error", "unknown"]
RuntimeLogSource = Literal["android_logcat", "web_console", "ios_syslog"]


def empty_raw_app_state() -> dict[str, Any]:
    return {}


def empty_raw_log_state() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class DeviceInfo:
    width: int
    height: int
    platform: AppPlatform
    device_ref: str | None


@dataclass(frozen=True)
class CurrentAppState:
    platform: AppPlatform
    entry_identity: str | None
    activity_name: str | None = None
    url: str | None = None
    title: str | None = None
    load_state: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_raw_app_state)
    surface_identity: str | None = None


@dataclass(frozen=True)
class RuntimeLogEntry:
    timestamp_ms: int | None
    level: RuntimeLogLevel
    source: RuntimeLogSource | str
    message: str
    step_index: int | None = None
    target_identity: str | None = None
    surface_identity: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_raw_log_state)
