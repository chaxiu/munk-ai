from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.scheduling.models import ScheduleRecord


def build_run_plans_request_from_schedule(record: ScheduleRecord) -> RunPlansCliRequest:
    request_json = record.request_json
    runtime_overrides = cast(dict[str, Any], request_json.get("runtime_overrides") or {})
    artifact_path = request_json.get("artifact_path")
    assets_root = request_json.get("assets_root")
    return RunPlansCliRequest(
        app_id=record.app_id,
        plan_ids=[str(item) for item in request_json.get("plan_ids", []) if str(item).strip()],
        device_ref=record.device_ref,
        headless=bool(request_json.get("headless", False)),
        artifact_path=Path(artifact_path) if artifact_path else None,
        assets_root=Path(assets_root) if assets_root else None,
        runtime_overrides=runtime_overrides,
        fail_fast=bool(request_json.get("fail_fast", False)),
    )
