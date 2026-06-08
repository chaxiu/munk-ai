from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from munk.execution.models import CaseExecutionRequest
from munk.orchestration import AgentDecision, EventHistoryEntry, StateDelta
from munk.running.orchestration_models import (
    RunnerExecutionContext,
    RunnerOrchestrationRequest,
    RunnerOrchestrationResult,
)
from munk.services.events import RunEvent
from munk.testing import TestCase

if TYPE_CHECKING:
    from munk.services.running.service import PreparedRunnerExecution, RunService


@dataclass(frozen=True)
class RunnerStepExecution:
    case_request: CaseExecutionRequest
    stage: PreparedRunnerExecution
    result: RunnerOrchestrationResult


class RunnerOrchestrationService:
    def __init__(self, *, run_service: RunService) -> None:
        self._run_service = run_service

    def execute(self, request: RunnerOrchestrationRequest) -> RunnerStepExecution:
        case_request = CaseExecutionRequest(
            plan_id=request.plan_id,
            case=self._apply_execution_context(request.case, request.execution_context),
            app_id=request.app_id,
            app_target=request.app_target,
            device_ref=request.device_ref,
            artifact_path=request.artifact_path,
            assets_root=request.assets_root,
            runtime_overrides=dict(request.runtime_overrides),
        )
        stage = self._run_service.execute_case_runtime_stage(case_request)
        result = RunnerOrchestrationResult(
            status=stage.execution.status,
            stop_reason=stage.execution.stop_reason,
            steps_completed=stage.execution.steps_completed,
            run_dir=stage.paths.run_dir,
            error_message=stage.execution.error_message,
            error_type=stage.execution.error_type,
            last_action_summary=stage.execution.last_action_summary,
            last_target_identity=stage.execution.last_target_identity,
            last_surface_identity=stage.execution.last_surface_identity,
            artifacts=dict(stage.artifacts),
            history_entries=[self._to_history_entry(event) for event in stage.events],
            state_delta=StateDelta(
                status="ready",
                next_step="judge",
                reason="runner execution completed",
            ),
            token_usage=stage.runtime_output.token_usage if stage.runtime_output is not None else None,
            decision=AgentDecision(
                decision_type="continue",
                target_step="judge",
                reason="runner execution completed",
            ),
        )
        return RunnerStepExecution(case_request=case_request, stage=stage, result=result)

    @staticmethod
    def _apply_execution_context(case: TestCase, execution_context: RunnerExecutionContext) -> TestCase:
        retry_handoff_message = (execution_context.retry_handoff_message or "").strip()
        if not retry_handoff_message:
            return case
        runner_goal = f"{case.runner_goal.strip()}\n\nRetry Context:\n{retry_handoff_message}"
        return case.model_copy(
            update={
                "runner_goal": runner_goal,
            }
        )

    @staticmethod
    def _to_history_entry(event: RunEvent) -> EventHistoryEntry:
        return EventHistoryEntry(
            event_type=event.type.value,
            timestamp=event.timestamp,
            step="runner",
            message=event.message,
            payload=dict(event.data),
        )
