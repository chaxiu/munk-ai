from __future__ import annotations

import json
from pathlib import Path

from munk.execution.models import CaseExecutionResult
from munk.judging import JudgeOptimizationTrigger, JudgeResult

from .models import (
    ATTEMPT_CANONICAL_ARTIFACT_IDS,
    TOP_LEVEL_CANONICAL_ARTIFACT_IDS,
    CaseRunEvidence,
)


def load_json_artifact(path_value: str | Path | None) -> object | None:
    return load_artifact_payload(path_value)


def load_artifact_payload(path_value: str | Path | None) -> object | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    if path.suffix == ".jsonl":
        items: list[object] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return items
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def load_judge_result(path: Path | None) -> JudgeResult | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    return JudgeResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


def resolve_explicit_optimization_attempt(
    result: CaseExecutionResult,
) -> tuple[int | None, JudgeOptimizationTrigger | None, str | None]:
    orchestration_payload = load_json_artifact(result.artifacts.get("orchestration_result"))
    attempt_payloads = (
        orchestration_payload.get("attempts", [])
        if isinstance(orchestration_payload, dict)
        else []
    )
    for attempt_payload in attempt_payloads:
        if not isinstance(attempt_payload, dict):
            continue
        judge_payload = attempt_payload.get("judge")
        if not isinstance(judge_payload, dict):
            continue
        trigger_payload = judge_payload.get("optimization_trigger")
        trigger = _build_trigger_from_payload(trigger_payload)
        if trigger is None or not trigger.needs_optimization:
            continue
        attempt_index = attempt_payload.get("attempt_index")
        if not isinstance(attempt_index, int):
            continue
        explicit_judge_result_path: str | None = None
        judge_artifacts = judge_payload.get("artifacts")
        if isinstance(judge_artifacts, dict):
            raw_path = judge_artifacts.get("judge_result")
            if isinstance(raw_path, str) and raw_path.strip():
                explicit_judge_result_path = raw_path
        return attempt_index, trigger, explicit_judge_result_path
    return None, None, None


def resolve_source_attempt_index(
    result: CaseExecutionResult,
    explicit_index: int | None,
) -> int | None:
    if explicit_index is not None:
        return explicit_index
    if not result.attempts:
        return None
    for attempt in result.attempts:
        if attempt.verdict in {"failed", "inconclusive"}:
            return attempt.attempt_index
    return result.attempts[-1].attempt_index


def resolve_judge_result_path(
    result: CaseExecutionResult,
    *,
    source_attempt_index: int | None,
    explicit_path: str | None,
) -> str | None:
    if explicit_path:
        return explicit_path
    if source_attempt_index is not None and 0 <= source_attempt_index < len(result.attempts):
        raw_path = result.attempts[source_attempt_index].artifacts.get("judge_result")
        if raw_path:
            return raw_path
    fallback_path = result.artifacts.get("judge_result")
    if fallback_path:
        return fallback_path
    return None


def build_canonical_artifact_paths(
    result: CaseExecutionResult,
    source_attempt_index: int | None,
) -> dict[str, Path]:
    canonical: dict[str, Path] = {}
    for artifact_id in TOP_LEVEL_CANONICAL_ARTIFACT_IDS:
        raw_path = result.artifacts.get(artifact_id)
        if raw_path:
            canonical[artifact_id] = Path(raw_path)
    if source_attempt_index is not None and 0 <= source_attempt_index < len(result.attempts):
        for artifact_id, raw_path in result.attempts[source_attempt_index].artifacts.items():
            if artifact_id in ATTEMPT_CANONICAL_ARTIFACT_IDS and raw_path:
                canonical[artifact_id] = Path(raw_path)
    return canonical


def merge_canonical_artifacts(
    artifacts: dict[str, str],
    canonical: dict[str, Path],
) -> dict[str, str]:
    merged = dict(artifacts)
    for artifact_id, path in canonical.items():
        if artifact_id not in merged:
            merged[artifact_id] = str(path)
    return merged


def resolve_case_run_evidence(
    result: CaseExecutionResult,
    *,
    judge_result_path: Path | None = None,
    prefer_optimization_attempt: bool = True,
) -> CaseRunEvidence:
    explicit_index: int | None = None
    explicit_judge_path: str | None = None
    if prefer_optimization_attempt:
        explicit_index, _explicit_trigger, explicit_judge_path = resolve_explicit_optimization_attempt(result)
    source_attempt_index = resolve_source_attempt_index(result, explicit_index)
    selected_path = resolve_judge_result_path(
        result,
        source_attempt_index=source_attempt_index,
        explicit_path=str(judge_result_path) if judge_result_path is not None else explicit_judge_path,
    )
    resolved_judge_path = Path(selected_path) if selected_path else None
    if judge_result_path is not None:
        resolved_judge_path = judge_result_path
    canonical_artifacts = build_canonical_artifact_paths(result, source_attempt_index)
    if resolved_judge_path is not None:
        canonical_artifacts["judge_result"] = resolved_judge_path
    artifacts = merge_canonical_artifacts(result.artifacts, canonical_artifacts)
    return CaseRunEvidence(
        case_result=result,
        source_attempt_index=source_attempt_index,
        judge_result_path=resolved_judge_path,
        judge_result=load_judge_result(resolved_judge_path),
        artifacts=artifacts,
        canonical_artifacts=canonical_artifacts,
    )


def _build_trigger_from_payload(payload: object) -> JudgeOptimizationTrigger | None:
    if not isinstance(payload, dict):
        return None
    try:
        return JudgeOptimizationTrigger.model_validate(payload)
    except Exception:
        return None
