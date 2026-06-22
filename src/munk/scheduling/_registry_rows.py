from __future__ import annotations

import json
import sqlite3
from typing import Any, cast

from munk.scheduling.models import ScheduleRecord, ScheduleRunRecord, ScheduleRunStatus, ScheduleTriggerKind


def dump_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    loaded = json.loads(value)
    return cast(dict[str, Any], loaded if isinstance(loaded, dict) else {})


def row_to_schedule(row: sqlite3.Row) -> ScheduleRecord:
    return ScheduleRecord(
        schedule_id=str(row["schedule_id"]),
        name=str(row["name"]),
        app_id=str(row["app_id"]),
        device_ref=str(row["device_ref"]),
        timezone=str(row["timezone"]),
        enabled=bool(row["enabled"]),
        trigger_kind=cast(ScheduleTriggerKind, str(row["trigger_kind"])),
        cron_expr=str(row["cron_expr"]),
        request_json=load_json(row["request_json"]),
        next_run_at=row["next_run_at"],
        last_run_at=row["last_run_at"],
        last_schedule_run_id=row["last_schedule_run_id"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def row_to_schedule_run(row: sqlite3.Row) -> ScheduleRunRecord:
    return ScheduleRunRecord(
        schedule_run_id=str(row["schedule_run_id"]),
        schedule_id=str(row["schedule_id"]),
        scheduled_for=str(row["scheduled_for"]),
        status=cast(ScheduleRunStatus, str(row["status"])),
        operation_id=row["operation_id"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=str(row["created_at"]),
        started_at=row["started_at"],
        triggered_at=row["triggered_at"],
        finished_at=row["finished_at"],
    )
