from __future__ import annotations

from munk.testing import CaseBudget, CaseStartState
from munk.testing import TestCase as SharedTestCase


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
