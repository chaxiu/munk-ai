from __future__ import annotations

from munk.knowledge_agent.models import (
    KnowledgeAgentEvidenceBundle,
    KnowledgeAgentRequest,
    KnowledgeArtifactRef,
)

from .models import CaseRunEvidence, PostRunAnalysisAgentInput
from .structured_evidence import build_case_run_structured_evidence

KNOWLEDGE_DEFAULT_REQUIREMENTS = {
    "output_kind": "knowledge_candidate_submissions",
    "prefer_zero_or_few_candidates": True,
    "must_be_reviewable": True,
    "must_be_grounded_in_run_evidence": True,
}


def build_post_run_analysis_agent_input(
    evidence: CaseRunEvidence,
    *,
    app_id: str | None = None,
    case_title: str | None = None,
    requirements: dict[str, object] | None = None,
) -> PostRunAnalysisAgentInput:
    case_result = evidence.case_result
    judge_summary = (
        evidence.judge_result.model_dump(mode="json")
        if evidence.judge_result is not None
        else {}
    )
    return PostRunAnalysisAgentInput(
        app_id=app_id or case_result.app_id or "",
        plan_id=case_result.plan_id,
        case_id=case_result.case_id,
        case_title=case_title or case_result.summary,
        run_dir=case_result.run_dir,
        execution_summary={
            "verdict": case_result.verdict,
            "summary": case_result.summary,
            "judge_reason": case_result.judge_reason,
            "attempt_count": case_result.attempt_count,
            "retry_count": max(0, case_result.attempt_count - 1),
        },
        judge_summary=judge_summary,
        artifacts=dict(evidence.artifacts),
        structured_evidence=build_case_run_structured_evidence(evidence),
        source_attempt_index=evidence.source_attempt_index,
        requirements=dict(requirements or KNOWLEDGE_DEFAULT_REQUIREMENTS),
    )


def build_knowledge_agent_request(
    agent_input: PostRunAnalysisAgentInput,
    evidence: CaseRunEvidence,
) -> KnowledgeAgentRequest:
    if evidence.judge_result is None:
        raise ValueError("knowledge agent request requires a judge result")
    artifact_refs = [
        KnowledgeArtifactRef(artifact_id=artifact_id, path=path)
        for artifact_id, path in sorted(evidence.canonical_artifacts.items())
    ]
    return KnowledgeAgentRequest(
        app_id=agent_input.app_id,
        plan_id=agent_input.plan_id,
        case_id=agent_input.case_id,
        case_title=agent_input.case_title,
        run_dir=agent_input.run_dir,
        structured_evidence=dict(agent_input.structured_evidence),
        evidence_bundle=KnowledgeAgentEvidenceBundle(
            judge_result=evidence.judge_result,
            judge_result_path=evidence.judge_result_path,
            artifacts=artifact_refs,
        ),
    )
