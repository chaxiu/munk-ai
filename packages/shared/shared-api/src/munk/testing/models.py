from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, Field

JsonValue: TypeAlias = Any


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


class HttpSetupStep(BaseModel):
    kind: Literal["http"] = "http"
    base: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    path: str = "/"
    headers: dict[str, str] = Field(default_factory=dict)
    query: dict[str, str] = Field(default_factory=dict)
    body: JsonValue | None = None
    expected_status: list[int] = Field(default_factory=lambda: [200])


class CommandSetupStep(BaseModel):
    kind: Literal["command"] = "command"
    exec: str
    args: list[str] = Field(default_factory=list)
    expected_exit_code: int = 0


SetupStep = Annotated[HttpSetupStep | CommandSetupStep, Field(discriminator="kind")]


def empty_setup() -> list[SetupStep]:
    return []


class TestCase(BaseModel):
    __test__ = False

    case_id: str
    title: str
    intent: str
    preconditions: list[str] = Field(default_factory=empty_strings)
    expected: list[str] = Field(default_factory=empty_strings)
    procedure: list[str] = Field(default_factory=empty_procedure)
    post_action: list[str] = Field(default_factory=empty_post_action)
    setup: list[SetupStep] = Field(default_factory=empty_setup)
    is_core_case: bool = False
    runner_goal: str
    acceptance_criteria_indices: list[int] = Field(default_factory=empty_strings)
    budget: CaseBudget | None = None
    start_state: CaseStartState = Field(default_factory=CaseStartState)
    ai_guidance: AiGuidance | None = None
    source_metadata: dict[str, str] = Field(default_factory=empty_string_map)
