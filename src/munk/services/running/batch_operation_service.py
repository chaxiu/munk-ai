from __future__ import annotations

from typing import Any, Protocol, cast

from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.config import ResolvedConfig
from munk.planning.models import RequirementPlan
from munk.planning.storage import PlanStore
from munk.services.errors import BatchPlanExecutionError, OperationCancelledError, PlanNotFoundError
from munk.services.machine_contracts import EXIT_OK, EXIT_OPERATION_CANCELLED
from munk.services.operations.command_helpers import merged_tracker_artifacts
from munk.services.operations.service import OperationCommandResult, OperationService, OperationTracker
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
        aggregate = self._empty_aggregate(total_children=len(plans))
        tracker.update_progress(
            phase="running",
            batch_kind="single_device_multi_plan",
            total_children=len(plans),
            completed_children=0,
        )
        tracker.append_event(
            event_type="batch_started",
            message="batch plan run started",
            data={
                "app_id": request.app_id,
                "device_ref": request.device_ref,
                "plan_ids": plan_ids,
                "total_children": len(plans),
            },
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
                total_children=len(plans),
            )
            child_summary = self._execute_child_plan(
                tracker=tracker,
                child_tracker=child_tracker,
                request=request,
                plan=plan,
                resolved_config=resolved_config,
            )
            child_records.append(child_summary)
            self._update_aggregate(aggregate, child_summary)
            tracker.update_progress(
                phase="running",
                batch_kind="single_device_multi_plan",
                total_children=len(plans),
                completed_children=len(child_records),
                current_child_operation_id=None,
                current_child_plan_id=None,
                current_child_title=None,
                last_child_operation_id=child_summary["operation_id"],
                last_child_plan_id=child_summary["plan_id"],
                last_child_title=child_summary["title"],
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
                    data={"plan_id": plan.plan_id, "operation_id": child_summary["operation_id"]},
                )
                break

        data = {
            "app_id": request.app_id,
            "device_ref": request.device_ref,
            "batch_kind": "single_device_multi_plan",
            "plan_ids": plan_ids,
            "total_children": len(plans),
            "completed_children": len(child_records),
            "stopped_early": stopped_early,
            "token_usage": _aggregate_token_usage_dict(child_records),
            "children": child_records,
            "aggregate": aggregate,
        }
        verification_verdict = self._aggregate_verdict(child_records)
        tracker.update_progress(
            phase="completed",
            batch_kind="single_device_multi_plan",
            total_children=len(plans),
            completed_children=len(child_records),
            verification_verdict=cast(Any, verification_verdict),
        )
        tracker.append_event(
            event_type="batch_finished",
            message="batch plan run finished",
            data={
                "total_children": len(plans),
                "completed_children": len(child_records),
                "verification_verdict": verification_verdict,
                "stopped_early": stopped_early,
            },
        )
        return OperationCommandResult(
            data=data,
            artifacts={},
            verification_verdict=cast(Any, verification_verdict),
            result_json=data,
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
        return self._operation_service.create_operation(
            kind="run_plan",
            request_json={
                **request.model_dump(mode="json"),
                "plan_id": plan.plan_id,
                "batch_kind": "single_device_multi_plan",
            },
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
    ) -> dict[str, Any]:
        position_label = child_tracker.get_record().position_label
        title = plan.name or plan.plan_id
        child_tracker.mark_running(
            pid=tracker.get_record().pid or child_tracker.get_record().pid or 0,
            progress={
                "phase": "running",
                "position_label": position_label,
                "parent_operation_id": tracker.operation_id,
            },
        )
        child_tracker.append_event(
            event_type="operation_started",
            message="child plan operation started",
            data={"parent_operation_id": tracker.operation_id, "position_label": position_label},
        )
        tracker.update_progress(
            phase="running",
            current_child_operation_id=child_tracker.operation_id,
            current_child_plan_id=plan.plan_id,
            current_child_title=title,
        )
        tracker.append_event(
            event_type="batch_child_started",
            message="batch child started",
            data={
                "operation_id": child_tracker.operation_id,
                "plan_id": plan.plan_id,
                "title": title,
                "position_label": position_label,
            },
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
                    progress={
                        "phase": "cancelled",
                        "parent_operation_id": tracker.operation_id,
                        "position_label": position_label,
                    }
                )
                return self._child_summary_from_record(child_tracker.get_record(), title=title)
            child_tracker.mark_failed(
                error_code="runtime_error",
                error_message=str(exc),
                progress={
                    "phase": "failed",
                    "parent_operation_id": tracker.operation_id,
                    "position_label": position_label,
                },
            )
            return self._child_summary_from_record(child_tracker.get_record(), title=title)

        merged_artifacts = merged_tracker_artifacts(child_tracker, result.artifacts)
        if child_tracker.cancel_observed or result.status == "cancelled":
            child_tracker.mark_cancelled(
                result_json=result.result_json or result.data,
                artifacts=merged_artifacts,
                progress={
                    "phase": "cancelled",
                    "parent_operation_id": tracker.operation_id,
                    "position_label": position_label,
                },
            )
        else:
            child_tracker.mark_succeeded(
                verification_verdict=result.verification_verdict,
                result_json=result.result_json or result.data,
                artifacts=merged_artifacts,
                progress={
                    "phase": "completed",
                    "parent_operation_id": tracker.operation_id,
                    "position_label": position_label,
                    "verification_verdict": result.verification_verdict,
                },
            )
        return self._child_summary_from_record(child_tracker.get_record(), title=title)

    @staticmethod
    def _child_summary_from_record(record, *, title: str) -> dict[str, Any]:  # noqa: ANN001
        return {
            "operation_id": record.operation_id,
            "plan_id": record.plan_id,
            "title": title,
            "status": record.status,
            "verification_verdict": record.verification_verdict,
            "position_index": record.position_index,
            "position_label": record.position_label,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "error_code": record.error_code,
            "error_message": record.error_message,
            "token_usage": _token_usage_dict_from_result_json(record.result_json),
        }

    @staticmethod
    def _empty_aggregate(*, total_children: int) -> dict[str, Any]:
        return {
            "total_children": total_children,
            "queued_children": total_children,
            "running_children": 0,
            "succeeded_children": 0,
            "failed_children": 0,
            "cancelled_children": 0,
            "completed_children": 0,
            "current_child_operation_id": None,
            "current_child_plan_id": None,
            "current_child_title": None,
            "token_usage": None,
        }

    @staticmethod
    def _update_aggregate(aggregate: dict[str, Any], child_summary: dict[str, Any]) -> None:
        aggregate["completed_children"] = int(aggregate.get("completed_children") or 0) + 1
        aggregate["queued_children"] = max(0, int(aggregate.get("queued_children") or 0) - 1)
        aggregate["running_children"] = 0
        aggregate["token_usage"] = _merge_token_usage_dicts(
            aggregate.get("token_usage"),
            child_summary.get("token_usage"),
        )
        status = child_summary["status"]
        if status == "succeeded":
            aggregate["succeeded_children"] = int(aggregate.get("succeeded_children") or 0) + 1
        elif status == "failed":
            aggregate["failed_children"] = int(aggregate.get("failed_children") or 0) + 1
        elif status == "cancelled":
            aggregate["cancelled_children"] = int(aggregate.get("cancelled_children") or 0) + 1
        aggregate["current_child_operation_id"] = None
        aggregate["current_child_plan_id"] = None
        aggregate["current_child_title"] = None

    @staticmethod
    def _aggregate_verdict(children: list[dict[str, Any]]) -> str | None:
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
