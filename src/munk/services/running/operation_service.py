from __future__ import annotations

from collections.abc import Callable
from typing import Any

from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionRequest, PlanExecutionRequest
from munk.services.errors import OperationCancelledError
from munk.services.events import RunEventSink
from munk.services.machine_contracts import verdict_exit_code
from munk.services.operations.command_helpers import merged_tracker_artifacts, verdict_from_execution_status
from munk.services.operations.service import OperationCommandResult, OperationService, OperationTracker
from munk.services.operations.submission_service import OperationSubmissionService
from munk.services.plan_execution_service import (
    PlanCaseExecutionOutcome,
    PlanExecutionService,
)
from munk.services.running.plan_operation_tracker_adapter import PlanOperationTrackerAdapter
from munk.services.running.operation_payloads import (
    build_run_case_child_operation_progress_payload,
    build_run_case_child_summary_payload,
    build_run_case_operation_started_payload,
    build_run_plan_batch_child_started_payload,
    build_run_case_operation_request_payload,
    build_run_plan_progress_payload,
    build_run_plan_operation_result_data,
    build_run_plan_operation_result_payload,
)
from munk.services.running.post_run_child_operations import run_case_completion_hooks
from munk.services.running.service import RunService

__all__ = ["OperationSubmissionService", "RunOperationService"]


class RunOperationService:
    def __init__(
        self,
        *,
        plan_execution_service_factory: Callable[
            [ResolvedConfig, OperationTracker, RunEventSink | None], PlanExecutionService
        ]
        | None = None,
    ) -> None:
        self._plan_execution_service_factory = plan_execution_service_factory or self._default_plan_execution_service

    def execute_case(
        self,
        *,
        tracker: OperationTracker,
        request: PlanExecutionRequest,
        case_id: str,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None,
    ) -> OperationCommandResult:
        result = self._plan_execution_service_factory(resolved_config, tracker, event_sink).execute_case_from_plan(
            request,
            case_id=case_id,
        )
        if not tracker.cancel_observed:
            run_case_completion_hooks(
                parent_tracker=tracker,
                request=request,
                result=result,
            )
        data = result.model_dump(mode="json")
        return OperationCommandResult(
            data=data,
            artifacts=dict(result.artifacts),
            verification_verdict=None if tracker.cancel_observed else result.verdict,
            result_json=data,
            status="cancelled" if tracker.cancel_observed else "succeeded",
            exit_code=verdict_exit_code(result.verdict),
        )

    def execute_plan(
        self,
        *,
        tracker: OperationTracker,
        request: PlanExecutionRequest,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None,
    ) -> OperationCommandResult:
        plan_service = self._plan_execution_service_factory(resolved_config, tracker, event_sink)
        result = plan_service.execute_plan_with_case_executor(
            request,
            case_executor=lambda case_request, position_index, total_cases: self._execute_plan_child_case(
                parent_tracker=tracker,
                request=request,
                case_request=case_request,
                position_index=position_index,
                total_cases=total_cases,
                resolved_config=resolved_config,
                event_sink=event_sink,
            ),
        )
        verdict = verdict_from_execution_status(result.status)
        artifacts = {
            "summary": str(result.summary_path),
            "report": str(result.report_path),
            "plan": str(result.summary_path.parent / "plan.json"),
        }
        data = build_run_plan_operation_result_data(result)
        return OperationCommandResult(
            data=data,
            artifacts=artifacts,
            verification_verdict=None if tracker.cancel_observed else verdict,
            result_json=build_run_plan_operation_result_payload(result, artifacts=artifacts),
            status="cancelled" if tracker.cancel_observed else "succeeded",
            exit_code=verdict_exit_code(verdict),
        )

    def _execute_plan_child_case(
        self,
        *,
        parent_tracker: OperationTracker,
        request: PlanExecutionRequest,
        case_request: CaseExecutionRequest,
        position_index: int,
        total_cases: int,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None,
    ) -> PlanCaseExecutionOutcome:
        operation_service = OperationService(parent_tracker.registry)
        case_id = case_request.case.case_id
        title = case_request.case.title or case_id
        child_tracker = operation_service.create_operation(
            kind="run_case",
            request_json=build_run_case_operation_request_payload(
                request,
                case_id=case_id,
                case_title=title,
                batch_kind="single_plan_multi_case",
            ),
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=case_id,
            parent_operation_id=parent_tracker.operation_id,
            batch_id=parent_tracker.operation_id,
            position_index=position_index,
            position_label=f"{position_index}/{total_cases}",
            requires_device=False,
            device_ref=request.device_ref,
        )
        position_label = child_tracker.get_record().position_label
        child_tracker.mark_running(
            pid=parent_tracker.get_record().pid or child_tracker.get_record().pid or 0,
            progress=build_run_case_child_operation_progress_payload(
                phase="running",
                parent_operation_id=parent_tracker.operation_id,
                case_id=case_id,
                case_title=title,
                position_label=position_label,
            ),
        )
        child_tracker.append_event(
            event_type="operation_started",
            message="child case operation started",
            data=build_run_case_operation_started_payload(
                parent_operation_id=parent_tracker.operation_id,
                case_id=case_id,
                case_title=title,
                position_label=position_label,
            ),
        )
        parent_tracker.update_progress(
            **build_run_plan_progress_payload(
                phase="running",
                current_child_operation_id=child_tracker.operation_id,
                current_child_case_id=case_id,
                current_child_title=title,
            )
        )
        parent_tracker.append_event(
            event_type="batch_child_started",
            message="plan child case started",
            data=build_run_plan_batch_child_started_payload(
                operation_id=child_tracker.operation_id,
                case_id=case_id,
                title=title,
                position_label=position_label,
            ),
        )
        child_plan_service = self._plan_execution_service_factory(resolved_config, child_tracker, event_sink)
        try:
            case_result = child_plan_service.execute_case_from_plan(request, case_id=case_id)
        except Exception as exc:
            if isinstance(exc, OperationCancelledError):
                child_tracker.mark_cancelled(
                    progress=build_run_case_child_operation_progress_payload(
                        phase="cancelled",
                        parent_operation_id=parent_tracker.operation_id,
                        case_id=case_id,
                        case_title=title,
                        position_label=position_label,
                    )
                )
                parent_tracker.append_event(
                    event_type="batch_child_finished",
                    message="plan child case cancelled",
                    data=self._child_case_summary(child_tracker, title=title),
                )
                raise
            child_tracker.mark_failed(
                error_code="runtime_error",
                error_message=str(exc),
                progress=build_run_case_child_operation_progress_payload(
                    phase="failed",
                    parent_operation_id=parent_tracker.operation_id,
                    case_id=case_id,
                    case_title=title,
                    position_label=position_label,
                ),
            )
            parent_tracker.append_event(
                event_type="batch_child_finished",
                message="plan child case failed",
                data=self._child_case_summary(child_tracker, title=title),
            )
            raise

        result_data: dict[str, Any] = case_result.model_dump(mode="json")
        result_json = result_data
        merged_artifacts = merged_tracker_artifacts(child_tracker, case_result.artifacts)
        child_status = "cancelled" if child_tracker.cancel_observed else "succeeded"
        if child_status == "cancelled":
            child_tracker.mark_cancelled(
                result_json=result_json,
                artifacts=merged_artifacts,
                progress=build_run_case_child_operation_progress_payload(
                    phase="cancelled",
                    parent_operation_id=parent_tracker.operation_id,
                    case_id=case_id,
                    case_title=title,
                    position_label=position_label,
                ),
            )
        else:
            child_tracker.mark_succeeded(
                verification_verdict=case_result.verdict,
                result_json=result_json,
                artifacts=merged_artifacts,
                progress=build_run_case_child_operation_progress_payload(
                    phase="completed",
                    parent_operation_id=parent_tracker.operation_id,
                    case_id=case_id,
                    case_title=title,
                    position_label=position_label,
                    verification_verdict=case_result.verdict,
                ),
            )
            run_case_completion_hooks(
                parent_tracker=child_tracker,
                request=request,
                result=case_result,
            )
        parent_tracker.update_progress(
            **build_run_plan_progress_payload(
                phase="running",
                last_child_operation_id=child_tracker.operation_id,
                last_child_case_id=case_id,
                last_child_title=title,
            )
        )
        parent_tracker.append_event(
            event_type="batch_child_finished",
            message="plan child case finished",
            data=self._child_case_summary(child_tracker, title=title),
        )
        return PlanCaseExecutionOutcome(
            result=case_result,
            operation_id=child_tracker.operation_id,
            status=child_status,
        )

    @staticmethod
    def _child_case_summary(child_tracker: OperationTracker, *, title: str) -> dict[str, Any]:
        record = child_tracker.get_record()
        return build_run_case_child_summary_payload(record, title=title)

    @staticmethod
    def _default_plan_execution_service(
        resolved_config: ResolvedConfig,
        tracker: OperationTracker,
        event_sink: RunEventSink | None,
    ) -> PlanExecutionService:
        return PlanExecutionService(
            resolved_config=resolved_config,
            run_service_factory=lambda: RunService(
                resolved_config=resolved_config,
                event_sink=event_sink,
                operation_tracker=tracker,
            ),
            operation_tracker=PlanOperationTrackerAdapter(tracker),
        )
