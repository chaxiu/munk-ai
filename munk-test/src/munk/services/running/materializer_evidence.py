from __future__ import annotations

from munk.judging.models import (
    JudgeDecisionTraceEvidence,
    JudgeDecisionTraceEvidencePayload,
    JudgeEvidence,
    JudgeRunnerHistoryEvidence,
    JudgeRunnerHistoryEvidencePayload,
    JudgeRunnerIssueEvidence,
    JudgeRunnerIssueEvidencePayload,
    JudgeRunnerMemoryEvidence,
    JudgeRunnerMemoryEvidencePayload,
    JudgeRuntimeErrorLogEvidence,
    JudgeRuntimeErrorLogEvidencePayload,
    JudgeScreenDiffEvidence,
    JudgeScreenDiffEvidencePayload,
    JudgeScreenFrameEvidence,
    JudgeScreenFrameEvidencePayload,
    JudgeScreenshotEvidence,
    JudgeScreenshotEvidencePayload,
    is_decision_trace_evidence,
    is_event_evidence,
    is_execution_evidence,
    is_runner_history_evidence,
    is_runner_issue_evidence,
    is_runner_memory_evidence,
    is_runtime_error_log_evidence,
    is_screen_diff_evidence,
    is_screen_frame_evidence,
    is_screenshot_evidence,
)


def compact_judge_evidence(evidence: JudgeEvidence) -> JudgeEvidence:
    if is_execution_evidence(evidence) or is_event_evidence(evidence):
        return evidence
    if is_decision_trace_evidence(evidence):
        return JudgeDecisionTraceEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeDecisionTraceEvidencePayload(
                path=evidence.payload.path,
                step_index=evidence.payload.step_index,
                attempt_index=evidence.payload.attempt_index,
                decision=evidence.payload.decision,
                action=evidence.payload.action,
                summary=evidence.payload.summary,
                result_summary=evidence.payload.result_summary,
                tool_name=evidence.payload.tool_name,
                tool_names=list(evidence.payload.tool_names),
                will_retry=evidence.payload.will_retry,
                seeded_element_count=evidence.payload.seeded_element_count,
                ui_elements_summary=evidence.payload.ui_elements_summary,
            ),
        )
    if is_runner_history_evidence(evidence):
        return JudgeRunnerHistoryEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeRunnerHistoryEvidencePayload(
                path=evidence.payload.path,
                latest_step_index=evidence.payload.latest_step_index,
                excerpt=list(evidence.payload.excerpt),
            ),
        )
    if is_runner_memory_evidence(evidence):
        return JudgeRunnerMemoryEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeRunnerMemoryEvidencePayload(
                path=evidence.payload.path,
                excerpt=list(evidence.payload.excerpt),
            ),
        )
    if is_runner_issue_evidence(evidence):
        return JudgeRunnerIssueEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeRunnerIssueEvidencePayload(
                path=evidence.payload.path,
                issue=evidence.payload.issue,
            ),
        )
    if is_runtime_error_log_evidence(evidence):
        return JudgeRuntimeErrorLogEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeRuntimeErrorLogEvidencePayload(
                path=evidence.payload.path,
                excerpt=evidence.payload.excerpt,
                step_indexes=list(evidence.payload.step_indexes),
            ),
        )
    if is_screen_frame_evidence(evidence):
        return JudgeScreenFrameEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeScreenFrameEvidencePayload(
                path=evidence.payload.path,
                step_index=evidence.payload.step_index,
                package=evidence.payload.package,
                tree_available=evidence.payload.tree_available,
                tree_summary=evidence.payload.tree_summary,
                compact_tree=evidence.payload.compact_tree.model_copy(deep=True),
                focus_hits=list(evidence.payload.focus_hits),
            ),
        )
    if is_screen_diff_evidence(evidence):
        return JudgeScreenDiffEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeScreenDiffEvidencePayload(
                path=evidence.payload.path,
                step_index=evidence.payload.step_index,
                summary=evidence.payload.summary,
                appeared_labels=list(evidence.payload.appeared_labels),
                updated_labels=list(evidence.payload.updated_labels),
                disappeared_labels=list(evidence.payload.disappeared_labels),
                linked_visual_changes=list(evidence.payload.linked_visual_changes),
            ),
        )
    if is_screenshot_evidence(evidence):
        return JudgeScreenshotEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=JudgeScreenshotEvidencePayload.model_validate(evidence.payload.model_dump(mode="json")),
        )
    return evidence
