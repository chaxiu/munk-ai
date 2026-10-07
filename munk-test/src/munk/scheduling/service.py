from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from munk.app_assets.storage import AppRegistry
from munk.planning.storage import PlanStore
from munk.scheduling.models import ScheduleRecord
from munk.scheduling.registry import ScheduleRegistry
from munk.scheduling.time import compute_next_run_at, validate_cron_expr, validate_timezone_name
from munk.services.errors import ScheduleDeletionConflictError
from munk.services.machine_contracts import InvalidMachineRequestError


class _NormalizedScheduleRequest(TypedDict):
    name: str
    app_id: str
    device_ref: str
    timezone: str
    cron_expr: str
    enabled: bool
    request_json: dict[str, Any]


class ScheduleService:
    def __init__(
        self,
        *,
        registry: ScheduleRegistry | None = None,
        plan_store: PlanStore | None = None,
        app_registry: AppRegistry | None = None,
    ) -> None:
        self._registry = registry or ScheduleRegistry()
        self._plan_store = plan_store or PlanStore()
        self._app_registry = app_registry or AppRegistry(self._plan_store.root_dir)

    def create_schedule_record(
        self,
        *,
        name: str | None,
        app_id: str,
        plan_ids: list[str],
        device_ref: str,
        timezone_name: str | None,
        cron_expr: str,
        headless: bool,
        fail_fast: bool,
        artifact_path: Path | None,
        assets_root: Path | None,
        runtime_overrides: dict[str, Any],
        enabled: bool,
    ) -> ScheduleRecord:
        normalized = self._normalize_request(
            name=name,
            app_id=app_id,
            plan_ids=plan_ids,
            device_ref=device_ref,
            timezone_name=timezone_name,
            cron_expr=cron_expr,
            headless=headless,
            fail_fast=fail_fast,
            artifact_path=artifact_path,
            assets_root=assets_root,
            runtime_overrides=runtime_overrides,
            enabled=enabled,
        )
        now = datetime.now().astimezone()
        schedule_id = f"schedule-{uuid4().hex[:12]}"
        timezone_name = normalized["timezone"]
        name = normalized["name"] or now.astimezone().strftime("%Y-%m-%d %H:%M")
        next_run_at = (
            compute_next_run_at(
                timezone_name=timezone_name,
                cron_expr=normalized["cron_expr"],
            )
            if normalized["enabled"]
            else None
        )
        record = ScheduleRecord(
            schedule_id=schedule_id,
            name=name,
            app_id=normalized["app_id"],
            device_ref=normalized["device_ref"],
            timezone=timezone_name,
            enabled=normalized["enabled"],
            cron_expr=normalized["cron_expr"],
            request_json=normalized["request_json"],
            next_run_at=next_run_at,
        )
        return self._registry.create_schedule(record)

    def update_schedule_record(
        self,
        schedule_id: str,
        *,
        name: str | None,
        app_id: str,
        plan_ids: list[str],
        device_ref: str,
        timezone_name: str | None,
        cron_expr: str,
        headless: bool,
        fail_fast: bool,
        artifact_path: Path | None,
        assets_root: Path | None,
        runtime_overrides: dict[str, Any],
        enabled: bool,
    ) -> ScheduleRecord:
        existing = self._registry.get_schedule(schedule_id)
        normalized = self._normalize_request(
            name=name,
            app_id=app_id,
            plan_ids=plan_ids,
            device_ref=device_ref,
            timezone_name=timezone_name,
            cron_expr=cron_expr,
            headless=headless,
            fail_fast=fail_fast,
            artifact_path=artifact_path,
            assets_root=assets_root,
            runtime_overrides=runtime_overrides,
            enabled=enabled,
        )
        next_run_at = (
            compute_next_run_at(
                timezone_name=normalized["timezone"],
                cron_expr=normalized["cron_expr"],
            )
            if normalized["enabled"]
            else None
        )
        updated = existing.model_copy(
            update={
                "name": normalized["name"] or existing.name,
                "app_id": normalized["app_id"],
                "device_ref": normalized["device_ref"],
                "timezone": normalized["timezone"],
                "enabled": normalized["enabled"],
                "cron_expr": normalized["cron_expr"],
                "request_json": normalized["request_json"],
                "next_run_at": next_run_at,
                "updated_at": datetime.now().astimezone().isoformat(),
            }
        )
        return self._registry.update_schedule(updated)

    def enable_schedule(self, schedule_id: str) -> ScheduleRecord:
        existing = self._registry.get_schedule(schedule_id)
        next_run_at = compute_next_run_at(timezone_name=existing.timezone, cron_expr=existing.cron_expr)
        return self._registry.set_schedule_enabled(
            schedule_id,
            enabled=True,
            next_run_at=next_run_at,
            updated_at=datetime.now().astimezone().isoformat(),
        )

    def disable_schedule(self, schedule_id: str) -> ScheduleRecord:
        return self._registry.set_schedule_enabled(
            schedule_id,
            enabled=False,
            next_run_at=None,
            updated_at=datetime.now().astimezone().isoformat(),
        )

    def delete_schedule(self, schedule_id: str) -> None:
        self._registry.get_schedule(schedule_id)
        blocking_statuses = [
            status
            for status in ("dispatching", "triggered")
            if self._registry.has_schedule_runs_in_statuses(schedule_id, statuses=[status])
        ]
        if blocking_statuses:
            raise ScheduleDeletionConflictError(
                schedule_id=schedule_id,
                blocking_statuses=blocking_statuses,
            )
        self._registry.delete_schedule(schedule_id)

    def _normalize_request(
        self,
        *,
        name: str | None,
        app_id: str,
        plan_ids: list[str],
        device_ref: str,
        timezone_name: str | None,
        cron_expr: str,
        headless: bool,
        fail_fast: bool,
        artifact_path: Path | None,
        assets_root: Path | None,
        runtime_overrides: dict[str, Any],
        enabled: bool,
    ) -> _NormalizedScheduleRequest:
        app_id = app_id.strip()
        if not app_id:
            raise InvalidMachineRequestError("app_id must not be empty")
        if not self._app_registry.exists(app_id):
            raise InvalidMachineRequestError(f"app '{app_id}' not found")
        if not plan_ids:
            raise InvalidMachineRequestError("plan_ids must not be empty")
        plan_ids = [plan_id.strip() for plan_id in plan_ids if plan_id.strip()]
        if not plan_ids:
            raise InvalidMachineRequestError("plan_ids must not be empty")
        for plan_id in plan_ids:
            try:
                self._plan_store.load(app_id, plan_id)
            except FileNotFoundError as exc:
                raise InvalidMachineRequestError(str(exc)) from exc
        device_ref = device_ref.strip()
        if not device_ref:
            raise InvalidMachineRequestError("device_ref must not be empty")
        timezone_name = validate_timezone_name(timezone_name or _detect_local_timezone_name())
        cron_expr = validate_cron_expr(cron_expr)
        name = (name or "").strip()
        request_json = {
            "app_id": app_id,
            "plan_ids": plan_ids,
            "device_ref": device_ref,
            "headless": headless,
            "fail_fast": fail_fast,
            "artifact_path": str(artifact_path) if artifact_path else None,
            "assets_root": str(assets_root) if assets_root else None,
            "runtime_overrides": runtime_overrides,
        }
        return {
            "name": name,
            "app_id": app_id,
            "device_ref": device_ref,
            "timezone": timezone_name,
            "cron_expr": cron_expr,
            "enabled": enabled,
            "request_json": request_json,
        }


def _detect_local_timezone_name() -> str:
    tzinfo = datetime.now().astimezone().tzinfo
    if tzinfo is None:
        raise InvalidMachineRequestError("failed to detect local timezone")
    timezone_name = getattr(tzinfo, "key", None) or str(tzinfo)
    return validate_timezone_name(timezone_name)
