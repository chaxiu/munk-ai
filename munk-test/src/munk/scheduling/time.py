from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter

from munk.services.machine_contracts import InvalidMachineRequestError


def validate_timezone_name(timezone_name: str) -> str:
    normalized = timezone_name.strip()
    if not normalized:
        raise InvalidMachineRequestError("timezone must not be empty")
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise InvalidMachineRequestError(f"invalid timezone: {timezone_name}") from exc
    return normalized


def validate_cron_expr(cron_expr: str) -> str:
    normalized = cron_expr.strip()
    if not normalized:
        raise InvalidMachineRequestError("cron_expr must not be empty")
    if len(normalized.split()) != 5:
        raise InvalidMachineRequestError("cron_expr must use standard 5-field format")
    try:
        croniter(normalized, datetime.now(timezone.utc))
    except Exception as exc:  # noqa: BLE001
        raise InvalidMachineRequestError(f"invalid cron_expr: {cron_expr}") from exc
    return normalized


def compute_next_run_at(
    *,
    timezone_name: str,
    cron_expr: str,
    reference_time: datetime | None = None,
) -> str:
    validated_timezone = validate_timezone_name(timezone_name)
    validated_cron = validate_cron_expr(cron_expr)
    tz = ZoneInfo(validated_timezone)
    base = reference_time or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    local_base = base.astimezone(tz)
    next_local = croniter(validated_cron, local_base).get_next(datetime)
    if next_local.tzinfo is None:
        next_local = next_local.replace(tzinfo=tz)
    return next_local.astimezone(timezone.utc).isoformat()
