from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from munk.execution.models import CaseExecutionRequest
from munk.services.events import RunEvent
from munk.services.models import RunPaths, RunStatus


@dataclass
class RunExecutionSession:
    request: CaseExecutionRequest
    events: list[RunEvent] = field(default_factory=list)
    status: RunStatus = field(default_factory=lambda: RunStatus(running=False))
    stop_requested: bool = False
    cancel_checker: Callable[[], bool] | None = None
    paths: RunPaths | None = None
    context: Any = None

    def should_stop(self) -> bool:
        if self.stop_requested:
            return True
        if self.cancel_checker is None:
            return False
        if self.cancel_checker():
            self.stop_requested = True
            return True
        return False
