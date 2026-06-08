from __future__ import annotations

from pathlib import Path
from typing import Literal

from munk.app_knowledge import (
    IssueKnowledgeCandidateDraft,
    IssuePayload,
    KnowledgeCandidateSubmission,
    KnowledgeSource,
)
from munk.judging import JudgeResult
from munk.knowledge_agent.models import (
    KnowledgeAgentEvidenceBundle,
    KnowledgeAgentManagedPaths,
    KnowledgeAgentRequest,
    KnowledgeAgentResult,
    KnowledgeAgentRuntimeContext,
    KnowledgeArtifactRef,
)
from munk_knowledge_agent_local.runtime import LocalKnowledgeAgentRuntimeFactory
from munk_knowledge_agent_local.service import KnowledgeAgentRuntimeService


def _build_judge_result(path: Path, *, verdict: Literal["passed", "failed", "inconclusive"]) -> JudgeResult:
    return JudgeResult(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        verdict=verdict,
        summary="登录失败",
        reason="点击登录后停留在原页面",
        failure_hypothesis="登录接口返回异常",
        confidence=0.82,
        missing_evidence=["缺少接口响应日志"],
        optimization_reason="可以补抓登录接口网络日志",
        judge_request_path=path.parent / "judge_request.json",
        judge_result_path=path,
    )


def test_generate_candidates_skips_passed_case(tmp_path: Path) -> None:
    request = KnowledgeAgentRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="登录流程",
        run_dir=tmp_path / "run",
        evidence_bundle=KnowledgeAgentEvidenceBundle(
            judge_result=_build_judge_result(tmp_path / "judge_result.json", verdict="passed"),
        ),
    )

    result = KnowledgeAgentRuntimeService(
        resolved_config=None,
        agent=_FakeKnowledgeAgent(KnowledgeAgentResult(summary="unused")),
    ).generate_candidates(request, context=_build_context(tmp_path))

    assert result.candidate_submissions == []
    assert result.skip_reason == "verdict_passed"
    assert result.tool_calls == []
    assert result.artifacts["knowledge_agent_tool_calls"].endswith("knowledge_post_action_tool_calls.json")


def test_generate_candidates_builds_issue_submission_with_evidence_bundle(tmp_path: Path) -> None:
    judge_result_path = tmp_path / "judge_result.json"
    decision_trace_path = tmp_path / "decision_trace.jsonl"
    request = KnowledgeAgentRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="登录流程",
        run_dir=tmp_path / "run",
        evidence_bundle=KnowledgeAgentEvidenceBundle(
            judge_result=_build_judge_result(judge_result_path, verdict="failed"),
            judge_result_path=judge_result_path,
            artifacts=[
                KnowledgeArtifactRef(artifact_id="decision_trace", path=decision_trace_path),
                KnowledgeArtifactRef(artifact_id="judge_result", path=judge_result_path),
            ],
        ),
    )

    result = KnowledgeAgentRuntimeService(
        resolved_config=None,
        agent=_FakeKnowledgeAgent(
            KnowledgeAgentResult(
                summary="knowledge agent generated candidate proposals",
                candidate_submissions=[
                    KnowledgeCandidateSubmission(
                        app_id="app-1",
                        candidate=IssueKnowledgeCandidateDraft(
                            app_id="app-1",
                            title="登录流程",
                            confidence=0.82,
                            source=KnowledgeSource(
                                kind="knowledge_agent",
                                note="knowledge agent runtime",
                                ref=str(judge_result_path),
                            ),
                            card_type="issue",
                            payload=IssuePayload(
                                symptoms=[
                                    "登录失败",
                                    "点击登录后停留在原页面",
                                    "缺少接口响应日志",
                                ],
                                trigger_conditions=[
                                    "case_id=case-1",
                                    "plan_id=plan-1",
                                    "verdict=failed",
                                ],
                                workaround="登录接口返回异常",
                                severity="high",
                            ),
                        ),
                        evidence_refs=[str(decision_trace_path), str(judge_result_path)],
                    )
                ],
            ),
            last_tool_calls=["read_judge_result", "read_decision_trace_tail"],
        ),
    ).generate_candidates(request, context=_build_context(tmp_path))

    assert result.skip_reason is None
    assert len(result.candidate_submissions) == 1
    assert result.tool_calls == ["read_judge_result", "read_decision_trace_tail"]
    submission = result.candidate_submissions[0]
    assert submission.app_id == "app-1"
    assert submission.evidence_refs == [str(decision_trace_path), str(judge_result_path)]
    assert submission.candidate.title == "登录流程"
    assert submission.candidate.source.kind == "knowledge_agent"
    assert submission.candidate.source.ref == str(judge_result_path)
    assert submission.candidate.payload.symptoms == [
        "登录失败",
        "点击登录后停留在原页面",
        "缺少接口响应日志",
    ]
    assert submission.candidate.payload.trigger_conditions == [
        "case_id=case-1",
        "plan_id=plan-1",
        "verdict=failed",
    ]
    assert submission.candidate.payload.workaround == "登录接口返回异常"
    assert submission.candidate.payload.severity == "high"


def test_local_runtime_factory_reports_health() -> None:
    health = LocalKnowledgeAgentRuntimeFactory().diagnose()
    assert health.runtime_id == "local"
    assert health.status == "ok"


class _FakeKnowledgeAgent:
    def __init__(
        self,
        result: KnowledgeAgentResult,
        *,
        last_tool_calls: list[str] | None = None,
        last_prompt: str = "knowledge prompt",
    ) -> None:
        self._result = result
        self.last_tool_calls = list(last_tool_calls or [])
        self.last_prompt = last_prompt

    def generate_candidates(self, request: KnowledgeAgentRequest, *, deps) -> KnowledgeAgentResult:  # noqa: ANN001
        del request, deps
        return self._result


def _build_context(tmp_path: Path) -> KnowledgeAgentRuntimeContext:
    root_dir = tmp_path / "knowledge"
    root_dir.mkdir(parents=True, exist_ok=True)
    return KnowledgeAgentRuntimeContext(
        operation_id="op-1",
        managed_paths=KnowledgeAgentManagedPaths(
            root_dir=root_dir,
            prompt_path=root_dir / "knowledge_post_action_prompt.txt",
            tool_calls_path=root_dir / "knowledge_post_action_tool_calls.json",
            llm_transcript_path=root_dir / "knowledge_post_action_llm_transcript.json",
        ),
    )
