from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class KnowledgeAgentRuntimeHealth(BaseModel):
    runtime_id: str
    status: Literal["ok", "degraded", "error"]
    message: str
