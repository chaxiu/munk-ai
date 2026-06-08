from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from munk.user_data import cache_home

from .models import ResolvedTelemetryConfig


def distinct_id_path(config: ResolvedTelemetryConfig) -> Path:
    if config.distinct_id_file:
        return Path(config.distinct_id_file).expanduser().resolve()
    return cache_home() / "telemetry" / "distinct_id"


def load_or_create_distinct_id(config: ResolvedTelemetryConfig) -> str:
    path = distinct_id_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = str(uuid4())
    path.write_text(value, encoding="utf-8")
    return value
