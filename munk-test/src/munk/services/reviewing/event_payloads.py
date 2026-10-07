from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReviewTimelineEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    app_id: str
    root_dir: str | None = None
    retrieval_hit_count: int | None = None
    prompt_hit_count: int | None = None
    finding_count: int | None = None
    suggested_case_count: int | None = None
