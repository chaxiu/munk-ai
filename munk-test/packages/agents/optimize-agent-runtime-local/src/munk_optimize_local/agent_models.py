from __future__ import annotations

from munk.optimizing.models import OptimizeFieldName
from pydantic import BaseModel, Field, field_validator


def empty_strings() -> list[str]:
    return []


class OptimizeFieldPatchOutput(BaseModel):
    field_name: OptimizeFieldName
    replace_with: list[str] = Field(default_factory=empty_strings)
    reason: str | None = None

    @field_validator("replace_with")
    @classmethod
    def validate_items(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class OptimizeAgentOutput(BaseModel):
    summary: str
    patched_fields: list[OptimizeFieldPatchOutput] = Field(default_factory=list)
