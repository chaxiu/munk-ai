from __future__ import annotations

from pathlib import Path

from munk.post_run_analysis import PostRunAnalysisAgentInput


def test_post_run_analysis_agent_input_serializes_stable_fields() -> None:
    agent_input = PostRunAnalysisAgentInput(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="Login flow",
        run_dir=Path("/tmp/run"),
        execution_summary={"verdict": "failed"},
        judge_summary={"reason": "button unresponsive"},
        artifacts={"result": "/tmp/run/result.json"},
        structured_evidence={"attempts": [{"attempt_index": 0}]},
        source_attempt_index=0,
        requirements={"output_kind": "knowledge_candidate_submissions"},
    )

    payload = agent_input.model_dump(mode="json")

    assert payload["app_id"] == "app-1"
    assert payload["structured_evidence"]["attempts"][0]["attempt_index"] == 0
    assert payload["requirements"]["output_kind"] == "knowledge_candidate_submissions"
