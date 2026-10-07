from __future__ import annotations

from typing import Any, cast

from munk.services.operations.models import OperationProjection, OperationRecord
from munk.token_usage import TokenUsage


def build_operation_projection(record: OperationRecord) -> OperationProjection:
    return OperationProjection(
        run_type=_infer_record_run_type(record),
        platform=_infer_record_platform(record),
        title=_infer_record_title(record),
        source_recording_id=_infer_record_source_recording_id(record),
    )


def with_projected_fields(record: OperationRecord) -> OperationRecord:
    projection = build_operation_projection(record)
    return record.model_copy(
        update={
            "projected_run_type": projection.run_type,
            "projected_platform": projection.platform,
            "projected_title": projection.title,
            "projected_source_recording_id": projection.source_recording_id,
        }
    )


def infer_run_type(record: OperationRecord) -> str | None:
    if isinstance(record.projected_run_type, str) and record.projected_run_type.strip():
        return record.projected_run_type
    return _infer_record_run_type(record)


def _infer_record_run_type(record: OperationRecord) -> str | None:
    if record.kind == "run_plans":
        return "plan_batch_run"
    if record.kind == "run_plan":
        return "plan_run"
    if record.kind == "optimize_case":
        return "optimize_case"
    if record.kind == "knowledge_post_action":
        return "knowledge_post_action"
    if record.kind == "verify_change":
        return "verify_change"
    if record.kind == "run_case":
        if str(record.plan_id or "").startswith("recording-replay:") or source_recording_id(record) is not None:
            return "replay"
        return "case_run"
    return None


def infer_platform(record: OperationRecord) -> str | None:
    if isinstance(record.projected_platform, str) and record.projected_platform.strip():
        return record.projected_platform
    return _infer_record_platform(record)


def _infer_record_platform(record: OperationRecord) -> str | None:
    request = _request_json(record)
    result = _result_json(record)
    progress = _progress_json(record)
    request_target = request.get("app_target")
    request_target_dict = cast(dict[str, object] | None, request_target) if isinstance(request_target, dict) else None
    request_target_platform = request_target_dict.get("platform") if request_target_dict is not None else None
    candidates: tuple[object | None, ...] = (
        request.get("platform"),
        request_target_platform,
        result.get("platform"),
        progress.get("platform"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    if request.get("base_url"):
        return "web"
    if request.get("bundle_id"):
        return "ios"
    if request.get("package"):
        return "android"
    return None


def infer_phase(record: OperationRecord) -> str | None:
    result = _result_json(record)
    progress = _progress_json(record)
    for candidate in (result.get("phase"), progress.get("phase")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def infer_target_label(record: OperationRecord) -> str:
    if record.kind == "run_plans":
        plan_count = _run_plans_plan_count_from_request_json(record.request_json)
        parts = [record.app_id]
        if isinstance(plan_count, int):
            parts.append(f"{plan_count} plans")
        if record.device_ref:
            parts.append(record.device_ref)
        label = " / ".join(part for part in parts if part)
        return label or record.operation_id
    parts = [record.app_id, record.plan_id, record.case_id]
    label = " / ".join(part for part in parts if part)
    return label or record.operation_id


def infer_title(record: OperationRecord) -> str:
    if isinstance(record.projected_title, str) and record.projected_title.strip():
        return record.projected_title
    return _infer_record_title(record)


def _infer_record_title(record: OperationRecord) -> str:
    request = _request_json(record)
    result = _result_json(record)
    run_type = infer_run_type(record)
    if run_type == "verify_change":
        return _first_non_empty_string(
            request.get("change_summary"),
            result.get("change_summary"),
            record.plan_id,
            record.operation_id,
        )
    if run_type == "plan_batch_run":
        plan_count = _run_plans_plan_count_from_request_json(record.request_json)
        if isinstance(plan_count, int) and plan_count > 0:
            return f"{plan_count} plans"
        return record.app_id or record.operation_id
    if run_type == "plan_run":
        return record.plan_id or record.operation_id
    if run_type == "replay":
        return _first_non_empty_string(
            _run_case_title_from_request_json(request),
            record.case_id,
            source_recording_id(record),
            record.operation_id,
        )
    if run_type == "case_run":
        return _first_non_empty_string(
            _run_case_title_from_request_json(request),
            record.case_id,
            record.operation_id,
        )
    if run_type == "optimize_case":
        return _first_non_empty_string(
            _run_case_title_from_request_json(request),
            result.get("summary"),
            record.case_id,
            record.operation_id,
        )
    if run_type == "knowledge_post_action":
        return _first_non_empty_string(
            _run_case_title_from_request_json(request),
            result.get("summary"),
            record.case_id,
            record.operation_id,
        )
    return record.case_id or record.plan_id or record.operation_id


def matches_query(record: OperationRecord, query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return True
    values: list[str | None] = [
        record.operation_id,
        record.app_id,
        record.plan_id,
        record.case_id,
        infer_title(record),
        infer_target_label(record),
        source_recording_id(record),
    ]
    return any(isinstance(value, str) and normalized in value.lower() for value in values)


def source_recording_id(record: OperationRecord) -> str | None:
    if isinstance(record.projected_source_recording_id, str) and record.projected_source_recording_id.strip():
        return record.projected_source_recording_id
    return _infer_record_source_recording_id(record)


def _infer_record_source_recording_id(record: OperationRecord) -> str | None:
    from munk.services.recording.operation_payloads import source_recording_id_from_payloads

    return source_recording_id_from_payloads(
        _request_json(record),
        _result_json(record),
        _progress_json(record),
    )


def build_operation_detail_payload(
    record: OperationRecord,
    *,
    artifact_summary: dict[str, Any],
    is_batch: bool = False,
    batch_kind: str | None = None,
    aggregate: dict[str, Any] | None = None,
    current_child_operation_id: str | None = None,
    current_child_case_id: str | None = None,
    children_preview: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    token_usage = token_usage_from_result_json(record.result_json)
    planning_usage = planning_usage_from_result_json(record.result_json)
    execution_usage = execution_usage_from_result_json(record.result_json)
    attempt_usages = attempt_usages_from_result_json(record.result_json)
    return {
        "operation_id": record.operation_id,
        "kind": record.kind,
        "run_type": infer_run_type(record),
        "title": infer_title(record),
        "platform": infer_platform(record),
        "phase": infer_phase(record),
        "target_label": infer_target_label(record),
        "source_recording_id": source_recording_id(record),
        "status": record.status,
        "verification_verdict": record.verification_verdict,
        "app_id": record.app_id,
        "plan_id": record.plan_id,
        "case_id": record.case_id,
        "parent_operation_id": record.parent_operation_id,
        "batch_id": record.batch_id,
        "position_index": record.position_index,
        "position_label": record.position_label,
        "pid": record.pid,
        "cancel_requested": record.cancel_requested,
        "device_ref": record.device_ref,
        "resource_scope": record.resource_scope,
        "conflict_reason": record.conflict_reason,
        "created_at": record.created_at,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "progress": record.progress_json,
        "result": record.result_json,
        "artifact_manifest_path": artifact_summary.get("artifact_manifest_path"),
        "repro_dir": artifact_summary.get("repro_dir"),
        "primary_artifact_ids": list(artifact_summary.get("primary_artifact_ids") or []),
        "artifact_manifest_version": artifact_summary.get("artifact_manifest_version"),
        "schema_versions": artifact_summary.get("schema_versions") or {},
        "diagnostics_path": artifact_summary.get("diagnostics_path"),
        "duration_ms": artifact_summary.get("duration_ms"),
        "failure_category": artifact_summary.get("failure_category"),
        "warning_summary": list(artifact_summary.get("warning_summary") or []),
        "is_batch": is_batch,
        "batch_kind": batch_kind,
        "aggregate": aggregate,
        "current_child_operation_id": current_child_operation_id,
        "current_child_case_id": current_child_case_id,
        "children_preview": children_preview or [],
        "token_usage": token_usage if token_usage is not None else artifact_summary.get("token_usage"),
        "planning_usage": planning_usage if planning_usage is not None else artifact_summary.get("planning_usage"),
        "execution_usage": execution_usage if execution_usage is not None else artifact_summary.get("execution_usage"),
        "attempt_usages": attempt_usages or list(artifact_summary.get("attempt_usages") or []),
    }


def token_usage_from_result_json(result_json: object) -> dict[str, Any] | None:
    return _validated_usage_dict(result_json, "token_usage", "total_usage")


def planning_usage_from_result_json(result_json: object) -> dict[str, Any] | None:
    return _validated_usage_dict(result_json, "planning_usage")


def execution_usage_from_result_json(result_json: object) -> dict[str, Any] | None:
    return _validated_usage_dict(result_json, "execution_usage")


def attempt_usages_from_result_json(result_json: object) -> list[dict[str, Any]]:
    if not isinstance(result_json, dict):
        return []
    raw_attempts = cast(object, result_json.get("attempts"))
    if not isinstance(raw_attempts, list):
        return []
    attempt_items = cast(list[object], raw_attempts)
    items: list[dict[str, Any]] = []
    for index, raw_attempt in enumerate(attempt_items):
        if not isinstance(raw_attempt, dict):
            continue
        raw_attempt_dict = cast(dict[str, object], raw_attempt)
        attempt_index = raw_attempt_dict.get("attempt_index")
        if not isinstance(attempt_index, int):
            attempt_index = index
        items.append(
            {
                "attempt_index": attempt_index,
                "runner_usage": _validated_usage_dict(raw_attempt_dict, "runner_usage"),
                "judge_usage": _validated_usage_dict(raw_attempt_dict, "judge_usage"),
                "total_usage": _validated_usage_dict(raw_attempt_dict, "total_usage"),
            }
        )
    return items


def _request_json(record: OperationRecord) -> dict[str, object]:
    return cast(dict[str, object], record.request_json) if isinstance(record.request_json, dict) else {}


def _result_json(record: OperationRecord) -> dict[str, object]:
    return cast(dict[str, object], record.result_json) if isinstance(record.result_json, dict) else {}


def _progress_json(record: OperationRecord) -> dict[str, object]:
    return cast(dict[str, object], record.progress_json) if isinstance(record.progress_json, dict) else {}


def _validated_usage_dict(source: object, *fields: str) -> dict[str, Any] | None:
    if not isinstance(source, dict):
        return None
    source_dict = cast(dict[str, object], source)
    for field in fields:
        raw = source_dict.get(field)
        if not isinstance(raw, dict):
            continue
        try:
            usage = TokenUsage.model_validate(raw)
        except Exception:
            continue
        return usage.model_dump(mode="json")
    return None


def _run_case_title_from_request_json(request_json: object) -> str | None:
    from munk.services.running.operation_payloads import run_case_title_from_request_json

    return run_case_title_from_request_json(request_json)


def _run_plans_plan_count_from_request_json(request_json: object) -> int | None:
    from munk.services.running.operation_payloads import run_plans_plan_count_from_request_json

    return run_plans_plan_count_from_request_json(request_json)


def _first_non_empty_string(*candidates: object) -> str:
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return ""
