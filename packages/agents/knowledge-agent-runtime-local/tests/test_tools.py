from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast

from munk.judging import JudgeResult
from munk.knowledge_agent import KnowledgeAgentEvidenceBundle, KnowledgeAgentRequest, KnowledgeArtifactRef
from munk_knowledge_agent_local.tool_models import KnowledgeToolDeps
from munk_knowledge_agent_local.tools import register_knowledge_agent_tools


class CapturingAgent:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., object]] = {}

    def tool(self, func: Callable[..., object]) -> Callable[..., object]:
        self.tools[func.__name__] = func
        return func


def _build_judge_result(path: Path) -> JudgeResult:
    return JudgeResult(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        verdict="failed",
        summary="登录失败",
        reason="点击登录后停留在原页面",
        confidence=0.82,
        judge_request_path=path.parent / "judge_request.json",
        judge_result_path=path,
    )


def _build_deps(tmp_path: Path) -> KnowledgeToolDeps:
    attempts_path = tmp_path / "attempts.json"
    history_path = tmp_path / "history.json"
    retry_handoffs_path = tmp_path / "retry_handoffs.json"
    decision_trace_path = tmp_path / "decision_trace.jsonl"
    manifest_path = tmp_path / "artifact_manifest.json"
    judge_result_path = tmp_path / "judge_result.json"
    attempts_path.write_text(
        json.dumps(
            [
                {
                    "attempt_index": 0,
                    "verdict": "failed",
                    "retry_reason": "element_not_found",
                    "judge_reason": "登录按钮无响应",
                    "execution": {"status": "failed", "stop_reason": "timeout", "error_type": "RunnerProtocolError"},
                }
            ]
        ),
        encoding="utf-8",
    )
    history_path.write_text(json.dumps([{"type": "runner_step"}, {"type": "judge_completed"}]), encoding="utf-8")
    retry_handoffs_path.write_text(json.dumps([{"reason": "尝试重新登录"}]), encoding="utf-8")
    decision_trace_path.write_text('{"step": 1, "decision": "retry"}\n{"step": 2, "decision": "stop"}\n', encoding="utf-8")
    manifest_path.write_text(json.dumps({"items": [{"artifact_id": "attempts"}]}), encoding="utf-8")
    judge_result_path.write_text(_build_judge_result(judge_result_path).model_dump_json(indent=2), encoding="utf-8")
    request = KnowledgeAgentRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="登录流程",
        run_dir=tmp_path / "run",
        evidence_bundle=KnowledgeAgentEvidenceBundle(
            judge_result=_build_judge_result(judge_result_path),
            judge_result_path=judge_result_path,
            artifacts=[
                KnowledgeArtifactRef(artifact_id="attempts", path=attempts_path),
                KnowledgeArtifactRef(artifact_id="history", path=history_path),
                KnowledgeArtifactRef(artifact_id="retry_handoffs", path=retry_handoffs_path),
                KnowledgeArtifactRef(artifact_id="decision_trace", path=decision_trace_path),
                KnowledgeArtifactRef(artifact_id="artifact_manifest", path=manifest_path),
            ],
        ),
    )
    return KnowledgeToolDeps(request=request, tool_budget=4)


def _build_tools() -> dict[str, Callable[..., object]]:
    agent = CapturingAgent()
    register_knowledge_agent_tools(cast(Any, agent))
    return agent.tools


def test_read_attempts_overview_returns_compact_payload(tmp_path: Path) -> None:
    deps = _build_deps(tmp_path)
    tools = _build_tools()

    payload = json.loads(cast(Callable[..., str], tools["read_attempts_overview"])(SimpleNamespace(deps=deps)))

    assert payload["attempts"][0]["attempt_index"] == 0
    assert payload["attempts"][0]["retry_reason"] == "element_not_found"
    assert deps.tool_calls == ["read_attempts_overview"]


def test_read_decision_trace_tail_returns_tail_entries(tmp_path: Path) -> None:
    deps = _build_deps(tmp_path)
    tools = _build_tools()

    payload = json.loads(cast(Callable[..., str], tools["read_decision_trace_tail"])(SimpleNamespace(deps=deps), last_n=1))

    assert payload["entries"] == [{"step": 2, "decision": "stop"}]


def test_tool_budget_exhaustion_returns_stable_message(tmp_path: Path) -> None:
    deps = _build_deps(tmp_path)
    deps.tool_budget = 1
    tools = _build_tools()
    read_judge_result = cast(Callable[..., str], tools["read_judge_result"])
    read_retry_handoffs = cast(Callable[..., str], tools["read_retry_handoffs"])

    first = read_judge_result(SimpleNamespace(deps=deps))
    second = read_retry_handoffs(SimpleNamespace(deps=deps))

    assert "登录失败" in first
    assert second == "tool budget exhausted; make the best knowledge candidate judgment from the current context"
