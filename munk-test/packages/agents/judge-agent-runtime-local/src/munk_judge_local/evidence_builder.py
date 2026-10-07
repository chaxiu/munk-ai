from __future__ import annotations

from munk.judging.models import (
    JudgeEvidence,
    JudgeExecutionEvidence,
    JudgeExecutionEvidencePayload,
    JudgeExecutionSummary,
    JudgeRequest,
)

from .evidence_builder_observation import _build_observation_evidence
from .evidence_builder_selection import MAX_PRIMARY_EVIDENCE as _MAX_PRIMARY_EVIDENCE, _select_primary_evidence
from .evidence_builder_support import (
    _build_event_evidence,
    _build_runner_history_evidence,
    _build_runner_issue_evidence,
    _build_runner_memory_evidence,
    _build_runtime_error_log_evidence,
    _build_screenshot_evidence,
    _build_screenshot_refs,
    _build_trace_evidence,
    _runner_issue_summary,
    _runner_memory_summary,
)
from .focus_terms import extract_focus_terms
from .models import JudgeEvidencePack

MAX_PRIMARY_EVIDENCE = _MAX_PRIMARY_EVIDENCE


def build_evidence_pack(
    *,
    request: JudgeRequest,
) -> JudgeEvidencePack:
    execution = request.execution
    artifacts = _artifacts_from_bundle(request)
    focus_terms = extract_focus_terms(request.intent, request.runner_goal, *request.expected)
    execution_evidence = JudgeExecutionEvidence(
        evidence_id="execution",
        kind="execution_outcome",
        source="execution",
        summary=_summarize_execution(execution),
        payload=JudgeExecutionEvidencePayload(
            status=execution.status,
            stop_reason=execution.stop_reason,
            steps_completed=execution.steps_completed,
            error_message=execution.error_message,
            error_type=execution.error_type,
            last_action_summary=execution.last_action_summary,
            last_target_identity=execution.last_target_identity,
            last_surface_identity=execution.last_surface_identity,
        ),
    )

    supporting_candidates: list[JudgeEvidence] = []
    supporting_candidates.extend(_build_event_evidence(request.events))

    runner_history_evidence = _build_runner_history_evidence(artifacts.get("runner_history"))
    supporting_candidates.extend(runner_history_evidence)

    runner_memory_evidence = _build_runner_memory_evidence(artifacts.get("runner_memory"))
    supporting_candidates.extend(runner_memory_evidence)

    runner_issue_evidence = _build_runner_issue_evidence(artifacts.get("runner_issues"))
    supporting_candidates.extend(runner_issue_evidence)

    supporting_candidates.extend(_build_trace_evidence(artifacts.get("decision_trace")))

    runtime_log_evidence = _build_runtime_error_log_evidence(artifacts.get("runtime_logs"))
    supporting_candidates.extend(runtime_log_evidence)

    frame_evidence = _build_observation_evidence(
        "screen_frame",
        artifacts.get("observation_frames"),
        focus_terms,
        tree_directory_value=artifacts.get("observation_tree"),
    )
    supporting_candidates.extend(frame_evidence)

    diff_evidence = _build_observation_evidence(
        "screen_diff",
        artifacts.get("observation_diffs"),
        focus_terms,
    )
    supporting_candidates.extend(diff_evidence)

    recent_raw_screenshots = _build_screenshot_refs(
        kind="raw",
        directory_value=artifacts.get("raw_screenshots"),
        frame_evidence=frame_evidence,
        diff_evidence=diff_evidence,
        runner_history_evidence=runner_history_evidence,
    )
    recent_annotated_screenshots = _build_screenshot_refs(
        kind="annotated",
        directory_value=artifacts.get("annotated_screenshots"),
        frame_evidence=frame_evidence,
        diff_evidence=diff_evidence,
        runner_history_evidence=runner_history_evidence,
    )
    supporting_candidates.extend(_build_screenshot_evidence(recent_raw_screenshots))

    primary_evidence = _select_primary_evidence(supporting_candidates, focus_terms)
    primary_ids = {item.evidence_id for item in primary_evidence}
    supporting_evidence = [item for item in supporting_candidates if item.evidence_id not in primary_ids]
    evidence: list[JudgeEvidence] = [execution_evidence, *primary_evidence, *supporting_evidence]

    return JudgeEvidencePack(
        plan_id=request.plan_id,
        case_id=request.case_id,
        case_title=request.case_title,
        intent=request.intent,
        preconditions=list(request.preconditions),
        expected=list(request.expected),
        runner_goal=request.runner_goal,
        ai_guidance=request.ai_guidance.model_copy(deep=True) if request.ai_guidance is not None else None,
        execution=execution,
        primary_evidence=primary_evidence,
        supporting_evidence=supporting_evidence,
        evidence=evidence,
        runner_memory_summary=_runner_memory_summary(runner_memory_evidence),
        runner_issue_summary=_runner_issue_summary(runner_issue_evidence),
        recent_raw_screenshots=recent_raw_screenshots,
        recent_annotated_screenshots=recent_annotated_screenshots,
        artifacts=artifacts,
    )


def _artifacts_from_bundle(request: JudgeRequest) -> dict[str, str]:
    bundle = request.evidence_bundle
    artifacts: dict[str, str] = {}
    field_map = {
        "runner_history": bundle.runner_history_path,
        "runner_memory": bundle.runner_memory_path,
        "runner_issues": bundle.runner_issues_path,
        "decision_trace": bundle.decision_trace_path,
        "runtime_logs": bundle.runtime_logs_path,
        "observation_frames": bundle.observation_frames_path,
        "observation_diffs": bundle.observation_diffs_path,
        "observation_tree": bundle.observation_tree_path,
        "raw_screenshots": bundle.raw_screenshots_path,
        "annotated_screenshots": bundle.annotated_screenshots_path,
        "llm_transcript": bundle.llm_transcript_path,
        "artifact_manifest": bundle.artifact_manifest_path,
    }
    for key, value in field_map.items():
        if value is not None:
            artifacts[key] = str(value)
    return artifacts


def _summarize_execution(execution: JudgeExecutionSummary) -> str:
    parts = [f"status={execution.status}"]
    if execution.stop_reason:
        parts.append(f"stop_reason={execution.stop_reason}")
    if execution.error_type:
        parts.append(f"error_type={execution.error_type}")
    if execution.error_message:
        parts.append(f"error_message={execution.error_message}")
    parts.append(f"steps_completed={execution.steps_completed}")
    if execution.last_action_summary:
        parts.append(f"last_action_summary={execution.last_action_summary}")
    if execution.last_target_identity:
        parts.append(f"last_target_identity={execution.last_target_identity}")
    if execution.last_surface_identity:
        parts.append(f"last_surface_identity={execution.last_surface_identity}")
    return "; ".join(parts)
