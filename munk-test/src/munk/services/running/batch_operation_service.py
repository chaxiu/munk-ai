from __future__ import annotations

from typing import Any, Protocol, cast

from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.config import ResolvedConfig
from munk.planning.models import RequirementPlan
from munk.planning.storage import PlanStore
from munk.services.errors import BatchPlanExecutionError, OperationCancelledError, PlanNotFoundError
from munk.services.machine_contracts import EXIT_OK, EXIT_OPERATION_CANCELLED
from munk.services.operations.command_helpers import merged_tracker_artifacts
from munk.services.operations.models import OperationRecord, VerificationVerdict
from munk.services.operations.service import OperationCommandResult, OperationService, OperationTracker
from munk.services.running.operation_payloads import (
    build_run_plan_child_operation_progress_payload,
    build_run_plan_operation_request_payload,
    build_run_plans_aggregate_payload,
    build_run_plans_batch_child_started_payload,
    build_run_plans_batch_finished_payload,
    build_run_plans_batch_started_payload,
    build_run_plans_batch_stopped_early_payload,
    build_run_plans_child_summary_payload,
    build_run_plans_progress_payload,
    build_run_plans_result_payload,
    update_run_plans_aggregate_payload,
)
from munk.services.running.operation_service import RunOperationService
from munk.token_usage import TokenUsage, merge_token_usages


class RunOperationServiceLike(Protocol):
    def execute_plan(
        self,
        *,
        tracker: OperationTracker,
        request,
        resolved_config: ResolvedConfig,
        event_sink,
    ) -> OperationCommandResult: ...  # noqa: ANN001


class RunBatchOperationService:
    def __init__(
        self,
        *,
        operation_service: OperationService,
        run_operation_service: RunOperationServiceLike | None = None,
    ) -> None:
        self._operation_service = operation_service
        self._run_operation_service = run_operation_service or RunOperationService()

    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: RunPlansCliRequest,
        resolved_config: ResolvedConfig,
    ) -> OperationCommandResult:
        plan_ids = self._normalize_plan_ids(request.plan_ids)
        plans = self._load_plans(request, plan_ids)
        total_children = len(plans)
        aggregate = build_run_plans_aggregate_payload(total_children=total_children)
        tracker.update_progress(
            **build_run_plans_progress_payload(
                phase="running",
                total_children=total_children,
                completed_children=0,
            )
        )
        tracker.append_event(
            event_type="batch_started",
            message="batch plan run started",
            data=build_run_plans_batch_started_payload(
                app_id=request.app_id,
                device_ref=request.device_ref,
                plan_ids=plan_ids,
                total_children=total_children,
            ),
        )

        child_records: list[dict[str, Any]] = []
        stopped_early = False

        for index, plan in enumerate(plans, start=1):
            tracker.raise_if_cancelled()
            child_tracker = self._create_child_tracker(
                parent_tracker=tracker,
                request=request,
                plan=plan,
                position_index=index,
                total_children=total_children,
            )
            child_summary = self._execute_child_plan(
                tracker=tracker,
                child_tracker=child_tracker,
                request=request,
                plan=plan,
                resolved_config=resolved_config,
                total_children=total_children,
                completed_children=len(child_records),
            )
            child_records.append(child_summary)
            aggregate = update_run_plans_aggregate_payload(
                aggregate,
                child_summary_payload=child_summary,
            )
            tracker.update_progress(
                **build_run_plans_progress_payload(
                    phase="running",
                    total_children=total_children,
                    completed_children=len(child_records),
                    last_child_operation_id=child_summary["operation_id"],
                    last_child_plan_id=child_summary["plan_id"],
                    last_child_title=child_summary["title"],
                )
            )
            tracker.append_event(
                event_type="batch_child_finished",
                message="batch child finished",
                data=child_summary,
            )
            if tracker.cancel_observed or child_summary["status"] == "cancelled":
                raise OperationCancelledError("batch plan run cancelled")
            if request.fail_fast and child_summary["verification_verdict"] == "failed":
                stopped_early = True
                tracker.append_event(
                    event_type="batch_stopped_early",
                    message="batch plan run stopped early",
                    data=build_run_plans_batch_stopped_early_payload(
                        plan_id=plan.plan_id,
                        operation_id=child_summary["operation_id"],
                    ),
                )
                break

        verification_verdict = self._aggregate_verdict(child_records)
        tracker.update_progress(
            **build_run_plans_progress_payload(
                phase="completed",
                total_children=total_children,
                completed_children=len(child_records),
                verification_verdict=verification_verdict,
            )
        )
        tracker.append_event(
            event_type="batch_finished",
            message="batch plan run finished",
            data=build_run_plans_batch_finished_payload(
                total_children=total_children,
                completed_children=len(child_records),
                verification_verdict=verification_verdict,
                stopped_early=stopped_early,
            ),
        )
        result_payload = build_run_plans_result_payload(
            app_id=request.app_id,
            device_ref=request.device_ref,
            plan_ids=plan_ids,
            total_children=total_children,
            completed_children=len(child_records),
            stopped_early=stopped_early,
            verification_verdict=verification_verdict,
            token_usage=_aggregate_token_usage_dict(child_records),
            children=child_records,
            aggregate=aggregate,
        )
        return OperationCommandResult(
            data=result_payload,
            artifacts={},
            verification_verdict=cast(Any, verification_verdict),
            result_json=result_payload,
            status="succeeded",
            exit_code=EXIT_OPERATION_CANCELLED if tracker.cancel_observed else EXIT_OK,
        )

    @staticmethod
    def _normalize_plan_ids(plan_ids: list[str]) -> list[str]:
        normalized = [item.strip() for item in plan_ids if isinstance(item, str) and item.strip()]
        if not normalized:
            raise BatchPlanExecutionError("plan_ids must contain at least one plan")
        if len(set(normalized)) != len(normalized):
            raise BatchPlanExecutionError("plan_ids contains duplicate values")
        return normalized

    def _load_plans(self, request: RunPlansCliRequest, plan_ids: list[str]) -> list[RequirementPlan]:
        store = PlanStore(request.assets_root)
        plans: list[RequirementPlan] = []
        for plan_id in plan_ids:
            try:
                plan = store.load(request.app_id, plan_id)
            except FileNotFoundError as exc:
                raise PlanNotFoundError(str(exc)) from exc
            if plan.app_id != request.app_id:
                raise BatchPlanExecutionError(
                    f"plan '{plan.plan_id}' does not belong to app '{request.app_id}'"
                )
            plans.append(plan)
        return plans

    def _create_child_tracker(
        self,
        *,
        parent_tracker: OperationTracker,
        request: RunPlansCliRequest,
        plan: RequirementPlan,
        position_index: int,
        total_children: int,
    ) -> OperationTracker:
        child_request = request.to_plan_execution_request(plan_id=plan.plan_id)
        return self._operation_service.create_operation(
            kind="run_plan",
            request_json=build_run_plan_operation_request_payload(
                child_request,
                batch_kind="single_device_multi_plan",
            ),
            app_id=request.app_id,
            plan_id=plan.plan_id,
            case_id=None,
            parent_operation_id=parent_tracker.operation_id,
            batch_id=parent_tracker.operation_id,
            position_index=position_index,
            position_label=f"{position_index}/{total_children}",
            requires_device=False,
            device_ref=request.device_ref,
        )

    def _execute_child_plan(
        self,
        *,
        tracker: OperationTracker,
        child_tracker: OperationTracker,
        request: RunPlansCliRequest,
        plan: RequirementPlan,
        resolved_config: ResolvedConfig,
        total_children: int,
        completed_children: int,
    ) -> dict[str, Any]:
        position_label = child_tracker.get_record().position_label
        title = plan.name or plan.plan_id
        child_tracker.mark_running(
            pid=tracker.get_record().pid or child_tracker.get_record().pid or 0,
            progress=build_run_plan_child_operation_progress_payload(
                phase="running",
                parent_operation_id=tracker.operation_id,
                position_label=position_label,
            ),
        )
        child_tracker.append_event(
            event_type="operation_started",
            message="child plan operation started",
            data=build_run_plans_batch_child_started_payload(
                operation_id=child_tracker.operation_id,
                plan_id=plan.plan_id,
                title=title,
                parent_operation_id=tracker.operation_id,
                position_label=position_label,
            ),
        )
        tracker.update_progress(
            **build_run_plans_progress_payload(
                phase="running",
                total_children=total_children,
                completed_children=completed_children,
                current_child_operation_id=child_tracker.operation_id,
                current_child_plan_id=plan.plan_id,
                current_child_title=title,
            )
        )
        tracker.append_event(
            event_type="batch_child_started",
            message="batch child started",
            data=build_run_plans_batch_child_started_payload(
                operation_id=child_tracker.operation_id,
                plan_id=plan.plan_id,
                title=title,
                position_label=position_label,
            ),
        )
        try:
            result = self._run_operation_service.execute_plan(
                tracker=child_tracker,
                request=request.to_plan_execution_request(plan_id=plan.plan_id),
                resolved_config=resolved_config,
                event_sink=None,
            )
        except Exception as exc:
            if isinstance(exc, OperationCancelledError):
                child_tracker.mark_cancelled(
                    progress=build_run_plan_child_operation_progress_payload(
                        phase="cancelled",
                        parent_operation_id=tracker.operation_id,
                        position_label=position_label,
                    )
                )
                return self._child_summary_from_record(child_tracker.get_record(), title=title)
            child_tracker.mark_failed(
                error_code="runtime_error",
                error_message=str(exc),
                progress=build_run_plan_child_operation_progress_payload(
                    phase="failed",
                    parent_operation_id=tracker.operation_id,
                    position_label=position_label,
                ),
            )
            return self._child_summary_from_record(child_tracker.get_record(), title=title)

        merged_artifacts = merged_tracker_artifacts(child_tracker, result.artifacts)
        if child_tracker.cancel_observed or result.status == "cancelled":
            child_tracker.mark_cancelled(
                result_json=result.result_json or result.data,
                artifacts=merged_artifacts,
                progress=build_run_plan_child_operation_progress_payload(
                    phase="cancelled",
                    parent_operation_id=tracker.operation_id,
                    position_label=position_label,
                ),
            )
        else:
            child_tracker.mark_succeeded(
                verification_verdict=result.verification_verdict,
                result_json=result.result_json or result.data,
                artifacts=merged_artifacts,
                progress=build_run_plan_child_operation_progress_payload(
                    phase="completed",
                    parent_operation_id=tracker.operation_id,
                    position_label=position_label,
                    verification_verdict=result.verification_verdict,
                ),
            )
        return self._child_summary_from_record(child_tracker.get_record(), title=title)

    @staticmethod
    def _child_summary_from_record(record: OperationRecord, *, title: str) -> dict[str, Any]:
        return build_run_plans_child_summary_payload(record, title=title)

    @staticmethod
    def _aggregate_verdict(children: list[dict[str, Any]]) -> VerificationVerdict:
        verdicts = [item.get("verification_verdict") for item in children]
        if any(verdict == "failed" for verdict in verdicts):
            return "failed"
        if any(verdict == "inconclusive" for verdict in verdicts):
            return "inconclusive"
        if any(item.get("status") == "cancelled" for item in children):
            return "inconclusive"
        if children:
            return "passed"
        return None


def _token_usage_dict_from_result_json(result_json: object) -> dict[str, Any] | None:
    if not isinstance(result_json, dict):
        return None
    raw = result_json.get("token_usage")
    if not isinstance(raw, dict):
        return None
    try:
        usage = TokenUsage.model_validate(raw)
    except Exception:
        return None
    return usage.model_dump(mode="json")


def _merge_token_usage_dicts(*payloads: object) -> dict[str, Any] | None:
    usages: list[TokenUsage | None] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            usages.append(None)
            continue
        try:
            usages.append(TokenUsage.model_validate(payload))
        except Exception:
            usages.append(None)
    merged = merge_token_usages(usages)
    return merged.model_dump(mode="json") if merged is not None else None


def _aggregate_token_usage_dict(children: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _merge_token_usage_dicts(*(child.get("token_usage") for child in children))
