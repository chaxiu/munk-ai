from __future__ import annotations

from munk.execution.models import CaseExecutionResult

from .request_models import OptimizeTriggerCandidate

DEFAULT_OPTIMIZATION_CONFIDENCE_THRESHOLD = 0.7


class OptimizeCasePolicy:
    def __init__(self, *, writeback_confidence_threshold: float = DEFAULT_OPTIMIZATION_CONFIDENCE_THRESHOLD) -> None:
        self._writeback_confidence_threshold = writeback_confidence_threshold

    def should_trigger(
        self,
        *,
        result: CaseExecutionResult,
        candidate: OptimizeTriggerCandidate,
    ) -> bool:
        trigger = candidate.trigger
        if trigger.needs_optimization:
            return True
        if result.verdict in {"failed", "inconclusive"} and result.attempt_count > 1:
            return True
        if "retry_handoffs_present" in candidate.trigger_signals:
            return True
        if "runner_protocol_error" in candidate.trigger_signals:
            return True
        return "repeated_no_progress" in candidate.trigger_signals

    def should_apply_writeback(
        self,
        *,
        optimization_confidence: float | None,
        optimization_fields: list[str],
    ) -> bool:
        if not optimization_fields:
            return False
        if optimization_confidence is None:
            return False
        return optimization_confidence >= self._writeback_confidence_threshold
