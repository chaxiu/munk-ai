from __future__ import annotations

from munk.judging.models import JudgeExecutionSummary
from munk.testing import AiGuidance
from munk_judge_local.agent import PydanticAiJudgeAgent
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
