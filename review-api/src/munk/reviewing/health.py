from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


def empty_details() -> dict[str, str]:
    return {}


class ReviewRuntimeDescriptor(BaseModel):
    runtime_id: str
    display_name: str
    package_name: str | None = None
    supports_knowledge_build: bool = True


class ReviewRuntimeHealth(BaseModel):
    runtime_id: str
    status: Literal["ok", "warning", "error"]
    message: str
    details: dict[str, str] = Field(default_factory=empty_details)
