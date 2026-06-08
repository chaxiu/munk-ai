from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeAlias

from munk.agent_base.base import ActionHistoryEntry, ScreenState
from munk.agent_base.llm import coerce_json_container_string
from munk.agent_base.locator import ElementLocator
from munk.shared_tools import KnowledgeToolProvider
from pydantic import BaseModel, Field, field_validator

from munk.services.events import RunEventSink, utc_now_iso
from munk_runner_local.brain.context_prep_models import ContextPrepKnowledgeItem
from munk_runner_local.brain.memory_store import RunnerMemoryStore

JsonScalar: TypeAlias = str | int | float | bool | None
JsonLeaf: TypeAlias = JsonScalar | list[JsonScalar] | dict[str, JsonScalar]
JsonLikeValue: TypeAlias = JsonLeaf | list[JsonLeaf] | dict[str, JsonLeaf]


@dataclass
class RunnerStepDeps:
    screen: ScreenState
    case_brief: str
    history_entries: list[ActionHistoryEntry]
    max_elements: int
    run_dir: Path
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


class ElementLocatorArgs(BaseModel):
    text_contains: str | None = None
    resource_id_contains: str | None = None
    content_desc_contains: str | None = None
    class_name: str | None = None
    package: str | None = None

    def to_locator(self) -> ElementLocator:
        return ElementLocator(
            text_contains=self.text_contains,
            resource_id_contains=self.resource_id_contains,
            content_desc_contains=self.content_desc_contains,
            class_name=self.class_name,
            package=self.package,
        )


class ClearAndInputToolArgs(BaseModel):
    target_id: int
    text: str
    summary: str
    dismiss_keyboard: bool = True

    @field_validator("text", "summary")
    @classmethod
    def validate_clear_and_input_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned


class DismissSoftKeyboardToolArgs(BaseModel):
    summary: str

    @field_validator("summary")
    @classmethod
    def validate_dismiss_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned


class WaitForElementToolArgs(BaseModel):
    locator: ElementLocatorArgs
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
    def validate_wait_for_element_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be empty")
        return cleaned


class WaitUntilGoneToolArgs(WaitForElementToolArgs):
    pass


class ScrollUntilVisibleToolArgs(BaseModel):
    locator: ElementLocatorArgs
    direction: str = "down"
    max_attempts: int = 5
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
    source: str = "all"

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"all", "vision", "tree"}:
            raise ValueError("source must be one of: all, vision, tree")
        return cleaned


class SaveMemoryToolArgs(BaseModel):
    key: str
    value: JsonLikeValue = Field(
        description="Structured JSON value for later reuse. Arrays/objects must be passed as JSON containers, not quoted strings."
    )
    summary: str

    @field_validator("key", "summary")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("value", mode="before")
    @classmethod
    def coerce_container_string(cls, value: Any) -> Any:
        return coerce_json_container_string(value)

    @field_validator("value")
    @classmethod
    def validate_json_value(cls, value: JsonLikeValue) -> JsonLikeValue:
        json.dumps(value, ensure_ascii=False)
        return value


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
