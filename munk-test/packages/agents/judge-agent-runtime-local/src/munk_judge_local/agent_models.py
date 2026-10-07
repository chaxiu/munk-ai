from __future__ import annotations

from typing import Literal

from munk.judging.models import JudgeVerdict
from pydantic import BaseModel, Field, field_validator, model_validator


def empty_strings() -> list[str]:
    return []


def empty_guidance_fields() -> list[GuidanceFieldName]:
    return []


GUIDANCE_FIELD_NAMES = (
    "objective_clarifications",
    "preflight_checks",
    "interaction_hints",
    "disambiguation_rules",
    "recovery_hints",
    "judge_hints",
)
GuidanceFieldName = Literal[
    "objective_clarifications",
    "preflight_checks",
    "interaction_hints",
    "disambiguation_rules",
    "recovery_hints",
    "judge_hints",
]


class JudgeAgentOutput(BaseModel):
    verdict: JudgeVerdict
    summary: str
    reason: str
    failure_hypothesis: str | None = None
    confidence: float | None = None
    missing_evidence: list[str] = Field(default_factory=empty_strings)
    supporting_evidence_ids: list[str] = Field(default_factory=empty_strings)
    needs_optimization: bool = False
    optimization_fields: list[GuidanceFieldName] = Field(default_factory=empty_guidance_fields)
    optimization_reason: str | None = None
    optimization_confidence: float | None = None

    @field_validator("summary", "reason")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not 0 <= value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("optimization_confidence")
    @classmethod
    def validate_optimization_confidence(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not 0 <= value <= 1:
            raise ValueError("optimization_confidence must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def validate_failure_hypothesis_for_non_pass(self) -> "JudgeAgentOutput":
        if self.verdict == "passed":
            return self._validate_optimization_fields()
        failure_hypothesis = (self.failure_hypothesis or "").strip()
        if not failure_hypothesis:
            raise ValueError("failure_hypothesis must not be empty for failed or inconclusive verdicts")
        return self._validate_optimization_fields()

    def _validate_optimization_fields(self) -> "JudgeAgentOutput":
        if not self.needs_optimization:
            return self
        if not self.optimization_fields:
            raise ValueError("optimization_fields must not be empty when needs_optimization is true")
        reason = (self.optimization_reason or "").strip()
        if not reason:
            raise ValueError("optimization_reason must not be empty when needs_optimization is true")
        return self
