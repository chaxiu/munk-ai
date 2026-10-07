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
        lines.extend(["Execution Hint:", *_goal_lines(case.runner_goal)])
    guidance_lines = _runner_guidance_lines(case)
    if guidance_lines:
        lines.extend(["", "AI Guidance:", *guidance_lines])
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


def _goal_lines(goal: str) -> list[str]:
    lines: list[str] = []
    for raw_line in goal.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.endswith(":") or line.startswith("- "):
            lines.append(line)
            continue
        lines.append(f"- {line}")
    return lines or ["- none"]


def _runner_guidance_lines(case: TestCase) -> list[str]:
    guidance = case.ai_guidance
    if guidance is None:
        return []
    sections: list[tuple[str, list[str]]] = [
        ("Preflight Checks", guidance.preflight_checks),
        ("Interaction Hints", guidance.interaction_hints),
        ("Disambiguation Rules", guidance.disambiguation_rules),
        ("Recovery Hints", guidance.recovery_hints),
    ]
    lines: list[str] = []
    for title, items in sections:
        cleaned = [item.strip() for item in items if item.strip()]
        if not cleaned:
            continue
        lines.append(f"{title}:")
        lines.extend(f"- {item}" for item in cleaned)
    return lines
