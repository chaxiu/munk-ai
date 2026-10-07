from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScheduleRunSummaryData(BaseModel):
    schedule_run_id: str
    scheduled_for: str
    status: str
    operation_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    triggered_at: str | None = None
    finished_at: str | None = None


class ScheduleSummaryData(BaseModel):
    schedule_id: str
    name: str
    app_id: str
    plan_ids: list[str] = Field(default_factory=list)
    device_ref: str
    timezone: str
    cron_expr: str
    enabled: bool
    next_run_at: str | None = None
    last_run_at: str | None = None
    created_at: str
    updated_at: str


class ScheduleDetailData(ScheduleSummaryData):
    latest_operation_id: str | None = None
    active_schedule_run_id: str | None = None
    queued_run_count: int = 0
    headless: bool = False
    fail_fast: bool = False
    artifact_path: str | None = None
    assets_root: str | None = None
    runtime_overrides: dict[str, Any] = Field(default_factory=dict)
    recent_runs: list[ScheduleRunSummaryData] = Field(default_factory=list)


class ScheduleListData(BaseModel):
    items: list[ScheduleSummaryData] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


class ScheduleRunListData(BaseModel):
    schedule_id: str
    items: list[ScheduleRunSummaryData] = Field(default_factory=list)
