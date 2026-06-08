from __future__ import annotations

from munk.shared_tools.ai_guidance import FIELD_DESCRIPTIONS


def test_ai_guidance_field_descriptions_cover_expected_fields() -> None:
    assert "objective_clarifications" in FIELD_DESCRIPTIONS
    assert "judge_hints" in FIELD_DESCRIPTIONS
