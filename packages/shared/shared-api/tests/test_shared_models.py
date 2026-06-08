from __future__ import annotations

from munk.testing import AiGuidance, CaseBudget, CaseStartState
from munk.testing import TestCase as SharedTestCase

from munk.orchestration import (
    AgentDecision,
    CaseWorkflowState,
    OrchestrationPolicy,
    StateDelta,
    StepRequest,
    StepResult,
)


def test_testcase_defaults_match_main_repo_expectations() -> None:
    case = SharedTestCase(
        case_id="case-1",
        title="Title",
        intent="Intent",
        runner_goal="Runner goal",
    )

    assert case.preconditions == []
    assert case.expected == []
    assert case.procedure == []
    assert case.is_core_case is False
    assert case.start_state == CaseStartState()


def test_testcase_round_trip_includes_budget_and_start_state() -> None:
    case = SharedTestCase(
        case_id="case-1",
        title="Title",
        intent="Intent",
        runner_goal="Runner goal",
        budget=CaseBudget(max_steps=8, max_seconds=80),
        start_state=CaseStartState(page_id="settings"),
    )

    dumped = case.model_dump()

    assert dumped["budget"] == {"max_steps": 8, "max_seconds": 80.0}
    assert dumped["start_state"] == {"mode": "reset", "page_id": "settings"}


def test_testcase_round_trip_includes_ai_guidance() -> None:
    case = SharedTestCase(
        case_id="case-1",
        title="Title",
        intent="Intent",
        runner_goal="Runner goal",
        ai_guidance=AiGuidance(
            preflight_checks=["User is logged in"],
            judge_hints=["Do not treat loading spinner as failure"],
        ),
    )

    dumped = case.model_dump()

    assert dumped["ai_guidance"] == {
        "objective_clarifications": [],
        "preflight_checks": ["User is logged in"],
        "interaction_hints": [],
        "disambiguation_rules": [],
        "recovery_hints": [],
        "judge_hints": ["Do not treat loading spinner as failure"],
    }


def test_orchestration_models_capture_case_state_and_decision() -> None:
    case = SharedTestCase(
        case_id="case-1",
        title="Title",
        intent="Intent",
        runner_goal="Runner goal",
        expected=["Expected"],
    )
    state = CaseWorkflowState(
        app_id="app-1",
        plan_id="plan-1",
        case=case,
        status="running",
        current_step="runner",
        retry_count=1,
        supplemental_context=["retry because submit button stayed disabled"],
    )
    request = StepRequest(
        app_id="app-1",
        plan_id="plan-1",
        case=case,
        state=state,
        step="judge",
    )
    result = StepResult(
        step="judge",
        state_delta=StateDelta(
            status="needs_retry",
            next_step="runner",
            retry_count_increment=1,
            supplemental_context=["collect more confirmation after save"],
        ),
        decision=AgentDecision(
            decision_type="retry_with_context",
            target_step="runner",
            reason="missing confirmation after save",
            supplemental_context=["wait for success toast before stopping"],
        ),
        artifacts={"judge_result": "/tmp/judge_result.json"},
    )

    assert request.state.current_step == "runner"
    assert result.state_delta.next_step == "runner"
    assert result.decision.decision_type == "retry_with_context"
    assert result.artifacts["judge_result"].endswith("judge_result.json")


def test_orchestration_policy_defaults_match_engine_expectations() -> None:
    policy = OrchestrationPolicy()

    assert policy.max_retry_attempts == 0
    assert policy.retry_on_inconclusive is True
    assert policy.retry_on_failed is True
    assert policy.terminal_decisions == ["finish", "escalate"]
