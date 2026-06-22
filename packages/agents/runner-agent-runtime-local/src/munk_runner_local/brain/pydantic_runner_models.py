from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from munk.agent_base.base import ActionHistoryEntry, ScreenState
from munk.shared_tools import KnowledgeToolProvider
from pydantic import BaseModel, Field, field_validator, model_validator

from munk.services.events import RunEventSink, utc_now_iso
from munk_runner_local.brain.context_prep_models import ContextPrepKnowledgeItem
from munk_runner_local.brain.memory_store import RunnerMemoryStore

@dataclass
class RunnerStepDeps:
    screen: ScreenState
    case_brief: str
    history_entries: list[ActionHistoryEntry]
    max_elements: int
    run_dir: Path
    raw_dir: Path
    annotated_dir: Path
    vl_max_side: int
    vl_image_format: str = "webp"
    vl_fallback_image_format: str = "jpeg"
    vl_webp_quality: int = 80
    vl_jpeg_quality: int = 82
    app_id: str = "unknown"
    knowledge_tools: KnowledgeToolProvider | None = None
    prepared_context_text: str = "none"
    prepared_knowledge_bundle: tuple[ContextPrepKnowledgeItem, ...] = ()
    prepared_selected_card_ids: tuple[str, ...] = ()
    context_prep_fallback_reason: str | None = None
    memory_store: RunnerMemoryStore = field(default_factory=RunnerMemoryStore)
    event_sink: RunEventSink | None = None
    trace_path: Path | None = None
    runner_memory_path: Path | None = None
    runner_issues_path: Path | None = None
    step_index: int | None = None
    target_part_limit_override: int | None = None
    seed_context_recorded: bool = False
    attempt_index: int = 0
    attempt_tool_names: list[str] = field(default_factory=list)


class ClickToolArgs(BaseModel):
    target_id: int
    summary: str

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned


class InputToolArgs(BaseModel):
    text: str
    summary: str
    dismiss_keyboard: bool = False

    @field_validator("text", "summary")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned


class ScrollToolArgs(BaseModel):
    start: tuple[int, int]
    end: tuple[int, int]
    duration: float | None = None
    summary: str

    @field_validator("summary")
    @classmethod
    def validate_scroll_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned

    @field_validator("duration")
    @classmethod
    def validate_scroll_duration(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("duration must be finite")
        if value < 0:
            raise ValueError("duration must be non-negative")
        return value


class TextMatchArgs(BaseModel):
    match_type: Literal["any_of_texts", "all_texts", "none_of_texts"]
    texts: list[str] = Field(
        description="Visible stable texts to match against the whole-screen OCR-style text snapshot.",
    )

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("texts must contain at least one non-empty string")
        return cleaned


class EditTextToolArgs(BaseModel):
    mode: Literal["append", "replace"]
    target_id: int | None = None
    text: str
    summary: str
    dismiss_keyboard: bool | None = None

    @field_validator("text", "summary")
    @classmethod
    def validate_edit_text_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_shape(self) -> "EditTextToolArgs":
        if self.mode == "replace":
            if self.target_id is None:
                raise ValueError("target_id is required for replace mode")
            if self.dismiss_keyboard is None:
                self.dismiss_keyboard = True
            return self
        if self.dismiss_keyboard is None:
            self.dismiss_keyboard = False
        return self


class DismissSoftKeyboardToolArgs(BaseModel):
    summary: str

    @field_validator("summary")
    @classmethod
    def validate_dismiss_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned


class WaitForTextToolArgs(BaseModel):
    match: TextMatchArgs
    timeout_sec: float
    summary: str

    @field_validator("timeout_sec")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("timeout_sec must be finite")
        if value < 0:
            raise ValueError("timeout_sec must be non-negative")
        return value

    @field_validator("summary")
    @classmethod
    def validate_wait_for_text_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned


class ScrollUntilTextToolArgs(BaseModel):
    match: TextMatchArgs
    direction: str = "down"
    max_attempts: int = 8
    summary: str

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"down", "up"}:
            raise ValueError("direction must be 'down' or 'up'")
        return cleaned

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_attempts must be positive")
        return value

    @field_validator("summary")
    @classmethod
    def validate_scroll_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned


class WaitToolArgs(BaseModel):
    duration: float
    summary: str

    @field_validator("duration")
    @classmethod
    def validate_wait_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("duration must be finite")
        if value < 0:
            raise ValueError("duration must be non-negative")
        return value

    @field_validator("summary")
    @classmethod
    def validate_wait_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned

class RunnerToolTraceEntry(BaseModel):
    step_index: int | None = None
    tool_name: str
    arguments: dict[str, Any]
    result_summary: str
    timestamp: str = Field(default_factory=utc_now_iso)


class ListClickableElementsToolArgs(BaseModel):
    max: int | None = None
    source: Literal["vision", "tree", "all"] = "all"

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"all", "vision", "tree"}:
            raise ValueError("source must be one of: all, vision, tree")
        return cleaned


class SaveMemoryToolArgs(BaseModel):
    key: str
    value: str = Field(description="Reusable fact string for later steps. Keep it concise and directly reusable.")
    summary: str

    @field_validator("key", "value", "summary")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned


class ReportIssueToolArgs(BaseModel):
    severity: Literal["warning", "error"]
    summary: str

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned


class RunnerIssueRecord(BaseModel):
    step_index: int | None = None
    severity: Literal["warning", "error"]
    summary: str
    timestamp: str = Field(default_factory=utc_now_iso)


class ReadMemoryToolArgs(BaseModel):
    key: str | None = None

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("key must not be empty")
        return cleaned
