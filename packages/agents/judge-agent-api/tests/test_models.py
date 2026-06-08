from __future__ import annotations

import pytest
from munk.judging.models import JudgeExecutionSummary, JudgeRequest


def test_judge_request_normalizes_and_validates_required_fields() -> None:
    request = JudgeRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title=" Case One ",
        intent=" Open settings ",
        expected=[" Settings page is visible "],
        runner_goal=" Open settings page ",
        execution=JudgeExecutionSummary(status="completed"),
    )

    assert request.case_title == "Case One"
    assert request.intent == "Open settings"
    assert request.expected == ["Settings page is visible"]
    assert request.runner_goal == "Open settings page"


def test_judge_request_requires_expected_items() -> None:
    with pytest.raises(ValueError, match="expected must not be empty"):
        JudgeRequest(
            app_id="app-1",
            plan_id="plan-1",
            case_id="case-1",
            case_title="Case One",
            intent="Open settings",
            expected=[],
            runner_goal="Open settings page",
            execution=JudgeExecutionSummary(status="completed"),
        )
