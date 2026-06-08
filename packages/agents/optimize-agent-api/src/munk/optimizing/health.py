from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


def empty_details() -> dict[str, str]:
    return {}


class OptimizeRuntimeHealth(BaseModel):
    runtime_id: str
    status: Literal["ok", "warning", "error"]
    message: str
    details: dict[str, str] = Field(default_factory=empty_details)
