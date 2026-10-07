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
from munk.services.operations.payload_storage import hydrate_event_data_json, merge_result_payload


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_json(value: Any) -> Any:
    if value in {None, ""}:
        return None
    return json.loads(str(value))


def _row_has_column(row: sqlite3.Row, column: str) -> bool:
    return column in row.keys()


def row_to_operation(row: sqlite3.Row, *, hydrate_payloads: bool = True) -> OperationRecord:
    has_request = _row_has_column(row, "request_json")
    has_result = _row_has_column(row, "result_json")
    has_artifacts = _row_has_column(row, "artifacts_json")
    has_progress = _row_has_column(row, "progress_json")
    result_path = (
        str(row["result_path"])
        if _row_has_column(row, "result_path") and row["result_path"] is not None
        else None
    )
    inline_result = load_json(row["result_json"]) if has_result else None
    result_json = (
        merge_result_payload(inline_result=inline_result, result_path=result_path)
        if hydrate_payloads
        else inline_result
    )
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
        request_json=(load_json(row["request_json"]) or {}) if has_request else {},
        result_json=result_json,
        artifacts_json=(load_json(row["artifacts_json"]) or {}) if has_artifacts else {},
        progress_json=(load_json(row["progress_json"]) or {}) if has_progress else {},
        projected_run_type=str(row["projected_run_type"]) if row["projected_run_type"] is not None else None,
        projected_platform=str(row["projected_platform"]) if row["projected_platform"] is not None else None,
        projected_title=str(row["projected_title"]) if row["projected_title"] is not None else None,
        projected_source_recording_id=(
            str(row["projected_source_recording_id"]) if row["projected_source_recording_id"] is not None else None
        ),
        result_path=result_path,
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


def row_to_event(row: sqlite3.Row, *, hydrate_payloads: bool = True) -> OperationEventRecord:
    data_json = load_json(row["data_json"]) or {}
    if hydrate_payloads and isinstance(data_json, dict):
        data_json = hydrate_event_data_json(data_json)
    return OperationEventRecord(
        seq=int(row["seq"]),
        operation_id=str(row["operation_id"]),
        timestamp=str(row["timestamp"]),
        event_type=str(row["event_type"]),
        message=str(row["message"]) if row["message"] is not None else None,
        data_json=data_json if isinstance(data_json, dict) else {},
    )
