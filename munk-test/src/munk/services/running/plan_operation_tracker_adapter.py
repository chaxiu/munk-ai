from __future__ import annotations

from dataclasses import dataclass

from munk.services.operations.service import OperationTracker
from munk.services.plan_execution_service import SupportsPlanOperationRecord


class PlanOperationTrackerAdapter:
    def __init__(self, tracker: OperationTracker) -> None:
        self._tracker = tracker

    def should_cancel(self) -> bool:
        return self._tracker.should_cancel()

    def raise_if_cancelled(self) -> None:
        self._tracker.raise_if_cancelled()

    def update_artifacts(self, artifacts: dict[str, str]) -> None:
        self._tracker.update_artifacts(artifacts)

    def update_progress(self, **progress: object) -> None:
        self._tracker.update_progress(**progress)

    def get_record(self) -> SupportsPlanOperationRecord:
        record = self._tracker.get_record()
        return _PlanOperationRecordView(
            operation_id=record.operation_id,
            kind=record.kind,
        )


@dataclass
class _PlanOperationRecordView:
    operation_id: str
    kind: str | None
