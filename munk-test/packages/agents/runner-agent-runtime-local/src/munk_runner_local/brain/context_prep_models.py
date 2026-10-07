from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_non_empty(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


class ContextPrepSelectionItem(BaseModel):
    card_id: str
    reason: str

    @field_validator("card_id", "reason")
    @classmethod
    def validate_required_text(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "value")
        return _validate_non_empty(value, field_name=str(field_name))


class ContextPrepKnowledgeItem(BaseModel):
    card_id: str
    title: str
    card_type: str
    summary_text: str

    @field_validator("card_id", "title", "card_type", "summary_text")
    @classmethod
    def validate_required_fields(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "value")
        return _validate_non_empty(value, field_name=str(field_name))


class ContextPrepBundleToolArgs(BaseModel):
    card_ids: list[str] = Field(min_length=1, max_length=3)

    @field_validator("card_ids")
    @classmethod
    def validate_card_ids(cls, value: list[str]) -> list[str]:
        cleaned = [_validate_non_empty(item, field_name="card_ids[]") for item in value]
        unique = list(dict.fromkeys(cleaned))
        if len(unique) != len(cleaned):
            raise ValueError("card_ids must not contain duplicates")
        return unique


class ContextPrepBundleToolResult(BaseModel):
    items: list[ContextPrepKnowledgeItem] = Field(default_factory=list)
    missing_card_ids: list[str] = Field(default_factory=list)

    @field_validator("missing_card_ids")
    @classmethod
    def validate_missing_card_ids(cls, value: list[str]) -> list[str]:
        cleaned = [_validate_non_empty(item, field_name="missing_card_ids[]") for item in value]
        unique = list(dict.fromkeys(cleaned))
        if len(unique) != len(cleaned):
            raise ValueError("missing_card_ids must not contain duplicates")
        return unique

    @model_validator(mode="after")
    def validate_disjoint_keys(self) -> ContextPrepBundleToolResult:
        item_keys = {item.card_id for item in self.items}
        overlap = item_keys.intersection(self.missing_card_ids)
        if overlap:
            raise ValueError(f"missing_card_ids must not overlap with items: {sorted(overlap)}")
        return self


class ContextPrepOutput(BaseModel):
    selected_entries: list[ContextPrepSelectionItem] = Field(default_factory=list)
    prep_summary: str
    fallback_reason: str | None = None

    @field_validator("prep_summary")
    @classmethod
    def validate_prep_summary(cls, value: str) -> str:
        return _validate_non_empty(value, field_name="prep_summary")

    @field_validator("fallback_reason")
    @classmethod
    def normalize_fallback_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_consistency(self) -> ContextPrepOutput:
        if len(self.selected_entries) > 3:
            raise ValueError("selected_entries must contain at most 3 items")
        selected_keys = [item.card_id for item in self.selected_entries]
        if len(selected_keys) != len(set(selected_keys)):
            raise ValueError("selected_entries card_ids must be unique")
        if self.fallback_reason is None and not self.selected_entries:
            raise ValueError("selected_entries must not be empty unless fallback_reason is set")
        return self


class ContextPrepFallbackSelectionOutput(BaseModel):
    selected_entries: list[ContextPrepSelectionItem] = Field(default_factory=list)
    prep_summary: str
    fallback_reason: str | None = None

    @field_validator("prep_summary")
    @classmethod
    def validate_prep_summary(cls, value: str) -> str:
        return _validate_non_empty(value, field_name="prep_summary")

    @field_validator("fallback_reason")
    @classmethod
    def normalize_fallback_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_consistency(self) -> ContextPrepFallbackSelectionOutput:
        if len(self.selected_entries) > 3:
            raise ValueError("selected_entries must contain at most 3 items")
        selected_keys = [item.card_id for item in self.selected_entries]
        if len(selected_keys) != len(set(selected_keys)):
            raise ValueError("selected_entries card_ids must be unique")
        if self.fallback_reason is None and not self.selected_entries:
            raise ValueError("selected_entries must not be empty unless fallback_reason is set")
        return self
