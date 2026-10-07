from __future__ import annotations

from munk.adapters.shared.payload_models import (
    ScheduleDetailData,
    ScheduleListData,
    ScheduleRunListData,
    ScheduleRunSummaryData,
    ScheduleSummaryData,
)
from munk.scheduling.models import ScheduleRecord, ScheduleRunRecord


def build_schedule_summary_data(record: ScheduleRecord) -> ScheduleSummaryData:
    return ScheduleSummaryData(
        schedule_id=record.schedule_id,
        name=record.name,
        app_id=record.app_id,
        plan_ids=[str(item) for item in record.request_json.get("plan_ids", []) if str(item).strip()],
        device_ref=record.device_ref,
        timezone=record.timezone,
        cron_expr=record.cron_expr,
        enabled=record.enabled,
        next_run_at=record.next_run_at,
        last_run_at=record.last_run_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def build_schedule_detail_data(
    record: ScheduleRecord,
    *,
    recent_runs: list[ScheduleRunRecord],
    active_schedule_run_id: str | None = None,
    queued_run_count: int = 0,
) -> ScheduleDetailData:
    summary = build_schedule_summary_data(record)
    latest_operation_id = next((item.operation_id for item in recent_runs if item.operation_id), None)
    request_json = record.request_json
    return ScheduleDetailData(
        **summary.model_dump(mode="json"),
        latest_operation_id=latest_operation_id,
        active_schedule_run_id=active_schedule_run_id,
        queued_run_count=queued_run_count,
        headless=bool(request_json.get("headless", False)),
        fail_fast=bool(request_json.get("fail_fast", False)),
        artifact_path=str(request_json.get("artifact_path")) if request_json.get("artifact_path") is not None else None,
        assets_root=str(request_json.get("assets_root")) if request_json.get("assets_root") is not None else None,
        runtime_overrides=(
            dict(request_json.get("runtime_overrides", {}))
            if isinstance(request_json.get("runtime_overrides"), dict)
            else {}
        ),
        recent_runs=[build_schedule_run_summary_data(item) for item in recent_runs],
    )

def build_schedule_list_data(
    records: list[ScheduleRecord],
    *,
    total: int,
    limit: int,
    offset: int,
) -> ScheduleListData:
    return ScheduleListData(
        items=[build_schedule_summary_data(item) for item in records],
        total=total,
        limit=limit,
        offset=offset,
    )


def build_schedule_run_summary_data(record: ScheduleRunRecord) -> ScheduleRunSummaryData:
    return ScheduleRunSummaryData(
        schedule_run_id=record.schedule_run_id,
        scheduled_for=record.scheduled_for,
        status=record.status,
        operation_id=record.operation_id,
        error_code=record.error_code,
        error_message=record.error_message,
        created_at=record.created_at,
        started_at=record.started_at,
        triggered_at=record.triggered_at,
        finished_at=record.finished_at,
    )


def build_schedule_run_list_data(
    *,
    schedule_id: str,
    runs: list[ScheduleRunRecord],
) -> ScheduleRunListData:
    return ScheduleRunListData(
        schedule_id=schedule_id,
        items=[build_schedule_run_summary_data(item) for item in runs],
    )
