from __future__ import annotations

from collections.abc import Callable
from typing import Any

from munk.config import ResolvedConfig
from munk.execution.models import GeneratedPlanResult, PhasedOperationResult, PlanExecutionRequest
from munk.planning.models import RequirementInput
from munk.services.machine_contracts import EXIT_OK, verdict_exit_code
from munk.services.operations.command_helpers import (
    build_executed_plan_result,
    build_phased_operation_data,
    merge_scene_usages,
    verdict_from_execution_status,
)
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.services.plan_execution_service import PlanExecutionService, SupportsPlanOperationRecord
from munk.services.plan_runtime import resolve_plan_runtime
from munk.services.planning.orchestration import (
    build_plan_saved_payload,
    build_planning_storage_bundle,
    execute_plan_generation,
)
from munk.services.running.service import RunService


class _TrackerWithCallback:
    def __init__(
        self,
        tracker: OperationTracker,
        callback: Callable[[str, str | None, dict[str, Any]], None] | None,
    ) -> None:
        self._tracker = tracker
        self._callback = callback
        self.operation_id: str | None = tracker.operation_id

    def append_event(self, event_type: str, message: str | None, data: dict[str, Any] | None = None) -> None:
        payload = data or {}
        self._tracker.append_event(event_type=event_type, message=message, data=payload)
        if self._callback is not None:
            self._callback(event_type, message, payload)

    def update_progress(self, **progress: Any) -> None:
        self._tracker.update_progress(**progress)

    def should_cancel(self) -> bool:
        return self._tracker.should_cancel()


class PlanOperationService:
    def __init__(
        self,
        *,
        plan_execution_service_factory: Callable[[ResolvedConfig, OperationTracker], PlanExecutionService] | None = None,
    ) -> None:
        self._plan_execution_service_factory = plan_execution_service_factory or self._default_plan_execution_service

    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: RequirementInput,
        plan_execution_request: PlanExecutionRequest | None,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None,
        resolved_config: ResolvedConfig,
    ) -> OperationCommandResult:
        storage = build_planning_storage_bundle(assets_root=getattr(request, "assets_root", None))
        tracker_with_callback = _TrackerWithCallback(tracker, progress_callback)
        materialized = execute_plan_generation(
            tracker=tracker_with_callback,
            request=request,
            resolved_config=resolved_config,
            storage=storage,
            runtime_factory=self._resolve_runtime,
        )
        saved_payload = build_plan_saved_payload(materialized)
        tracker.append_event(
            event_type="plan_saved",
            message="plan saved",
            data=saved_payload,
        )
        tracker.update_progress(
            **self._plan_progress_payload(
                "plan_saved",
                saved_payload,
            )
        )
        if progress_callback is not None:
            progress_callback(
                "plan_saved",
                "plan saved",
                saved_payload,
            )
        tracker.update_operation(
            app_id=materialized.plan.app_id,
            plan_id=materialized.plan.plan_id,
        )
        phased_result = PhasedOperationResult(
            app_id=materialized.plan.app_id,
            plan_id=materialized.plan.plan_id,
            plan_name=materialized.plan.name,
            phase="planned",
            plan_result=GeneratedPlanResult(
                plan_name=materialized.plan.name,
                case_count=len(materialized.plan.cases),
                plan_path=materialized.plan_path,
                snapshot_path=materialized.snapshot_path,
                planning_usage=materialized.planning_usage,
            ),
            planning_usage=materialized.planning_usage,
            total_usage=materialized.planning_usage,
        )
        artifacts: dict[str, str] = {
            "plan": str(materialized.plan_path),
            "snapshot": str(materialized.snapshot_path),
        }
        verdict: str | None = None
        exit_code = EXIT_OK
        if plan_execution_request is not None:
            execution_request = plan_execution_request.model_copy(
                update={"app_id": materialized.plan.app_id, "plan_id": materialized.plan.plan_id}
            )
            execution = self._plan_execution_service_factory(resolved_config, tracker).execute_plan(execution_request)
            phased_result = phased_result.model_copy(
                update={
                    "phase": "executed",
                    "execution_result": build_executed_plan_result(execution),
                    "execution_usage": execution.token_usage,
                    "total_usage": merge_scene_usages(materialized.planning_usage, execution.token_usage),
                }
            )
            verdict = verdict_from_execution_status(execution.status)
            exit_code = verdict_exit_code(verdict)
            artifacts.update(
                {
                    "summary": str(execution.summary_path),
                    "report": str(execution.report_path),
                    "execution_plan": str(execution.summary_path.parent / "plan.json"),
                }
            )
        data = build_phased_operation_data(phased_result)
        return OperationCommandResult(
            data=data,
            artifacts=artifacts,
            verification_verdict=None if tracker.cancel_observed else verdict,
            result_json=data,
            status="cancelled" if tracker.cancel_observed else "succeeded",
            exit_code=exit_code,
        )

    @staticmethod
    def _resolve_runtime(resolved_config: ResolvedConfig):
        return resolve_plan_runtime(resolved_config=resolved_config)

    @staticmethod
    def _default_plan_execution_service(
        resolved_config: ResolvedConfig,
        tracker: OperationTracker,
    ) -> PlanExecutionService:
        return PlanExecutionService(
            resolved_config=resolved_config,
            run_service_factory=lambda: RunService(
                resolved_config=resolved_config,
                operation_tracker=tracker,
            ),
            operation_tracker=_PlanExecutionTrackerAdapter(tracker),
        )

    @staticmethod
    def _plan_progress_payload(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        progress: dict[str, Any] = {
            "plan_event_type": event_type,
        }
        stage_map = {
            "plan_context_loaded": "context_loaded",
            "plan_agent_ready": "agent_ready",
            "plan_skeleton_generation_started": "skeleton_generation_started",
            "plan_skeleton_generated": "skeleton_generated",
            "plan_case_generation_started": "case_generation_started",
            "plan_case_generated": "case_generated",
            "plan_finalize_started": "finalize_started",
            "plan_finalize_completed": "finalize_completed",
            "plan_saved": "saved",
        }
        if event_type in stage_map:
            progress["stage"] = stage_map[event_type]
        for key in (
            "app_id",
            "plan_id",
            "plan_name",
            "target_case_count",
            "completed_case_count",
            "case_index",
            "case_id",
            "case_title",
            "case_count",
            "plan_path",
            "snapshot_path",
        ):
            if key in data and data[key] is not None:
                progress[key] = data[key]
        return progress


class _PlanExecutionTrackerAdapter:
    def __init__(self, tracker: OperationTracker) -> None:
        self._tracker = tracker

    def should_cancel(self) -> bool:
        return self._tracker.should_cancel()

    def raise_if_cancelled(self) -> None:
        self._tracker.raise_if_cancelled()

    def update_artifacts(self, artifacts: dict[str, str]) -> object:
        return self._tracker.update_artifacts(artifacts)

    def update_progress(self, **progress: object) -> object:
        return self._tracker.update_progress(**progress)

    def get_record(self) -> SupportsPlanOperationRecord:
        return self._tracker.get_record()
