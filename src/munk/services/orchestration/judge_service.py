from __future__ import annotations

from munk.execution.models import ExecutionOutcome
from munk.judging import JudgeOptimizationTrigger, JudgeOrchestrationResult, JudgeRetryGuidance
from munk.orchestration import AgentDecision, CaseWorkflowState, EventHistoryEntry, OrchestrationPolicy, StateDelta
from munk.services.judging import execute_case_judging

from .runner_service import RunnerStepExecution


class JudgeOrchestrationService:
    def __init__(self, *, resolved_config, tracker=None, judge_runtime=None) -> None:  # noqa: ANN001
        self._resolved_config = resolved_config
        self._tracker = tracker
        self._judge_runtime = judge_runtime

    def execute(
        self,
        *,
        runner_step: RunnerStepExecution,
        state: CaseWorkflowState,
        policy: OrchestrationPolicy,
    ) -> JudgeOrchestrationResult:
        materialized = execute_case_judging(
            request=runner_step.case_request,
            execution=self._build_execution_outcome(runner_step),
            events=list(runner_step.stage.events),
            artifacts=dict(runner_step.stage.artifacts),
            resolved_config=self._resolved_config,
            tracker=self._tracker,
            judge_runtime=self._judge_runtime,
        )
        decision, state_delta, retry_guidance = self._decide(
            state=state,
            policy=policy,
            reason=materialized.result.reason,
            verdict=materialized.result.verdict,
            missing_evidence=list(materialized.result.missing_evidence),
            failure_hypothesis=materialized.result.failure_hypothesis,
        )
        return JudgeOrchestrationResult(
            judge_result=materialized.result,
            decision=decision,
            state_delta=state_delta,
            retry_guidance=retry_guidance,
            optimization_trigger=JudgeOptimizationTrigger(
                needs_optimization=materialized.result.needs_optimization,
                optimization_fields=list(materialized.result.optimization_fields),
                optimization_reason=materialized.result.optimization_reason,
                optimization_confidence=materialized.result.optimization_confidence,
            ),
            artifacts=dict(materialized.artifacts),
            token_usage=materialized.result.token_usage,
            history_entries=[
                EventHistoryEntry(
                    event_type="judge_decision",
                    step="judge",
                    message=materialized.result.summary,
                    payload={
                        "verdict": materialized.result.verdict,
                        "reason": materialized.result.reason,
                        "decision_type": decision.decision_type,
                    },
                )
            ],
        )

    @staticmethod
    def _build_execution_outcome(runner_step: RunnerStepExecution) -> ExecutionOutcome:
        return runner_step.stage.execution

    @staticmethod
    def _decide(
        *,
        state: CaseWorkflowState,
        policy: OrchestrationPolicy,
        reason: str,
        verdict: str,
        missing_evidence: list[str],
        failure_hypothesis: str | None,
    ) -> tuple[AgentDecision, StateDelta, JudgeRetryGuidance]:
        supplemental_context = [item.strip() for item in missing_evidence if item.strip()]
        if failure_hypothesis and failure_hypothesis.strip():
            supplemental_context.append(failure_hypothesis.strip())
        retry_allowed = (
            (verdict == "failed" and policy.retry_on_failed)
            or (verdict == "inconclusive" and policy.retry_on_inconclusive)
        ) and state.retry_count < policy.max_retry_attempts
        if verdict == "passed":
            decision = AgentDecision(
                decision_type="finish",
                reason=reason,
                summary="judge accepted the case result",
            )
            delta = StateDelta(
                status="finished",
                next_step=None,
                reason=reason,
            )
            return decision, delta, JudgeRetryGuidance()
        if retry_allowed:
            decision = AgentDecision(
                decision_type="retry_with_context",
                target_step="runner",
                reason=reason,
                summary="judge requested another runner attempt",
                supplemental_context=supplemental_context,
            )
            delta = StateDelta(
                status="needs_retry",
                next_step="runner",
                retry_count_increment=1,
                reason=reason,
                supplemental_context=supplemental_context,
            )
            return (
                decision,
                delta,
                JudgeRetryGuidance(
                    supplemental_context=supplemental_context,
                    retry_reason=reason,
                ),
            )
        if policy.escalate_after_max_attempts:
            decision = AgentDecision(
                decision_type="escalate",
                reason=reason,
                summary="judge exhausted retry budget and escalated",
                supplemental_context=supplemental_context,
            )
            delta = StateDelta(
                status="escalated",
                reason=reason,
                supplemental_context=supplemental_context,
            )
            return (
                decision,
                delta,
                JudgeRetryGuidance(
                    supplemental_context=supplemental_context,
                    retry_reason=reason,
                ),
            )
        decision = AgentDecision(
            decision_type="finish",
            reason=reason,
            summary="judge produced a terminal verdict",
            supplemental_context=supplemental_context,
        )
        delta = StateDelta(
            status="finished",
            reason=reason,
            supplemental_context=supplemental_context,
        )
        return (
            decision,
            delta,
            JudgeRetryGuidance(
                supplemental_context=supplemental_context,
                retry_reason=reason,
            ),
        )
