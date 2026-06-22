from __future__ import annotations

from typing import Any, cast

from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.execution.models import PlanExecutionRequest, PlanExecutionResult
from munk.services.operations.models import OperationRecord, VerificationVerdict
from munk.token_usage import TokenUsage, merge_token_usages

from .operation_payload_models import (
    PostRunChildOperationEventPayload,
    RunCaseBatchKind,
    RunCaseChildOperationProgressPayload,
    RunCaseChildSummary,
    RunCaseOperationRequest,
    RunCaseOperationStartedPayload,
    RunPlanBatchChildStartedPayload,
    RunPlanBatchKind,
    RunPlanChildOperationProgressPayload,
    RunPlanOperationData,
    RunPlanOperationRequest,
    RunPlanOperationResultPayload,
    RunPlanProgressPayload,
    RunPlansAggregate,
    RunPlansBatchChildStartedPayload,
    RunPlansBatchFinishedPayload,
    RunPlansBatchStartedPayload,
    RunPlansBatchStoppedEarlyPayload,
    RunPlansChildSummary,
    RunPlansOperationRequest,
    RunPlansProgressPayload,
    RunPlansResultPayload,
)


def build_run_case_operation_request_payload(
    request: PlanExecutionRequest,
    *,
    case_id: str,
    case_title: str | None = None,
    batch_kind: RunCaseBatchKind | None = None,
) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    payload["case_id"] = case_id
    if case_title is not None:
        payload["case_title"] = case_title
    if batch_kind is not None:
        payload["batch_kind"] = batch_kind
    RunCaseOperationRequest.model_validate(payload)
    return payload


def build_run_plan_operation_request_payload(
    request: PlanExecutionRequest,
    *,
    batch_kind: RunPlanBatchKind | None = None,
) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    if batch_kind is not None:
        payload["batch_kind"] = batch_kind
    RunPlanOperationRequest.model_validate(payload)
    return payload


def build_run_case_child_summary_payload(record: OperationRecord, *, title: str) -> dict[str, Any]:
    payload = RunCaseChildSummary(
        operation_id=record.operation_id,
        plan_id=record.plan_id,
        case_id=record.case_id,
        title=title,
        status=record.status,
        verification_verdict=record.verification_verdict,
        position_index=record.position_index,
        position_label=record.position_label,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        error_code=record.error_code,
        error_message=record.error_message,
        token_usage=_token_usage_from_result_json(record.result_json),
    )
    return payload.model_dump(mode="json")


def build_run_plan_progress_payload(
    *,
    phase: str,
    current_child_operation_id: str | None = None,
    current_child_case_id: str | None = None,
    current_child_title: str | None = None,
    last_child_operation_id: str | None = None,
    last_child_case_id: str | None = None,
    last_child_title: str | None = None,
) -> dict[str, Any]:
    payload = RunPlanProgressPayload(
        phase=phase,
        current_child_operation_id=current_child_operation_id,
        current_child_case_id=current_child_case_id,
        current_child_title=current_child_title,
        last_child_operation_id=last_child_operation_id,
        last_child_case_id=last_child_case_id,
        last_child_title=last_child_title,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_case_child_operation_progress_payload(
    *,
    phase: str,
    parent_operation_id: str,
    case_id: str,
    case_title: str | None = None,
    position_label: str | None = None,
    verification_verdict: VerificationVerdict = None,
) -> dict[str, Any]:
    payload = RunCaseChildOperationProgressPayload(
        phase=phase,
        parent_operation_id=parent_operation_id,
        position_label=position_label,
        case_id=case_id,
        case_title=case_title,
        verification_verdict=verification_verdict,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_plan_batch_child_started_payload(
    *,
    operation_id: str,
    case_id: str,
    title: str,
    position_label: str | None = None,
) -> dict[str, Any]:
    payload = RunPlanBatchChildStartedPayload(
        operation_id=operation_id,
        case_id=case_id,
        title=title,
        position_label=position_label,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_case_operation_started_payload(
    *,
    parent_operation_id: str,
    case_id: str,
    case_title: str | None = None,
    position_label: str | None = None,
) -> dict[str, Any]:
    payload = RunCaseOperationStartedPayload(
        parent_operation_id=parent_operation_id,
        case_id=case_id,
        case_title=case_title,
        position_label=position_label,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_plan_child_operation_progress_payload(
    *,
    phase: str,
    parent_operation_id: str,
    position_label: str | None = None,
    verification_verdict: VerificationVerdict = None,
) -> dict[str, Any]:
    payload = RunPlanChildOperationProgressPayload(
        phase=phase,
        parent_operation_id=parent_operation_id,
        position_label=position_label,
        verification_verdict=verification_verdict,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_plans_batch_started_payload(
    *,
    app_id: str,
    device_ref: str | None,
    plan_ids: list[str],
    total_children: int,
) -> dict[str, Any]:
    payload = RunPlansBatchStartedPayload(
        app_id=app_id,
        device_ref=device_ref,
        plan_ids=list(plan_ids),
        total_children=total_children,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_plans_batch_child_started_payload(
    *,
    operation_id: str,
    plan_id: str,
    title: str,
    parent_operation_id: str | None = None,
    position_label: str | None = None,
) -> dict[str, Any]:
    payload = RunPlansBatchChildStartedPayload(
        operation_id=operation_id,
        plan_id=plan_id,
        title=title,
        parent_operation_id=parent_operation_id,
        position_label=position_label,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_plans_batch_stopped_early_payload(*, plan_id: str, operation_id: str) -> dict[str, Any]:
    payload = RunPlansBatchStoppedEarlyPayload(plan_id=plan_id, operation_id=operation_id)
    return payload.model_dump(mode="json")


def build_run_plans_batch_finished_payload(
    *,
    total_children: int,
    completed_children: int,
    verification_verdict: VerificationVerdict,
    stopped_early: bool,
) -> dict[str, Any]:
    payload = RunPlansBatchFinishedPayload(
        total_children=total_children,
        completed_children=completed_children,
        verification_verdict=verification_verdict,
        stopped_early=stopped_early,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_post_run_child_operation_event_payload(
    *,
    child_kind: str,
    case_id: str,
    operation_id: str | None = None,
    request_path: str | None = None,
    error: str | None = None,
    optimization_fields: list[str] | None = None,
    trigger_source: str | None = None,
    trigger_signals: list[str] | None = None,
    source_attempt_index: int | None = None,
    judge_result_path: str | None = None,
) -> dict[str, Any]:
    payload = PostRunChildOperationEventPayload(
        child_kind=child_kind,
        case_id=case_id,
        operation_id=operation_id,
        request_path=request_path,
        error=error,
        optimization_fields=list(optimization_fields or []),
        trigger_source=trigger_source,
        trigger_signals=list(trigger_signals or []),
        source_attempt_index=source_attempt_index,
        judge_result_path=judge_result_path,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_run_plans_operation_request_payload(request: RunPlansCliRequest) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    RunPlansOperationRequest.model_validate(payload)
    return payload


def build_run_plans_child_summary_payload(record: OperationRecord, *, title: str) -> dict[str, Any]:
    payload = RunPlansChildSummary(
        operation_id=record.operation_id,
        plan_id=record.plan_id,
        title=title,
        status=record.status,
        verification_verdict=record.verification_verdict,
        position_index=record.position_index,
        position_label=record.position_label,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        error_code=record.error_code,
        error_message=record.error_message,
        token_usage=_token_usage_from_result_json(record.result_json),
    )
    return payload.model_dump(mode="json")


def build_run_plans_aggregate_payload(*, total_children: int) -> dict[str, Any]:
    payload = RunPlansAggregate(
        total_children=total_children,
        queued_children=total_children,
        running_children=0,
        succeeded_children=0,
        failed_children=0,
        cancelled_children=0,
        completed_children=0,
    )
    return payload.model_dump(mode="json")


def update_run_plans_aggregate_payload(
    aggregate_payload: object,
    *,
    child_summary_payload: object,
) -> dict[str, Any]:
    aggregate = RunPlansAggregate.model_validate(aggregate_payload)
    child_summary = RunPlansChildSummary.model_validate(child_summary_payload)
    updated = aggregate.model_copy(
        update={
            "completed_children": aggregate.completed_children + 1,
            "queued_children": max(0, aggregate.queued_children - 1),
            "running_children": 0,
            "succeeded_children": aggregate.succeeded_children + (1 if child_summary.status == "succeeded" else 0),
            "failed_children": aggregate.failed_children + (1 if child_summary.status == "failed" else 0),
            "cancelled_children": aggregate.cancelled_children + (1 if child_summary.status == "cancelled" else 0),
            "current_child_operation_id": None,
            "current_child_plan_id": None,
            "current_child_title": None,
            "token_usage": _merge_token_usages(aggregate.token_usage, child_summary.token_usage),
        }
    )
    return updated.model_dump(mode="json")


def build_run_plans_progress_payload(
    *,
    phase: str,
    total_children: int,
    completed_children: int,
    current_child_operation_id: str | None = None,
    current_child_plan_id: str | None = None,
    current_child_title: str | None = None,
    last_child_operation_id: str | None = None,
    last_child_plan_id: str | None = None,
    last_child_title: str | None = None,
    verification_verdict: VerificationVerdict = None,
) -> dict[str, Any]:
    payload = RunPlansProgressPayload(
        phase=phase,
        total_children=total_children,
        completed_children=completed_children,
        current_child_operation_id=current_child_operation_id,
        current_child_plan_id=current_child_plan_id,
        current_child_title=current_child_title,
        last_child_operation_id=last_child_operation_id,
        last_child_plan_id=last_child_plan_id,
        last_child_title=last_child_title,
        verification_verdict=verification_verdict,
    )
    return payload.model_dump(mode="json")


def build_run_plans_result_payload(
    *,
    app_id: str,
    device_ref: str | None,
    plan_ids: list[str],
    total_children: int,
    completed_children: int,
    stopped_early: bool,
    verification_verdict: VerificationVerdict,
    token_usage: dict[str, Any] | None,
    children: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> dict[str, Any]:
    payload = RunPlansResultPayload(
        app_id=app_id,
        device_ref=device_ref,
        plan_ids=list(plan_ids),
        total_children=total_children,
        completed_children=completed_children,
        stopped_early=stopped_early,
        verification_verdict=verification_verdict,
        token_usage=TokenUsage.model_validate(token_usage) if isinstance(token_usage, dict) else None,
        children=[RunPlansChildSummary.model_validate(item) for item in children],
        aggregate=RunPlansAggregate.model_validate(aggregate),
    )
    return payload.model_dump(mode="json")


def build_run_plan_operation_result_data(result: PlanExecutionResult) -> dict[str, Any]:
    payload = RunPlanOperationData(
        plan_id=result.plan_id,
        verification_status=result.status,
        total_cases=result.total_cases,
        passed_cases=result.passed_cases,
        failed_cases=result.failed_cases,
        inconclusive_cases=result.inconclusive_cases,
        stopped_early=result.stopped_early,
        summary_path=str(result.summary_path),
        report_path=str(result.report_path),
        items=list(result.items),
        token_usage=result.token_usage,
    )
    return payload.model_dump(mode="json")


def build_run_plan_operation_result_payload(
    result: PlanExecutionResult,
    *,
    artifacts: dict[str, str],
) -> dict[str, Any]:
    payload = RunPlanOperationResultPayload(
        **build_run_plan_operation_result_data(result),
        artifacts=artifacts,
    )
    return payload.model_dump(mode="json")


def _token_usage_from_result_json(result_json: object) -> TokenUsage | None:
    if not isinstance(result_json, dict):
        return None
    result_json_dict = cast(dict[str, object], result_json)
    raw_usage = result_json_dict.get("token_usage")
    if not isinstance(raw_usage, dict):
        return None
    try:
        return TokenUsage.model_validate(raw_usage)
    except Exception:
        return None


def _merge_token_usages(*usages: TokenUsage | None) -> TokenUsage | None:
    return merge_token_usages(usages)
