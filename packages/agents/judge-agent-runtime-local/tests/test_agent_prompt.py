from __future__ import annotations

from munk.judging.models import JudgeExecutionSummary, JudgeScreenDiffEvidence, JudgeScreenDiffEvidencePayload
from munk.testing import AiGuidance
from munk_judge_local.agent import SYSTEM_PROMPT, PydanticAiJudgeAgent
from munk_judge_local.evidence_builder import MAX_PRIMARY_EVIDENCE
from munk_judge_local.models import JudgeEvidencePack


def test_build_prompt_renders_multiline_runner_goal_block() -> None:
    prompt = PydanticAiJudgeAgent._build_prompt(
        JudgeEvidencePack(
            plan_id="plan-1",
            case_id="case-1",
            case_title="Save profile",
            intent="Verify saving profile works",
            expected=["Success toast appears"],
            runner_goal=(
                "Save the profile successfully\n\n"
                "Retry Context:\n"
                "- This is retry attempt 1 for the same test case.\n"
                "- Previous judge assessment: success toast was not observed."
            ),
            execution=JudgeExecutionSummary(status="completed", steps_completed=3),
        )
    )

    assert "Runner Goal:" in prompt
    assert "Save the profile successfully" in prompt
    assert "Retry Context:" in prompt
    assert "- This is retry attempt 1 for the same test case." in prompt


def test_build_prompt_renders_judge_ai_guidance() -> None:
    prompt = PydanticAiJudgeAgent._build_prompt(
        JudgeEvidencePack(
            plan_id="plan-1",
            case_id="case-1",
            case_title="Save profile",
            intent="Verify saving profile works",
            expected=["Success toast appears"],
            runner_goal="Save the profile successfully",
            ai_guidance=AiGuidance(
                objective_clarifications=["Success requires the toast and the updated profile header"],
                judge_hints=["Do not fail only because the toast fades quickly"],
            ),
            execution=JudgeExecutionSummary(status="completed", steps_completed=3),
        )
    )

    assert "[AI_GUIDANCE]" in prompt
    assert "Objective Clarifications:" in prompt
    assert "Judge Hints:" in prompt


def test_system_prompt_is_short_and_keeps_core_judge_contract() -> None:
    assert "You are a judge agent for mobile UI automation test cases." in SYSTEM_PROMPT
    assert "Prefer inconclusive over pass when the evidence is incomplete or ambiguous." in SYSTEM_PROMPT
    assert "Treat explicit execution failures as failure if they are present in the evidence pack." in SYSTEM_PROMPT
    assert (
        "A completed runner stop does not automatically mean the case passed, and an incomplete run does not automatically mean inconclusive."
        in SYSTEM_PROMPT
    )
    assert "Use PRIMARY_EVIDENCE first. Read tools are fallback only when those primary excerpts are still insufficient." in SYSTEM_PROMPT
    assert "Return only the structured output." in SYSTEM_PROMPT
    assert "For passed verdicts, omit failure_hypothesis unless a useful residual risk must be noted." not in SYSTEM_PROMPT
    assert "Explain the verdict briefly and cite the most relevant evidence ids." not in SYSTEM_PROMPT


def test_build_prompt_omits_rules_and_tool_policy_blocks() -> None:
    prompt = PydanticAiJudgeAgent._build_prompt(
        JudgeEvidencePack(
            plan_id="plan-1",
            case_id="case-1",
            case_title="Save profile",
            intent="Verify saving profile works",
            expected=["Success toast appears"],
            runner_goal="Save the profile successfully",
            execution=JudgeExecutionSummary(status="completed", steps_completed=3),
        )
    )

    assert "[RULES]" not in prompt
    assert "[TOOL_POLICY]" not in prompt
    assert "[OBJECTIVE]" in prompt
    assert "[PRIMARY_EVIDENCE]" in prompt
    assert "[SUPPORTING_EVIDENCE]" in prompt


def test_build_prompt_renders_runner_issue_summary_without_raw_artifact_details() -> None:
    prompt = PydanticAiJudgeAgent._build_prompt(
        JudgeEvidencePack(
            plan_id="plan-1",
            case_id="case-1",
            case_title="Save profile",
            intent="Verify saving profile works",
            expected=["Success toast appears"],
            runner_goal="Save the profile successfully",
            execution=JudgeExecutionSummary(status="completed", steps_completed=3),
            runner_issue_summary=[
                {
                    "step_index": 2,
                    "severity": "warning",
                    "summary": "image did not load on the current page",
                    "path": "/tmp/run/runner_issues.json",
                }
            ],
        )
    )

    assert "[RUNNER_ISSUES]" in prompt
    assert "- step=2 severity=warning summary=image did not load on the current page" in prompt
    assert "/tmp/run/runner_issues.json" not in prompt


def test_build_prompt_renders_up_to_max_primary_evidence_items() -> None:
    primary_evidence = [
        JudgeScreenDiffEvidence(
            evidence_id=f"evidence-{index}",
            kind="screen_diff",
            source="artifact",
            summary=f"primary summary {index}",
            payload=JudgeScreenDiffEvidencePayload(
                path=f"/tmp/screen_diff_{index}.json",
                step_index=index,
                summary=f"primary summary {index}",
            ),
        )
        for index in range(MAX_PRIMARY_EVIDENCE + 1)
    ]
    prompt = PydanticAiJudgeAgent._build_prompt(
        JudgeEvidencePack(
            plan_id="plan-1",
            case_id="case-1",
            case_title="Save profile",
            intent="Verify saving profile works",
            expected=["Success toast appears"],
            runner_goal="Save the profile successfully",
            execution=JudgeExecutionSummary(status="completed", steps_completed=3),
            primary_evidence=primary_evidence,
        )
    )

    for index in range(MAX_PRIMARY_EVIDENCE):
        assert f"evidence-{index} [screen_diff/artifact] primary summary {index}" in prompt
    assert f"evidence-{MAX_PRIMARY_EVIDENCE}" not in prompt
