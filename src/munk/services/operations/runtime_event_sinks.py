from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from munk.agent_runtime import AgentRuntimeEvent


class SupportsAgentRuntimeTimeline(Protocol):
    def append_agent_runtime_event(self, event: AgentRuntimeEvent) -> None: ...

    def update_progress(self, **progress: object) -> object: ...


class TrackerAgentRuntimeTimelineSink:
    def __init__(
        self,
        tracker: SupportsAgentRuntimeTimeline,
        *,
        progress_builder: Callable[[AgentRuntimeEvent], dict[str, object]] | None = None,
    ) -> None:
        self._tracker = tracker
        self._progress_builder = progress_builder

    def emit(self, event: AgentRuntimeEvent) -> None:
        self._tracker.append_agent_runtime_event(event)
        if self._progress_builder is None:
            return
        progress = self._progress_builder(event)
        if progress:
            self._tracker.update_progress(**progress)
