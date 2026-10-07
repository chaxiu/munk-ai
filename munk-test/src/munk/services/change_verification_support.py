from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from munk.services.plan_execution_service import SupportsPlanOperationRecord


ChangeVerificationProgressCallback = Callable[[str, str | None, dict[str, Any]], None]


class SupportsChangeVerificationTracker(Protocol):
    operation_id: str

    def should_cancel(self) -> bool: ...

    def raise_if_cancelled(self) -> None: ...

    def append_event(
        self,
        *,
        event_type: str,
        message: str | None,
        data: dict[str, Any] | None = None,
    ) -> None: ...

    def update_artifacts(self, artifacts: dict[str, str]) -> object | None: ...

    def update_progress(self, **progress: Any) -> object | None: ...

    def get_record(self) -> SupportsPlanOperationRecord: ...


class ChangeVerificationProgressReporter:
    def __init__(
        self,
        *,
        tracker: SupportsChangeVerificationTracker | None,
        progress_callback: ChangeVerificationProgressCallback | None,
    ) -> None:
        self._tracker = tracker
        self._progress_callback = progress_callback

    def should_cancel(self) -> bool:
        tracker = self._tracker
        if tracker is None:
            return False
        return tracker.should_cancel()

    def append_event(
        self,
        event_type: str,
        message: str | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        payload = data or {}
        progress_callback = self._progress_callback
        if progress_callback is not None:
            progress_callback(event_type, message, payload)
            return
        tracker = self._tracker
        if tracker is not None:
            tracker.append_event(event_type=event_type, message=message, data=payload)

    def update_artifacts(self, artifacts: dict[str, str]) -> None:
        tracker = self._tracker
        if tracker is not None:
            tracker.update_artifacts(artifacts)

    def operation_id(self) -> str | None:
        tracker = self._tracker
        if tracker is None:
            return None
        try:
            return tracker.get_record().operation_id
        except Exception:
            return tracker.operation_id
