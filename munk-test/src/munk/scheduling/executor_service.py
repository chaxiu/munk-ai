from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.scheduling.models import ScheduleRecord, ScheduleRunRecord
from munk.scheduling.registry import ScheduleRegistry
from munk.scheduling.request_adapter import build_run_plans_request_from_schedule
from munk.scheduling.time import compute_next_run_at
from munk.services.errors import OperationNotFoundError
from munk.services.operations.models import OperationRecord
from munk.services.operations.registry import OperationRegistry

_logger = logging.getLogger(__name__)

BackgroundSubmitter = Callable[[str, Callable[[], None]], None]


class ScheduleExecutorService:
    def __init__(
        self,
        *,
        registry: ScheduleRegistry | None = None,
        machine_service: Any,
        operation_registry: OperationRegistry | None = None,
        background_submitter: BackgroundSubmitter | None = None,
        started_at: datetime | None = None,
    ) -> None:
        self._registry = registry or ScheduleRegistry()
        self._machine_service = machine_service
        self._operation_registry = operation_registry or OperationRegistry()
        self._background_submitter = background_submitter
        self._started_at = (started_at or datetime.now(timezone.utc)).astimezone(timezone.utc)

    def enqueue_due_schedules(self, *, now: datetime | None = None, limit: int = 100) -> list[ScheduleRunRecord]:
        current = _ensure_utc(now or datetime.now(timezone.utc))
        due_schedules = self._registry.list_due_schedules(now_iso=current.isoformat(), limit=limit)
        created_runs: list[ScheduleRunRecord] = []
        for schedule in due_schedules:
            if schedule.next_run_at is None:
                continue
            scheduled_for = _parse_utc(schedule.next_run_at)
            should_enqueue = scheduled_for >= self._started_at
            existing = self._registry.find_active_or_queued_run_for_schedule(schedule.schedule_id)
            if should_enqueue and existing is None:
                created = self._registry.create_queued_run_if_absent(
                    schedule_id=schedule.schedule_id,
                    scheduled_for=schedule.next_run_at,
                    schedule_run_id=_new_schedule_run_id(),
                    created_at=current.isoformat(),
                )
                if created is not None:
                    created_runs.append(created)
            next_run_at = _advance_next_run_at(schedule=schedule, current_due=scheduled_for, now=current)
            self._registry.update_schedule_fields(
                schedule.schedule_id,
                next_run_at=next_run_at,
                updated_at=current.isoformat(),
            )
        return created_runs

    def dispatch_next_run(self, *, now: datetime | None = None) -> ScheduleRunRecord | None:
        current = _ensure_utc(now or datetime.now(timezone.utc))
        if self._registry.find_active_schedule_run() is not None:
            return None
        claimed = self._registry.claim_next_queued_run(claimed_at=current.isoformat())
        if claimed is None:
            return None
        try:
            schedule = self._registry.get_schedule(claimed.schedule_id)
            request = self._build_run_request(schedule)
            response = self._machine_service.submit_run_plans(
                request=request,
                wait=False,
                detach=False,
                background_submitter=self._background_submitter,
            )
            payload = cast(dict[str, Any], response.payload)
            if payload.get("ok") is not True:
                error = payload.get("error") or {}
                return self._registry.update_schedule_run(
                    claimed.schedule_run_id,
                    status="failed",
                    error_code=error.get("code"),
                    error_message=error.get("message"),
                    finished_at=current.isoformat(),
                )
            data = payload.get("data") or {}
            operation_id = data.get("operation_id")
            if not isinstance(operation_id, str) or not operation_id:
                return self._registry.update_schedule_run(
                    claimed.schedule_run_id,
                    status="failed",
                    error_code="missing_operation_id",
                    error_message="submit_run_plans returned without operation_id",
                    finished_at=current.isoformat(),
                )
            return self._registry.update_schedule_run(
                claimed.schedule_run_id,
                status="triggered",
                operation_id=operation_id,
                triggered_at=current.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001
            _logger.exception("failed to dispatch schedule run %s", claimed.schedule_run_id)
            return self._registry.update_schedule_run(
                claimed.schedule_run_id,
                status="failed",
                error_code="schedule_dispatch_failed",
                error_message=str(exc),
                finished_at=current.isoformat(),
            )

    def sync_triggered_runs(self, *, now: datetime | None = None, limit: int = 100) -> list[ScheduleRunRecord]:
        current = _ensure_utc(now or datetime.now(timezone.utc))
        changed: list[ScheduleRunRecord] = []
        for schedule_run in self._registry.list_runs_by_statuses(statuses=["triggered"], limit=limit):
            if not schedule_run.operation_id:
                changed.append(
                    self._registry.update_schedule_run(
                        schedule_run.schedule_run_id,
                        status="failed",
                        error_code="missing_operation_id",
                        error_message="triggered schedule run missing operation_id",
                        finished_at=current.isoformat(),
                    )
                )
                continue
            try:
                operation = self._operation_registry.get_operation(schedule_run.operation_id)
            except Exception as exc:  # noqa: BLE001
                _logger.exception("failed to sync schedule run %s", schedule_run.schedule_run_id)
                error_code = "operation_not_found" if isinstance(exc, OperationNotFoundError) else "schedule_sync_failed"
                changed.append(
                    self._registry.update_schedule_run(
                        schedule_run.schedule_run_id,
                        status="failed",
                        error_code=error_code,
                        error_message=str(exc),
                        finished_at=current.isoformat(),
                    )
                )
                continue
            if operation.status in ("queued", "running"):
                continue
            changed.append(self._complete_run(schedule_run=schedule_run, operation=operation, now=current))
        return changed

    def run_once(self, *, now: datetime | None = None) -> None:
        current = _ensure_utc(now or datetime.now(timezone.utc))
        self.enqueue_due_schedules(now=current)
        self.sync_triggered_runs(now=current)
        self.dispatch_next_run(now=current)

    def _complete_run(
        self,
        *,
        schedule_run: ScheduleRunRecord,
        operation: OperationRecord,
        now: datetime,
    ) -> ScheduleRunRecord:
        operation_status = operation.status
        if operation_status == "succeeded":
            status = "succeeded"
        elif operation_status == "failed":
            status = "failed"
        else:
            status = "cancelled"
        updated = self._registry.update_schedule_run(
            schedule_run.schedule_run_id,
            status=status,
            error_code=operation.error_code,
            error_message=operation.error_message,
            finished_at=now.isoformat(),
        )
        self._registry.update_schedule_fields(
            schedule_run.schedule_id,
            last_run_at=now.isoformat(),
            updated_at=now.isoformat(),
        )
        return updated

    @staticmethod
    def _build_run_request(schedule: ScheduleRecord) -> RunPlansCliRequest:
        return build_run_plans_request_from_schedule(schedule)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return _ensure_utc(parsed)


def _advance_next_run_at(*, schedule: ScheduleRecord, current_due: datetime, now: datetime) -> str:
    candidate = current_due
    next_run_at = schedule.next_run_at or current_due.isoformat()
    while candidate <= now:
        next_run_at = compute_next_run_at(
            timezone_name=schedule.timezone,
            cron_expr=schedule.cron_expr,
            reference_time=candidate,
        )
        candidate = _parse_utc(next_run_at)
    return next_run_at


def _new_schedule_run_id() -> str:
    return f"schedule-run-{uuid4().hex[:12]}"
