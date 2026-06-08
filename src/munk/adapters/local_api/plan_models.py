from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from munk.testing import CaseBudget, CaseStartState, TestCase

_EDITABLE_CASE_FIELDS = (
    "intent",
    "runner_goal",
    "start_mode",
    "start_page_id",
    "preconditions",
    "expected",
    "procedure",
    "post_action",
)


def _clean_required_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_text_list(value: list[str] | None, *, field_name: str) -> list[str] | None:
    if value is None:
        return None
    cleaned_items: list[str] = []
    for item in value:
        cleaned = item.strip()
        if not cleaned:
            continue
        cleaned_items.append(cleaned)
    if len(cleaned_items) != len(value):
        raise ValueError(f"{field_name} must not contain empty items")
    return cleaned_items


class CaseUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str | None = None
    runner_goal: str | None = None
    start_mode: Literal["reset", "resume"] | None = None
    start_page_id: str | None = None
    preconditions: list[str] | None = None
    expected: list[str] | None = None
    procedure: list[str] | None = None
    post_action: list[str] | None = None

    @field_validator("intent", "runner_goal")
    @classmethod
    def _validate_required_text(cls, value: str | None, info) -> str | None:  # type: ignore[no-untyped-def]
        return _clean_required_text(value, field_name=info.field_name)

    @field_validator("start_page_id")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("preconditions", "expected", "procedure", "post_action")
    @classmethod
    def _validate_text_list(cls, value: list[str] | None, info) -> list[str] | None:  # type: ignore[no-untyped-def]
        return _clean_text_list(value, field_name=info.field_name)

    def provided_fields(self) -> list[str]:
        return [field for field in _EDITABLE_CASE_FIELDS if field in self.model_fields_set]

    def require_single_field(self) -> tuple[str, str | list[str] | None]:
        provided_fields = self.provided_fields()
        if len(provided_fields) != 1:
            raise ValueError("exactly one editable field must be provided")
        field_name = provided_fields[0]
        value = getattr(self, field_name)
        if field_name != "start_page_id" and value is None:
            raise ValueError(f"{field_name} must not be null")
        return field_name, value


class CaseBudgetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_steps: int | None = Field(default=None, gt=0)
    max_seconds: float | None = Field(default=None, gt=0)

    def to_case_budget(self) -> CaseBudget:
        return CaseBudget(max_steps=self.max_steps, max_seconds=self.max_seconds)


class CaseStartStateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["reset", "resume"] = "reset"
    page_id: str | None = None

    @field_validator("page_id")
    @classmethod
    def _validate_page_id(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    def to_case_start_state(self) -> CaseStartState:
        return CaseStartState(mode=self.mode, page_id=self.page_id)


class TestCasePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    intent: str
    preconditions: list[str] = Field(default_factory=list)
    expected: list[str] = Field(default_factory=list)
    procedure: list[str] = Field(default_factory=list)
    post_action: list[str] = Field(default_factory=list)
    is_core_case: bool = False
    runner_goal: str
    budget: CaseBudgetRequest | None = None
    start_state: CaseStartStateRequest = Field(default_factory=CaseStartStateRequest)
    source_metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("case_id", "title", "intent", "runner_goal")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info) -> str:  # type: ignore[no-untyped-def]
        cleaned = _clean_required_text(value, field_name=info.field_name)
        if cleaned is None:
            raise ValueError(f"{info.field_name} must not be null")
        return cleaned

    @field_validator("preconditions", "expected", "procedure", "post_action")
    @classmethod
    def _validate_text_lists(cls, value: list[str], info) -> list[str]:  # type: ignore[no-untyped-def]
        cleaned = _clean_text_list(value, field_name=info.field_name)
        return cleaned or []

    @field_validator("source_metadata")
    @classmethod
    def _validate_source_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, item in value.items():
            cleaned_key = key.strip()
            cleaned_value = item.strip()
            if not cleaned_key:
                raise ValueError("source_metadata keys must not be empty")
            if not cleaned_value:
                raise ValueError(f"source_metadata['{cleaned_key}'] must not be empty")
            cleaned[cleaned_key] = cleaned_value
        return cleaned

    def to_test_case(self) -> TestCase:
        return TestCase(
            case_id=self.case_id,
            title=self.title,
            intent=self.intent,
            preconditions=list(self.preconditions),
            expected=list(self.expected),
            procedure=list(self.procedure),
            post_action=list(self.post_action),
            is_core_case=self.is_core_case,
            runner_goal=self.runner_goal,
            budget=None if self.budget is None else self.budget.to_case_budget(),
            start_state=self.start_state.to_case_start_state(),
            source_metadata=dict(self.source_metadata),
        )


class CaseUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case: TestCasePayload

    def to_test_case(self) -> TestCase:
        return self.case.to_test_case()


class CaseRewritePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str

    @field_validator("prompt")
    @classmethod
    def _validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("prompt must not be empty")
        return cleaned


class PlanCaseReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_ids: list[str] = Field(min_length=1)

    @field_validator("case_ids")
    @classmethod
    def _validate_case_ids(cls, value: list[str]) -> list[str]:
        cleaned = _clean_text_list(value, field_name="case_ids")
        if cleaned is None or not cleaned:
            raise ValueError("case_ids must not be empty")
        return cleaned


class PlanImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    name: str
    file_name: str | None = None
    raw_plan: dict[str, Any]

    @field_validator("app_id", "name")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info) -> str:  # type: ignore[no-untyped-def]
        cleaned = _clean_required_text(value, field_name=info.field_name)
        if cleaned is None:
            raise ValueError(f"{info.field_name} must not be null")
        return cleaned

    @field_validator("file_name")
    @classmethod
    def _validate_file_name(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("raw_plan")
    @classmethod
    def _validate_raw_plan(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("raw_plan must be an object")
        return value
