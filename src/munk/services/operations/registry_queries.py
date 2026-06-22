from __future__ import annotations

from typing import Any

from munk.services.operations.models import OperationKind, OperationStatus


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
    sql = """
        SELECT *
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
        SELECT *
        FROM operations
        WHERE kind = ?
          AND ({' OR '.join(clauses)})
        ORDER BY datetime(created_at) DESC, operation_id DESC
    """
    return sql, params, unique_refs
