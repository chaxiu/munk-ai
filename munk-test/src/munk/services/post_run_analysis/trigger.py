from __future__ import annotations

import json
from pathlib import Path

from munk.execution.models import CaseExecutionResult
from munk.judging import JudgeOptimizationTrigger, JudgeResult

from munk.services.optimization.request_models import OptimizeTriggerCandidate

from .evidence import (
    load_json_artifact,
    resolve_case_run_evidence,
    resolve_explicit_optimization_attempt,
    resolve_judge_result_path,
    resolve_source_attempt_index,
)


def should_trigger_knowledge_post_action(result: CaseExecutionResult) -> bool:
    if result.verdict == "passed":
        return False
    if "result" not in result.artifacts:
        return False
    evidence = resolve_case_run_evidence(result, prefer_optimization_attempt=False)
    return evidence.judge_result_path is not None


def build_optimize_trigger_candidate(result: CaseExecutionResult) -> OptimizeTriggerCandidate:
    explicit_trigger_index, explicit_trigger, explicit_judge_result_path = resolve_explicit_optimization_attempt(result)

    trigger_signals: list[str] = []
    if result.verdict in {"failed", "inconclusive"} and result.attempt_count > 1:
        trigger_signals.append("retried_terminal_failure")
    retry_handoffs = load_json_artifact(result.artifacts.get("retry_handoffs"))
    if isinstance(retry_handoffs, list) and retry_handoffs:
        trigger_signals.append("retry_handoffs_present")
    if result.execution.error_type == "RunnerProtocolError":
        trigger_signals.append("runner_protocol_error")
    if _has_repeated_no_progress(result):
        trigger_signals.append("repeated_no_progress")

    source_attempt_index = resolve_source_attempt_index(result, explicit_trigger_index)
    selected_judge_result_path = resolve_judge_result_path(
        result,
        source_attempt_index=source_attempt_index,
        explicit_path=explicit_judge_result_path,
    )

    trigger = explicit_trigger
    if trigger is None and selected_judge_result_path:
        trigger = _load_optimization_trigger(selected_judge_result_path)
    if trigger is None:
        trigger = JudgeOptimizationTrigger()

    if not trigger_signals and not trigger.needs_optimization:
        return OptimizeTriggerCandidate(
            trigger=trigger,
            trigger_source="judge",
            trigger_signals=[],
            source_attempt_index=source_attempt_index,
            judge_result_path=Path(selected_judge_result_path) if selected_judge_result_path else None,
        )

    trigger_source = "judge" if trigger.needs_optimization else "execution_heuristics"
    return OptimizeTriggerCandidate(
        trigger=trigger,
        trigger_source=trigger_source,
        trigger_signals=trigger_signals,
        source_attempt_index=source_attempt_index,
        judge_result_path=Path(selected_judge_result_path) if selected_judge_result_path else None,
    )


def _load_optimization_trigger(judge_result_path: str | None) -> JudgeOptimizationTrigger | None:
    if not judge_result_path:
        return None
    payload = json.loads(Path(judge_result_path).read_text(encoding="utf-8"))
    return _build_trigger_from_judge_payload(payload)


def _build_trigger_from_judge_payload(payload: object) -> JudgeOptimizationTrigger | None:
    if not isinstance(payload, dict):
        return None
    judge_result = JudgeResult.model_validate(payload)
    return JudgeOptimizationTrigger(
        needs_optimization=judge_result.needs_optimization,
        optimization_fields=list(judge_result.optimization_fields),
        optimization_reason=judge_result.optimization_reason,
        optimization_confidence=judge_result.optimization_confidence,
    )


def _has_repeated_no_progress(result: CaseExecutionResult) -> bool:
    if result.attempt_count <= 1:
        return False
    repeated_markers: dict[str, int] = {}
    for attempt in result.attempts:
        marker_parts = [
            (attempt.retry_reason or "").strip().lower(),
            (attempt.judge_reason or "").strip().lower(),
            (attempt.execution.stop_reason or "").strip().lower(),
            (attempt.execution.error_type or "").strip().lower(),
        ]
        marker = " | ".join(part for part in marker_parts if part)
        if not marker:
            continue
        repeated_markers[marker] = repeated_markers.get(marker, 0) + 1
        if repeated_markers[marker] >= 2:
            return True
    return False
