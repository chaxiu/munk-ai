from __future__ import annotations

from munk.running.contracts import build_case_brief
from munk.testing import AiGuidance, TestCase


def test_build_case_brief_renders_runner_ai_guidance() -> None:
    case = TestCase(
        case_id="case-1",
        title="Open settings",
        intent="Open settings page",
        runner_goal="Open settings reliably",
        ai_guidance=AiGuidance(
            preflight_checks=["User is logged in"],
            interaction_hints=["Prefer the profile tab first"],
            disambiguation_rules=["Do not confuse account settings with app settings"],
            recovery_hints=["If a popup blocks the screen, dismiss it first"],
        ),
    )

    brief = build_case_brief(case)

    assert "AI Guidance:" in brief
    assert "Preflight Checks:" in brief
    assert "- User is logged in" in brief
    assert "Interaction Hints:" in brief
    assert "Recovery Hints:" in brief
