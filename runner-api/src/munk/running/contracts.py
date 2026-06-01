from __future__ import annotations

from munk.testing import TestCase


def build_case_brief(case: TestCase) -> str:
    validate_case_for_runner(case)
    lines = [
        f"Case Title: {case.title}",
        f"Intent: {case.intent}",
        "Preconditions:",
        *_bullet_lines(case.preconditions),
        "Procedure:",
        *_bullet_lines(case.procedure),
        "Expected Result:",
        *_bullet_lines(case.expected),
    ]
    if case.runner_goal.strip():
        lines.extend(["Execution Hint:", f"- {case.runner_goal.strip()}"])
    return "\n".join(lines)


def validate_case_for_runner(case: TestCase) -> None:
    if not case.title.strip():
        raise ValueError("case title must not be empty")
    if not case.intent.strip():
        raise ValueError("case intent must not be empty")
    if not case.runner_goal.strip():
        raise ValueError("case runner_goal must not be empty")


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
