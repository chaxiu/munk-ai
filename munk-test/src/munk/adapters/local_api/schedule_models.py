from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from munk.execution.models import RuntimeOverrideValue


def empty_runtime_overrides() -> dict[str, RuntimeOverrideValue]:
    return {}


class ScheduleUpsertRequest(BaseModel):
    name: str | None = None
    app_id: str
    plan_ids: list[str]
    device_ref: str
    timezone: str | None = None
    cron_expr: str
    headless: bool = False
    fail_fast: bool = False
    artifact_path: Path | None = None
    assets_root: Path | None = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=empty_runtime_overrides)
    enabled: bool = True
