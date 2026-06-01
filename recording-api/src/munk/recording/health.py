from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


def empty_details() -> dict[str, str]:
    return {}


class RecordingRuntimeDescriptor(BaseModel):
    runtime_id: str
    display_name: str
    package_name: str | None = None
    supports_android: bool = True
    supports_ios: bool = False
    supports_web: bool = False


class RecordingRuntimeHealth(BaseModel):
    runtime_id: str
    status: Literal["ok", "warning", "error"]
    message: str
    details: dict[str, str] = Field(default_factory=empty_details)
