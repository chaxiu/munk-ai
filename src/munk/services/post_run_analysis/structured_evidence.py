from __future__ import annotations

from pathlib import Path

from .evidence import load_artifact_payload
from .models import CaseRunEvidence


def build_case_run_structured_evidence(evidence: CaseRunEvidence) -> dict[str, object]:
    case_result = evidence.case_result
    structured: dict[str, object] = {}

    attempts = _attempt_payloads(
        case_result=case_result,
        loaded_attempts=_load_canonical_artifact(evidence, "attempts"),
    )
    if attempts:
        structured["attempts"] = attempts

    history = _load_canonical_artifact(evidence, "history")
    if not isinstance(history, list):
        history = _load_canonical_artifact(evidence, "runner_history")
    if isinstance(history, list):
        structured["history"] = history

    retry_handoffs = _load_canonical_artifact(evidence, "retry_handoffs")
    if isinstance(retry_handoffs, list):
        structured["retry_handoffs"] = retry_handoffs

    decision_trace = _load_canonical_artifact(evidence, "decision_trace")
    if isinstance(decision_trace, list):
        structured["decision_trace"] = decision_trace

    artifact_manifest = _load_canonical_artifact(evidence, "artifact_manifest")
    if isinstance(artifact_manifest, dict):
        structured["artifact_manifest"] = artifact_manifest

    if evidence.judge_result is not None:
        structured["judge_result"] = evidence.judge_result.model_dump(mode="json")

    return structured


def _load_canonical_artifact(evidence: CaseRunEvidence, artifact_id: str) -> object | None:
    canonical_path = evidence.canonical_artifacts.get(artifact_id)
    if canonical_path is not None:
        return load_artifact_payload(canonical_path)
    return load_artifact_payload(evidence.artifacts.get(artifact_id))


def _attempt_payloads(
    *,
    case_result: object,
    loaded_attempts: object | None,
) -> list[dict[str, object]]:
    if isinstance(loaded_attempts, list):
        return [dict(item) for item in loaded_attempts if isinstance(item, dict)]
    attempts = getattr(case_result, "attempts", None)
    if not isinstance(attempts, list):
        return []
    return [attempt.model_dump(mode="json") for attempt in attempts]
