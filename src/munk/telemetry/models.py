from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TelemetryProvider = Literal["posthog"]
TelemetryEntrypoint = Literal["cli", "local_api", "mcp"]


@dataclass(frozen=True)
class ResolvedTelemetryConfig:
    enabled: bool = True
    provider: TelemetryProvider = "posthog"
    posthog_host: str | None = None
    posthog_api_key: str | None = None
    timeout_sec: float = 2.0
    distinct_id_file: str | None = None


@dataclass(frozen=True)
class TelemetryEvent:
    event: str
    properties: dict[str, Any] = field(default_factory=dict)
