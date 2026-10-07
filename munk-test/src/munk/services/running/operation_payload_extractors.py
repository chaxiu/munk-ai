from __future__ import annotations

from typing import Any, cast

from .operation_payload_models import (
    RunCaseOperationRequest,
    RunPlanOperationRequest,
    RunPlansOperationRequest,
    RunPlansProgressPayload,
    RunPlansResultPayload,
)


def run_plan_batch_kind_from_request_json(request_json: object) -> str | None:
    if not isinstance(request_json, dict):
        return None
    request_json_dict = cast(dict[str, object], request_json)
    try:
        request = RunPlanOperationRequest.model_validate(request_json_dict)
    except Exception:
        raw_batch_kind = request_json_dict.get("batch_kind")
        return raw_batch_kind if isinstance(raw_batch_kind, str) and raw_batch_kind.strip() else None
    return request.batch_kind


def run_plans_plan_ids_from_request_json(request_json: object) -> list[str]:
    if not isinstance(request_json, dict):
        return []
    request_json_dict = cast(dict[str, object], request_json)
    try:
        request = RunPlansOperationRequest.model_validate(request_json_dict)
    except Exception:
        raw_plan_ids = request_json_dict.get("plan_ids")
        if not isinstance(raw_plan_ids, list):
            return []
        raw_plan_id_items = cast(list[object], raw_plan_ids)
        return [item.strip() for item in raw_plan_id_items if isinstance(item, str) and item.strip()]
    return list(request.plan_ids)


def run_plans_plan_count_from_request_json(request_json: object) -> int | None:
    plan_ids = run_plans_plan_ids_from_request_json(request_json)
    return len(plan_ids) if plan_ids else None


def run_plans_batch_kind_from_payloads(*payloads: object) -> str | None:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        payload_dict = cast(dict[str, object], payload)
        try:
            progress = RunPlansProgressPayload.model_validate(payload_dict)
        except Exception:
            progress = None
        if progress is not None:
            return progress.batch_kind
        try:
            result = RunPlansResultPayload.model_validate(payload_dict)
        except Exception:
            result = None
        if result is not None:
            return result.batch_kind
        try:
            request = RunPlansOperationRequest.model_validate(payload_dict)
        except Exception:
            request = None
        if request is not None:
            return "single_device_multi_plan"
        raw_batch_kind = payload_dict.get("batch_kind")
        if isinstance(raw_batch_kind, str) and raw_batch_kind.strip():
            return raw_batch_kind
    return None


def run_plans_aggregate_from_result_json(result_json: object) -> dict[str, Any] | None:
    if not isinstance(result_json, dict):
        return None
    result_json_dict = cast(dict[str, object], result_json)
    try:
        result = RunPlansResultPayload.model_validate(result_json_dict)
    except Exception:
        raw_aggregate = result_json_dict.get("aggregate")
        return cast(dict[str, Any], raw_aggregate) if isinstance(raw_aggregate, dict) else None
    return result.aggregate.model_dump(mode="json")


def run_plans_children_from_result_json(result_json: object) -> list[dict[str, Any]]:
    if not isinstance(result_json, dict):
        return []
    result_json_dict = cast(dict[str, object], result_json)
    try:
        result = RunPlansResultPayload.model_validate(result_json_dict)
    except Exception:
        raw_children = result_json_dict.get("children")
        if not isinstance(raw_children, list):
            return []
        raw_child_items = cast(list[object], raw_children)
        return [cast(dict[str, Any], item) for item in raw_child_items if isinstance(item, dict)]
    return [item.model_dump(mode="json") for item in result.children]


def run_plans_children_preview_from_result_json(result_json: object) -> list[dict[str, Any]]:
    children = run_plans_children_from_result_json(result_json)
    previews: list[dict[str, Any]] = []
    for child in children:
        preview = dict(child)
        preview.setdefault("kind", "run_plan")
        preview.setdefault("run_type", "plan_run")
        preview.setdefault("case_id", None)
        previews.append(preview)
    return previews


def run_plans_current_child_operation_id_from_progress_json(progress_json: object) -> str | None:
    if not isinstance(progress_json, dict):
        return None
    progress_json_dict = cast(dict[str, object], progress_json)
    try:
        progress = RunPlansProgressPayload.model_validate(progress_json_dict)
    except Exception:
        raw_operation_id = progress_json_dict.get("current_child_operation_id")
        return raw_operation_id if isinstance(raw_operation_id, str) and raw_operation_id.strip() else None
    return progress.current_child_operation_id


def run_case_title_from_request_json(request_json: object) -> str | None:
    if not isinstance(request_json, dict):
        return None
    request_json_dict = cast(dict[str, object], request_json)
    try:
        request = RunCaseOperationRequest.model_validate(request_json_dict)
    except Exception:
        raw_title = request_json_dict.get("case_title")
        return raw_title.strip() if isinstance(raw_title, str) and raw_title.strip() else None
    if isinstance(request.case_title, str) and request.case_title.strip():
        return request.case_title.strip()
    return None
