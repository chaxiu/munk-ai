from __future__ import annotations

import json
import sqlite3
from typing import Any, cast

from munk.services.operations.models import (
    OperationEventRecord,
    OperationKind,
    OperationRecord,
    OperationStatus,
    ResourceScope,
)


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_json(value: Any) -> Any:
    if value in {None, ""}:
        return None
    return json.loads(str(value))


def row_to_operation(row: sqlite3.Row) -> OperationRecord:
    return OperationRecord(
        operation_id=str(row["operation_id"]),
        kind=cast(OperationKind, str(row["kind"])),
        status=cast(OperationStatus, str(row["status"])),
        verification_verdict=row["verification_verdict"],
        app_id=row["app_id"],
        plan_id=row["plan_id"],
        case_id=row["case_id"],
        parent_operation_id=str(row["parent_operation_id"]) if row["parent_operation_id"] is not None else None,
        batch_id=str(row["batch_id"]) if row["batch_id"] is not None else None,
        position_index=int(row["position_index"]) if row["position_index"] is not None else None,
        position_label=str(row["position_label"]) if row["position_label"] is not None else None,
        request_json=load_json(row["request_json"]) or {},
        result_json=load_json(row["result_json"]),
        artifacts_json=load_json(row["artifacts_json"]) or {},
        progress_json=load_json(row["progress_json"]) or {},
        projected_run_type=str(row["projected_run_type"]) if row["projected_run_type"] is not None else None,
        projected_platform=str(row["projected_platform"]) if row["projected_platform"] is not None else None,
        projected_title=str(row["projected_title"]) if row["projected_title"] is not None else None,
        projected_source_recording_id=(
            str(row["projected_source_recording_id"]) if row["projected_source_recording_id"] is not None else None
        ),
        pid=int(row["pid"]) if row["pid"] is not None else None,
        cancel_requested=bool(row["cancel_requested"]),
        device_ref=str(row["device_ref"]) if row["device_ref"] is not None else None,
        resource_scope=cast(ResourceScope, str(row["resource_scope"]) if row["resource_scope"] is not None else "none"),
        conflict_reason=str(row["conflict_reason"]) if row["conflict_reason"] is not None else None,
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=str(row["created_at"]),
        started_at=str(row["started_at"]) if row["started_at"] is not None else None,
        finished_at=str(row["finished_at"]) if row["finished_at"] is not None else None,
    )


def row_to_event(row: sqlite3.Row) -> OperationEventRecord:
    return OperationEventRecord(
        seq=int(row["seq"]),
        operation_id=str(row["operation_id"]),
        timestamp=str(row["timestamp"]),
        event_type=str(row["event_type"]),
        message=str(row["message"]) if row["message"] is not None else None,
        data_json=load_json(row["data_json"]),
    )
