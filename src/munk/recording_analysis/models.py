from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError, field_validator

MAX_STAGE_ATTEMPTS = 3
DEFAULT_READ_TOOL_BUDGET = 6
AnalysisProgressCallback = Callable[[str, dict[str, Any]], None]


def empty_strings() -> list[str]:
    return []


def _strip_non_empty(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


def _strip_string_list(values: list[str], *, field_name: str) -> list[str]:
    normalized = [_strip_non_empty(value, field_name=field_name) for value in values]
    return normalized


class AppendProcedureStepSubmission(BaseModel):
    """Structured output for one analyzed recording step."""

    action: str = Field(
        description=(
            "One concise description of the user's direct action in this step. "
            "Describe only the visible action, without pointer coordinates, ack payloads, raw forwarding data, "
            "or hidden implementation details."
        )
    )
    intent: str = Field(
        description=(
            "The most likely user intent for this step inferred from the before and after screens. "
            "Prefer concise, user-facing purpose wording instead of repeating the raw action name."
        )
    )
    state_change: str = Field(
        description=(
            "A concise summary of the visible UI state change caused by this step. "
            "Focus on what changed on screen after the interaction, and do not simply restate the action."
        )
    )
    warnings: list[str] = Field(
        default_factory=empty_strings,
        description=(
            "Optional analysis warnings about ambiguity or weak evidence in this step, such as sparse trees, "
            "missing context, or uncertain intent. Do not use this field for business verdicts."
        ),
    )

    @field_validator("action", "intent", "state_change")
    @classmethod
    def validate_step_field(cls, value: str, info) -> str:  # type: ignore[override]
        cleaned = _strip_non_empty(value, field_name=str(info.field_name))
        if len(cleaned) > 240:
            raise ValueError(f"{info.field_name} must be <= 240 characters")
        return cleaned

    @field_validator("warnings")
    @classmethod
    def validate_warnings(cls, value: list[str]) -> list[str]:
        return _strip_string_list(value, field_name="warnings[]")


class FinalizeCaseSubmission(BaseModel):
    """Structured output for the final canonical test case draft derived from a recording."""

    title: str = Field(
        description=(
            "Short, human-readable test case title suitable for direct display in a UI or test asset list. "
            "Keep it concise and avoid turning it into a long step-by-step sentence."
        )
    )
    intent: str = Field(
        description=(
            "The user goal or business intent this test case is validating. "
            "Describe the purpose of the case, not the procedure and not the expected result."
        )
    )
    expected: list[str] = Field(
        default_factory=empty_strings,
        description=(
            "List of user-observable expected outcomes for the case. "
            "Each item should be a natural-language weak assertion visible from the UI, not internal state, "
            "page metadata, or implementation details."
        ),
    )
    runner_goal: str = Field(
        description=(
            "Single execution-oriented objective for the runner to accomplish for this case. "
            "It should be specific enough to drive one runnable case, but not expanded into full step-by-step procedure."
        )
    )

    @field_validator("title", "intent", "runner_goal")
    @classmethod
    def validate_required_text(cls, value: str, info) -> str:  # type: ignore[override]
        return _strip_non_empty(value, field_name=str(info.field_name))

    @field_validator("expected")
    @classmethod
    def validate_expected(cls, value: list[str]) -> list[str]:
        normalized = _strip_string_list(value, field_name="expected[]")
        if not normalized:
            raise ValueError("expected must not be empty")
        return normalized


@dataclass
class StepStageDeps:
    bundle: dict[str, Any]
    step: dict[str, Any]
    history_procedure: list[str]
    attempt_index: int
    retry_feedback: str | None = None
    tool_budget: int = DEFAULT_READ_TOOL_BUDGET
    tool_calls: list[str] = field(default_factory=list)
    attempt_tool_names: list[str] = field(default_factory=list)
    last_submission_error: str | None = None


class FinalizeStepSummary(BaseModel):
    action: str
    intent: str
    state_change: str
    procedure_step: str


@dataclass
class FinalizeStageDeps:
    bundle: dict[str, Any]
    step_summaries: list[FinalizeStepSummary]
    warnings: list[str]
    attempt_index: int
    retry_feedback: str | None = None
    tool_budget: int = DEFAULT_READ_TOOL_BUDGET
    tool_calls: list[str] = field(default_factory=list)
    attempt_tool_names: list[str] = field(default_factory=list)
    last_submission_error: str | None = None


@dataclass(frozen=True)
class PreparedAnalysisContext:
    recording_id: str
    session: dict[str, Any]
    source_summary: str | None
    steps_payload: list[dict[str, Any]]


@dataclass(frozen=True)
class StepAttemptOutcome:
    submission: AppendProcedureStepSubmission | None
    output_excerpt: str
    last_error: str | None
    tool_names_seen: list[str]


@dataclass(frozen=True)
class FinalizeAttemptOutcome:
    submission: FinalizeCaseSubmission | None
    output_excerpt: str
    last_error: str | None
    tool_names_seen: list[str]


def format_validation_error(prefix: str, exc: ValidationError | ValueError) -> str:
    if isinstance(exc, ValidationError):
        parts: list[str] = []
        for error in exc.errors():
            field_path = ".".join(str(item) for item in error["loc"])
            message = str(error["msg"])
            parts.append(f"{field_path}: {message}")
        details = "; ".join(parts) if parts else str(exc)
        return f"{prefix} rejected: {details}"
    return f"{prefix} rejected: {exc}"
