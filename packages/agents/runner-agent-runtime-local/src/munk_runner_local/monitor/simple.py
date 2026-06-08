from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from munk.device import CurrentAppState


@dataclass(frozen=True)
class MonitorResult:
    should_stop: bool
    reason: str | None


class SimpleMonitor:
    def __init__(self, max_steps: int = 0, max_duration: float = 0.0) -> None:
        self._max_steps = max_steps
        self._max_duration = max_duration
        self._start_time = time.monotonic()
        self._steps = 0

    def on_step(self, app_info: CurrentAppState | dict[str, Any] | None) -> MonitorResult:
        self._steps += 1
        if self._max_steps > 0 and self._steps >= self._max_steps:
            return MonitorResult(True, "max_steps")
        if self._max_duration > 0 and (time.monotonic() - self._start_time) >= self._max_duration:
            return MonitorResult(True, "max_duration")
        if app_info is not None and _app_entry_identity(app_info) is None:
            return MonitorResult(True, "app_not_running")
        return MonitorResult(False, None)

    @property
    def steps(self) -> int:
        return self._steps

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start_time


def _app_entry_identity(app_info: CurrentAppState | dict[str, Any]) -> str | None:
    if isinstance(app_info, CurrentAppState):
        return app_info.entry_identity
    for key in ("entry_identity", "package", "bundle_id", "origin", "base_url", "url"):
        value = app_info.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None
