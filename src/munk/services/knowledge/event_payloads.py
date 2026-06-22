from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KnowledgeTimelineEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    lifecycle_state: str | None = None
    agent_role: str | None = None
    event_timestamp: str | None = None
    timestamp: str | None = None
    artifact_count: int | None = None
    prompt_path: str | None = None
    tool_call_count: int | None = None
    tool_calls: list[str] | None = None
    tool_name: str | None = None
    tool_index: int | None = None
    generated_candidate_count: int | None = None
    candidate_id: str | None = None
    candidate_count: int | None = None
    candidate_title: str | None = None
    card_type: str | None = None
    judge_verdict: str | None = None
    submitted: bool | None = None
    skip_reason: str | None = None
    agent_input_path: str | None = None
