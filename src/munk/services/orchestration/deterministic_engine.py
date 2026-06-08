from __future__ import annotations

from typing import TYPE_CHECKING

from munk.orchestration import CaseWorkflowState, EventHistory, EventHistoryEntry
from munk.running.orchestration_models import RunnerExecutionContext, RunnerOrchestrationRequest
from munk.services.operations.service import OperationTracker
from munk.token_usage import merge_token_usages

from .judge_service import JudgeOrchestrationService
from .models import CaseAttemptRecord, CaseOrchestrationRequest, CaseOrchestrationResult
from .runner_service import RunnerOrchestrationService

if TYPE_CHECKING:
    from munk.services.running.service import RunService


class DeterministicOrchestrationEngine:
    def __init__(self, *, run_service: RunService, resolved_config, tracker=None, judge_runtime=None) -> None:  # noqa: ANN001
        self._runner_service = RunnerOrchestrationService(run_service=run_service)
        self._judge_service = JudgeOrchestrationService(
            resolved_config=resolved_config,
            tracker=tracker,
            judge_runtime=judge_runtime,
        )
        self._tracker: OperationTracker | None = tracker

    def execute_case(self, request: CaseOrchestrationRequest) -> CaseOrchestrationResult:
        state = CaseWorkflowState(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case=request.case,
            status="ready",
            current_step="runner",
        )
        history = EventHistory(
            entries=[
                EventHistoryEntry(
                    event_type="workflow_started",
                    step="runner",
                    payload={"case_id": request.case.case_id},
                )
            ]
        )
        self._emit_event(
            event_type="workflow_started",
            message="case orchestration started",
            data={"case_id": request.case.case_id},
        )
        attempts: list[CaseAttemptRecord] = []
        execution_context = RunnerExecutionContext()
        while True:
            self._emit_event(
                event_type="workflow_attempt_started",
                message="runner attempt started",
                data={
                    "attempt_index": len(attempts),
                    "case_id": request.case.case_id,
                    "retry_count": state.retry_count,
                },
            )
            runner_request = RunnerOrchestrationRequest(
                app_id=request.app_id,
                plan_id=request.plan_id,
                case_id=request.case.case_id,
                case=state.case,
                app_target=request.app_target,
                device_ref=request.device_ref,
                assets_root=request.assets_root,
                artifact_path=request.artifact_path,
                runtime_overrides=dict(request.runtime_overrides),
                execution_context=execution_context,
            )
            runner_step = self._runner_service.execute(runner_request)
            history.entries.extend(runner_step.result.history_entries)
            judge_step = self._judge_service.execute(
                runner_step=runner_step,
                state=state,
                policy=request.policy,
            )
            history.entries.extend(judge_step.history_entries)
            retry_handoff_message: str | None = None
            focus_items = [item.strip() for item in judge_step.retry_guidance.supplemental_context if item.strip()]
            if judge_step.decision.decision_type == "retry_with_context":
                retry_handoff_message = self._build_retry_handoff_message(
                    retry_attempt=state.retry_count + 1,
                    retry_reason=judge_step.retry_guidance.retry_reason,
                    supplemental_context=focus_items,
                )
            attempts.append(
                CaseAttemptRecord(
                    attempt_index=len(attempts),
                    runner=runner_step.result,
                    judge=judge_step,
                    retry_handoff_message=retry_handoff_message,
                    runner_usage=runner_step.result.token_usage,
                    judge_usage=judge_step.token_usage,
                    total_usage=merge_token_usages([runner_step.result.token_usage, judge_step.token_usage]),
                )
            )
            self._emit_event(
                event_type="workflow_attempt_finished",
                message="runner and judge attempt finished",
                data={
                    "attempt_index": len(attempts) - 1,
                    "verdict": judge_step.judge_result.verdict,
                    "decision_type": judge_step.decision.decision_type,
                },
            )
            state = self._apply_delta(
                state=state,
                status=judge_step.state_delta.status,
                next_step=judge_step.state_delta.next_step,
                reason=judge_step.state_delta.reason,
                retry_count_increment=judge_step.state_delta.retry_count_increment,
                supplemental_context=judge_step.state_delta.supplemental_context,
                artifacts={
                    **runner_step.result.artifacts,
                    **judge_step.artifacts,
                },
                verdict=judge_step.judge_result.verdict,
            )
            self._update_progress(
                orchestration_status=state.status,
                current_attempt=len(attempts),
                retry_count=state.retry_count,
                verification_verdict=state.last_verdict,
            )
            if judge_step.decision.decision_type != "retry_with_context":
                history.entries.append(
                    EventHistoryEntry(
                        event_type="workflow_finished",
                        step="judge",
                        payload={
                            "decision_type": judge_step.decision.decision_type,
                            "verdict": judge_step.judge_result.verdict,
                        },
                    )
                )
                self._emit_event(
                    event_type="workflow_finished",
                    message="case orchestration finished",
                    data={
                        "decision_type": judge_step.decision.decision_type,
                        "verdict": judge_step.judge_result.verdict,
                        "attempt_count": len(attempts),
                    },
                )
                return CaseOrchestrationResult(
                    request=request,
                    state=state,
                    final_decision=judge_step.decision,
                    history=history,
                    attempts=attempts,
                    artifacts=dict(state.artifact_index.artifacts),
                    token_usage=merge_token_usages([attempt.total_usage for attempt in attempts]),
                )
            self._emit_event(
                event_type="workflow_retry_scheduled",
                message="judge requested another runner attempt",
                data={
                    "attempt_index": len(attempts) - 1,
                    "retry_count": state.retry_count,
                    "retry_attempt": state.retry_count,
                    "reason": judge_step.retry_guidance.retry_reason,
                    "retry_reason": judge_step.retry_guidance.retry_reason,
                    "supplemental_context": list(focus_items),
                    "focus_items": list(focus_items),
                    "handoff_summary": retry_handoff_message,
                },
            )
            history.entries.append(
                EventHistoryEntry(
                    event_type="workflow_retry_scheduled",
                    step="judge",
                    message="judge requested another runner attempt",
                    payload={
                        "attempt_index": len(attempts) - 1,
                        "retry_count": state.retry_count,
                        "retry_attempt": state.retry_count,
                        "reason": judge_step.retry_guidance.retry_reason,
                        "retry_reason": judge_step.retry_guidance.retry_reason,
                        "supplemental_context": list(focus_items),
                        "focus_items": list(focus_items),
                        "handoff_summary": retry_handoff_message,
                    },
                )
            )
            execution_context = RunnerExecutionContext(
                attempt_index=state.retry_count,
                supplemental_context=list(focus_items),
                retry_reason=judge_step.retry_guidance.retry_reason,
                retry_handoff_message=retry_handoff_message,
            )

    @staticmethod
    def _apply_delta(
        *,
        state: CaseWorkflowState,
        status,
        next_step,
        reason: str | None,
        retry_count_increment: int,
        supplemental_context: list[str],
        artifacts: dict[str, str],
        verdict: str,
    ) -> CaseWorkflowState:
        metadata = dict(state.metadata)
        if reason:
            metadata["last_reason"] = reason
        return state.model_copy(
            update={
                "status": status or state.status,
                "current_step": next_step,
                "last_completed_step": "judge",
                "retry_count": state.retry_count + retry_count_increment,
                "last_verdict": verdict,
                "supplemental_context": list(supplemental_context),
                "artifact_index": state.artifact_index.model_copy(
                    update={
                        "artifacts": {
                            **state.artifact_index.artifacts,
                            **artifacts,
                        }
                    }
                ),
                "metadata": metadata,
            }
        )

    def _emit_event(self, *, event_type: str, message: str, data: dict[str, object]) -> None:
        if self._tracker is None:
            return
        self._tracker.append_event(event_type=event_type, message=message, data=data)

    def _update_progress(self, **progress: object) -> None:
        if self._tracker is None:
            return
        self._tracker.update_progress(**progress)

    @staticmethod
    def _build_retry_handoff_message(
        *,
        retry_attempt: int,
        retry_reason: str | None,
        supplemental_context: list[str],
    ) -> str:
        focus_items = [item.strip() for item in supplemental_context if item.strip()]
        lines = [f"This is retry attempt {retry_attempt} for the same test case."]
        if retry_reason and retry_reason.strip():
            lines.extend(["", "Previous judge assessment:", f"- {retry_reason.strip()}"])
        if focus_items:
            lines.extend(["", "Focus for this retry:"])
            lines.extend(f"- {item}" for item in focus_items)
        return "\n".join(lines)
