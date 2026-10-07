from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from munk.services.operations.models import VerificationVerdict
from munk.token_usage import TokenUsage


class BatchStartedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    app_id: str
    device_ref: str | None = None
    plan_ids: list[str] | None = None
    total_children: int | None = None


class BatchChildStartedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    operation_id: str
    title: str
    position_label: str | None = None
    parent_operation_id: str | None = None
    case_id: str | None = None
    plan_id: str | None = None


class BatchChildFinishedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    operation_id: str
    title: str
    status: str
    verification_verdict: VerificationVerdict = None
    position_index: int | None = None
    position_label: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    token_usage: TokenUsage | None = None
    case_id: str | None = None
    plan_id: str | None = None


class BatchStoppedEarlyEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan_id: str
    operation_id: str


class BatchFinishedEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_children: int
    completed_children: int
    verification_verdict: VerificationVerdict = None
    stopped_early: bool = False
