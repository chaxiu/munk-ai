from __future__ import annotations

from munk.services.errors import InvalidCaseDefinitionError
from munk.testing import TestCase


def validate_case_definition(case: TestCase, *, context: str) -> TestCase:
    issues: list[str] = []

    title = case.title.strip()
    if not title:
        issues.append("title must not be empty")

    intent = case.intent.strip()
    if not intent:
        issues.append("intent must not be empty")

    runner_goal = case.runner_goal.strip()
    if not runner_goal:
        issues.append("runner_goal must not be empty")

    expected = [item.strip() for item in case.expected]
    if any(not item for item in expected):
        issues.append("expected[] must not contain empty items")
    normalized_expected = [item for item in expected if item]
    if not normalized_expected:
        issues.append("expected must not be empty")

    if issues:
        raise InvalidCaseDefinitionError(
            context=context,
            case_id=case.case_id,
            issues=issues,
        )

    return case.model_copy(
        update={
            "title": title,
            "intent": intent,
            "runner_goal": runner_goal,
            "expected": normalized_expected,
        }
    )
