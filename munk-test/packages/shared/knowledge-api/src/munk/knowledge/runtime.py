from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from munk.agent_runtime.events import AgentEventSink


def empty_details() -> dict[str, str]:
    return {}


class KnowledgeRuntimeUnavailableError(RuntimeError, LookupError):
    """Raised when no knowledge runtime is installed."""


class KnowledgeRuntimeConflictError(RuntimeError, LookupError):
    """Raised when multiple knowledge runtimes are installed without selection."""


class KnowledgeRuntimeHealth(BaseModel):
    runtime_id: str
    status: Literal["ok", "warning", "error"]
    message: str
    details: dict[str, str] = Field(default_factory=empty_details)
@dataclass(frozen=True)
class KnowledgeManagedPaths:
    root_dir: Path
    request_dump_path: Path | None = None


@dataclass(frozen=True)
class KnowledgeRuntimeContext:
    operation_id: str | None
    managed_paths: KnowledgeManagedPaths
    progress: AgentEventSink | None = None
