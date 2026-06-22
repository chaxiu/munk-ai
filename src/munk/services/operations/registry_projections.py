from __future__ import annotations

from typing import Any, cast

from munk.services.operations.models import OperationRecord
from munk.services.operations.payloads import infer_run_type, infer_title, source_recording_id
from munk.services.operations.payloads import matches_query as payload_matches_query


def include_in_run_center(record: OperationRecord) -> bool:
    return infer_run_type(record) is not None


def recording_id_sql_expr() -> str:
    return (
        "COALESCE("
        "NULLIF(projected_source_recording_id, ''), "
        "NULLIF(json_extract(request_json, '$.recording_id'), ''), "
        "NULLIF(json_extract(result_json, '$.recording_id'), ''), "
        "NULLIF(json_extract(progress_json, '$.recording_id'), '')"
        ")"
    )


def run_type_sql_expr() -> str:
    recording_id_expr = recording_id_sql_expr()
    return f"""
        COALESCE(
            NULLIF(projected_run_type, ''),
            CASE
                WHEN kind = 'run_plans' THEN 'plan_batch_run'
                WHEN kind = 'run_plan' THEN 'plan_run'
                WHEN kind = 'optimize_case' THEN 'optimize_case'
                WHEN kind = 'knowledge_post_action' THEN 'knowledge_post_action'
                WHEN kind = 'verify_change' THEN 'verify_change'
                WHEN kind = 'run_case'
                 AND (
                    COALESCE(plan_id, '') LIKE 'recording-replay:%'
                    OR {recording_id_expr} IS NOT NULL
                 ) THEN 'replay'
                WHEN kind = 'run_case' THEN 'case_run'
                ELSE NULL
            END
        )
    """


def platform_sql_expr() -> str:
    return """
        COALESCE(
            NULLIF(projected_platform, ''),
            NULLIF(json_extract(request_json, '$.platform'), ''),
            NULLIF(json_extract(request_json, '$.app_target.platform'), ''),
            NULLIF(json_extract(result_json, '$.platform'), ''),
            NULLIF(json_extract(progress_json, '$.platform'), ''),
            CASE
                WHEN json_extract(request_json, '$.base_url') IS NOT NULL THEN 'web'
                ELSE NULL
            END,
            CASE
                WHEN json_extract(request_json, '$.bundle_id') IS NOT NULL THEN 'ios'
                ELSE NULL
            END,
            CASE
                WHEN json_extract(request_json, '$.package') IS NOT NULL THEN 'android'
                ELSE NULL
            END
        )
    """


def infer_platform(record: OperationRecord) -> str | None:
    request = json_dict(record.request_json)
    result = json_dict(record.result_json)
    progress = json_dict(record.progress_json)
    request_target = request.get("app_target")
    request_target_dict = cast(dict[str, object] | None, request_target) if isinstance(request_target, dict) else None
    for candidate in (
        request.get("platform"),
        request_target_dict.get("platform") if request_target_dict is not None else None,
        result.get("platform"),
        progress.get("platform"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    if request.get("base_url"):
        return "web"
    if request.get("bundle_id"):
        return "ios"
    if request.get("package"):
        return "android"
    return None


def matches_query(record: OperationRecord, query: str) -> bool:
    return payload_matches_query(record, query)


def infer_title_for_record(record: OperationRecord) -> str:
    return infer_title(record)


def infer_target_label(record: OperationRecord) -> str:
    parts = [record.app_id, record.plan_id, record.case_id]
    label = " / ".join(part for part in parts if part)
    return label or record.operation_id


def source_recording_id_for_record(record: OperationRecord) -> str | None:
    return source_recording_id(record)


def json_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def should_refresh_projection(fields: dict[str, Any]) -> bool:
    return any(
        key in fields
        for key in (
            "kind",
            "app_id",
            "plan_id",
            "case_id",
            "request_json",
            "result_json",
            "progress_json",
        )
    )
