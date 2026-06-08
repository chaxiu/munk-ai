from __future__ import annotations

from typing import cast

from munk.adapters.shared.schedule_presenters import (
    build_schedule_detail_data,
    build_schedule_list_data,
    build_schedule_run_list_data,
)
from munk.scheduling.registry import ScheduleRegistry
from munk.services.machine_contracts import MachineCommandResponse, build_error_result, build_success_result


class ScheduleQueryService:
    def __init__(self, *, registry: ScheduleRegistry | None = None) -> None:
        self._registry = registry or ScheduleRegistry()

    def list_schedules(
        self,
        *,
        enabled: bool | None,
        app_id: str | None,
        keyword: str | None,
        limit: int,
        offset: int,
    ) -> MachineCommandResponse:
        try:
            records, total = self._registry.list_schedules(
                enabled=enabled,
                app_id=app_id,
                keyword=keyword,
                limit=limit,
                offset=offset,
            )
            data = build_schedule_list_data(records, total=total, limit=limit, offset=offset)
        except Exception as exc:  # noqa: BLE001
            return build_error_result(command="schedules_list", exc=cast(Exception, exc))
        return build_success_result(command="schedules_list", data=data.model_dump(mode="json"))

    def get_schedule(self, *, schedule_id: str, recent_runs_limit: int = 10) -> MachineCommandResponse:
        try:
            record = self._registry.get_schedule(schedule_id)
            recent_runs = self._registry.list_schedule_runs(schedule_id, limit=recent_runs_limit)
            active_run = self._registry.find_active_or_queued_run_for_schedule(schedule_id)
            queued_run_count = self._registry.count_runs_for_schedule(schedule_id, statuses=["queued"])
            data = build_schedule_detail_data(
                record,
                recent_runs=recent_runs,
                active_schedule_run_id=active_run.schedule_run_id if active_run is not None else None,
                queued_run_count=queued_run_count,
            )
        except Exception as exc:  # noqa: BLE001
            return build_error_result(command="schedules_get", exc=cast(Exception, exc))
        return build_success_result(command="schedules_get", data=data.model_dump(mode="json"))

    def list_schedule_runs(self, *, schedule_id: str, limit: int) -> MachineCommandResponse:
        try:
            runs = self._registry.list_schedule_runs(schedule_id, limit=limit)
            data = build_schedule_run_list_data(schedule_id=schedule_id, runs=runs)
        except Exception as exc:  # noqa: BLE001
            return build_error_result(command="schedule_runs_list", exc=cast(Exception, exc))
        return build_success_result(command="schedule_runs_list", data=data.model_dump(mode="json"))
