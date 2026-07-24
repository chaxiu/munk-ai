from __future__ import annotations

import json
from pathlib import Path

from munk.judging import JudgeResult
from munk.knowledge_agent import KnowledgeAgentEvidenceBundle, KnowledgeAgentRequest, KnowledgeArtifactRef
from munk_knowledge_agent_local.prompt import build_knowledge_agent_prompt_payload


def test_knowledge_prompt_uses_evidence_seed_instead_of_full_dump(tmp_path: Path) -> None:
    judge_path = tmp_path / "judge_result.json"
    request = KnowledgeAgentRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="Login",
        run_dir=tmp_path,
        evidence_bundle=KnowledgeAgentEvidenceBundle(
            judge_result=JudgeResult(
                app_id="app-1",
                plan_id="plan-1",
                case_id="case-1",
                verdict="failed",
                summary="login failed",
                reason="button stuck",
                judge_request_path=tmp_path / "judge_request.json",
                judge_result_path=judge_path,
            ),
            artifacts=[
                KnowledgeArtifactRef(artifact_id="attempts", path=tmp_path / "attempts.json"),
            ],
        ),
        structured_evidence={
            "attempts": [
                {
                    "attempt_index": 0,
                    "verdict": "failed",
                    "execution": {"status": "failed", "error_type": "TimeoutError"},
                    "huge": "x" * 5000,
                }
            ],
            "history": [{"event_type": f"e-{index}"} for index in range(20)],
            "decision_trace": [{"step": index, "arguments": {"raw": "y" * 200}} for index in range(30)],
            "judge_result": {
                "verdict": "failed",
                "summary": "login failed",
                "reason": "button stuck",
                "needs_optimization": False,
            },
        },
    )

    payload = json.loads(build_knowledge_agent_prompt_payload(request))

    assert "structured_evidence" not in payload
    assert "judge_result_summary" not in payload
    assert payload["evidence_seed"]["judge_result"]["verdict"] == "failed"
    assert payload["evidence_seed"]["attempts_overview"][0]["error_type"] == "TimeoutError"
    assert "huge" not in json.dumps(payload["evidence_seed"]["attempts_overview"])
    assert payload["requirements"]["use_read_tools_for_detail"] is True
