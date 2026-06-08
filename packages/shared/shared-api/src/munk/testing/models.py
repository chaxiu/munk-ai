from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


def empty_strings() -> list[str]:
    return []


def empty_procedure() -> list[str]:
    return []


def empty_post_action() -> list[str]:
    return []


def empty_string_map() -> dict[str, str]:
    return {}


def empty_guidance_items() -> list[str]:
    return []


class CaseBudget(BaseModel):
    max_steps: int | None = Field(default=None, gt=0)
    max_seconds: float | None = Field(default=None, gt=0)


class CaseStartState(BaseModel):
    mode: Literal["reset", "resume"] = "reset"
    page_id: str | None = Field(
        default=None,
        description=(
            "Optional semantic app page identifier. Resolution depends on app-specific "
            "navigation support and is not validated against a central registry."
        ),
    )


class AiGuidance(BaseModel):
    objective_clarifications: list[str] = Field(default_factory=empty_guidance_items)
    preflight_checks: list[str] = Field(default_factory=empty_guidance_items)
    interaction_hints: list[str] = Field(default_factory=empty_guidance_items)
    disambiguation_rules: list[str] = Field(default_factory=empty_guidance_items)
    recovery_hints: list[str] = Field(default_factory=empty_guidance_items)
    judge_hints: list[str] = Field(default_factory=empty_guidance_items)


class TestCase(BaseModel):
    __test__ = False

    case_id: str
    title: str
    intent: str
    preconditions: list[str] = Field(default_factory=empty_strings)
    expected: list[str] = Field(default_factory=empty_strings)
    procedure: list[str] = Field(default_factory=empty_procedure)
    post_action: list[str] = Field(default_factory=empty_post_action)
    is_core_case: bool = False
    runner_goal: str
    budget: CaseBudget | None = None
    start_state: CaseStartState = Field(default_factory=CaseStartState)
    ai_guidance: AiGuidance | None = None
    source_metadata: dict[str, str] = Field(default_factory=empty_string_map)
