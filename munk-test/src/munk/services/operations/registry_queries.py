from __future__ import annotations

from typing import Any

from munk.services.operations.models import OperationKind, OperationStatus

OPERATION_SUMMARY_COLUMNS = (
    "operation_id",
    "kind",
    "status",
    "verification_verdict",
    "app_id",
    "plan_id",
    "case_id",
    "parent_operation_id",
    "batch_id",
    "position_index",
    "position_label",
    "projected_run_type",
    "projected_platform",
    "projected_title",
    "projected_source_recording_id",
    "pid",
    "cancel_requested",
    "device_ref",
    "resource_scope",
    "conflict_reason",
    "error_code",
    "error_message",
    "created_at",
    "started_at",
    "finished_at",
    "result_path",
)

OPERATION_SUMMARY_SELECT = ",\n            ".join(OPERATION_SUMMARY_COLUMNS)


def build_list_operations_page_query(
    *,
    status: OperationStatus | None,
    kind: OperationKind | None,
    device_ref: str | None,
    surface: str | None,
    verification_verdict: str | None,
    platform: str | None,
    query: str | None,
    run_type: str | None,
    run_type_expr: str,
    platform_expr: str,
) -> tuple[str, list[Any]]:
    sql = f"""
        SELECT
            {OPERATION_SUMMARY_SELECT}
        FROM operations
        WHERE 1 = 1
    """
    params: list[Any] = []
    if kind is None:
        sql += " AND kind != ?"
        params.append("interactive_session")
    if status is not None:
        sql += " AND status = ?"
        params.append(status)
    if kind is not None:
        sql += " AND kind = ?"
        params.append(kind)
    if device_ref is not None:
        sql += " AND device_ref = ?"
        params.append(device_ref)
    if verification_verdict is not None:
        sql += " AND verification_verdict = ?"
        params.append(verification_verdict)
    if surface == "run_center":
        sql += f" AND ({run_type_expr}) IS NOT NULL"
    if platform is not None:
        sql += f" AND ({platform_expr}) = ?"
        params.append(platform)
    if run_type is not None:
        sql += f" AND ({run_type_expr}) = ?"
        params.append(run_type)
    if query is not None and query.strip():
        normalized_query = f"%{query.strip().lower()}%"
        sql += """
            AND (
                LOWER(operation_id) LIKE ?
                OR LOWER(COALESCE(app_id, '')) LIKE ?
                OR LOWER(COALESCE(plan_id, '')) LIKE ?
                OR LOWER(COALESCE(case_id, '')) LIKE ?
                OR LOWER(
                    COALESCE(
                        projected_title,
                        json_extract(request_json, '$.case_title'),
                        json_extract(request_json, '$.change_summary'),
                        json_extract(result_json, '$.change_summary'),
                        json_extract(result_json, '$.summary'),
                        ''
                    )
                ) LIKE ?
                OR LOWER(
                    COALESCE(
                        projected_source_recording_id,
                        json_extract(request_json, '$.recording_id'),
                        json_extract(result_json, '$.recording_id'),
                        json_extract(progress_json, '$.recording_id'),
                        ''
                    )
                ) LIKE ?
            )
        """
        params.extend([normalized_query] * 6)
    return sql, params


def build_latest_plan_runs_query(plan_refs: list[tuple[str, str]]) -> tuple[str | None, list[Any], list[tuple[str, str]]]:
    normalized_refs = [
        (app_id.strip(), plan_id.strip())
        for app_id, plan_id in plan_refs
        if isinstance(app_id, str) and app_id.strip() and isinstance(plan_id, str) and plan_id.strip()
    ]
    if not normalized_refs:
        return None, [], []

    unique_refs: list[tuple[str, str]] = []
    seen_refs: set[tuple[str, str]] = set()
    for ref in normalized_refs:
        if ref in seen_refs:
            continue
        seen_refs.add(ref)
        unique_refs.append(ref)

    clauses: list[str] = []
    params: list[Any] = ["run_plan"]
    for app_id, plan_id in unique_refs:
        clauses.append("(app_id = ? AND plan_id = ?)")
        params.extend([app_id, plan_id])

    sql = f"""
        SELECT
            {OPERATION_SUMMARY_SELECT}
        FROM (
            SELECT
                {OPERATION_SUMMARY_SELECT},
                ROW_NUMBER() OVER (
                    PARTITION BY app_id, plan_id
                    ORDER BY created_at DESC, operation_id DESC
                ) AS rn
            FROM operations
            WHERE kind = ?
              AND ({' OR '.join(clauses)})
        ) ranked
        WHERE rn = 1
    """
    return sql, params, unique_refs


def build_count_operations_query(
    *,
    status: OperationStatus | None = None,
    kind: OperationKind | None = None,
    device_ref: str | None = None,
    surface: str | None = None,
    verification_verdict: str | None = None,
    platform: str | None = None,
    query: str | None = None,
    run_type: str | None = None,
    run_type_expr: str,
    platform_expr: str,
) -> tuple[str, list[Any]]:
    list_sql, params = build_list_operations_page_query(
        status=status,
        kind=kind,
        device_ref=device_ref,
        surface=surface,
        verification_verdict=verification_verdict,
        platform=platform,
        query=query,
        run_type=run_type,
        run_type_expr=run_type_expr,
        platform_expr=platform_expr,
    )
    # Replace the SELECT list with COUNT(*) while keeping the same WHERE clause.
    where_index = list_sql.find("WHERE")
    if where_index < 0:
        raise RuntimeError("list operations query missing WHERE clause")
    sql = f"SELECT COUNT(*) AS total FROM operations {list_sql[where_index:]}"
    return sql, params
