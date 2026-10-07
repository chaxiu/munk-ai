from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

ScheduleTriggerKind = Literal["cron"]
ScheduleRunStatus = Literal["queued", "dispatching", "triggered", "succeeded", "failed", "cancelled"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScheduleRecord(BaseModel):
    schedule_id: str
    name: str
    app_id: str
    device_ref: str
    timezone: str
    enabled: bool = True
    trigger_kind: ScheduleTriggerKind = "cron"
    cron_expr: str
    request_json: dict[str, Any] = Field(default_factory=dict)
    next_run_at: str | None = None
    last_run_at: str | None = None
    last_schedule_run_id: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ScheduleRunRecord(BaseModel):
    schedule_run_id: str
    schedule_id: str
    scheduled_for: str
    status: ScheduleRunStatus
    operation_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = Field(default_factory=now_iso)
    started_at: str | None = None
    triggered_at: str | None = None
    finished_at: str | None = None
