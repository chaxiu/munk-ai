from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OptimizeTimelineEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    lifecycle_state: str | None = None
    agent_role: str | None = None
    event_timestamp: str | None = None
    timestamp: str | None = None
    request_path: str | None = None
    attempt_count: int | None = None
    step_summary_count: int | None = None
    step_screen_count: int | None = None
    step_transition_count: int | None = None
    tool_call_count: int | None = None
    tool_calls: list[str] | None = None
    tool_name: str | None = None
    tool_index: int | None = None
    patched_field_count: int | None = None
    skipped_field_count: int | None = None
    patched_fields: list[str] | None = None
    patched_field_summaries: list[str] | None = None
    applied: bool | None = None
    skip_reason: str | None = None
    error_type: str | None = None
