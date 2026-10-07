from __future__ import annotations

import atexit
import platform
from time import perf_counter
from typing import Any, Protocol

from ..version import resolve_munk_version
from .config import resolve_telemetry_config
from .distinct_id import load_or_create_distinct_id
from .models import ResolvedTelemetryConfig, TelemetryEntrypoint
from .posthog_client import PosthogClient


class TelemetrySink(Protocol):
    def capture_app_started(self, *, entrypoint: TelemetryEntrypoint) -> None: ...

    def capture_command_started(
        self,
        *,
        entrypoint: TelemetryEntrypoint,
        command: str,
        properties: dict[str, Any] | None = None,
    ) -> float: ...

    def capture_command_finished(
        self,
        *,
        entrypoint: TelemetryEntrypoint,
        command: str,
        started_at: float,
        status: str,
        properties: dict[str, Any] | None = None,
    ) -> None: ...


def _package_version() -> str:
    return resolve_munk_version()


class NullTelemetryService:
    def capture_app_started(self, *, entrypoint: TelemetryEntrypoint) -> None:
        del entrypoint

    def capture_command_started(
        self,
        *,
        entrypoint: TelemetryEntrypoint,
        command: str,
        properties: dict[str, Any] | None = None,
    ) -> float:
        del entrypoint, command, properties
        return perf_counter()

    def capture_command_finished(
        self,
        *,
        entrypoint: TelemetryEntrypoint,
        command: str,
        started_at: float,
        status: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        del entrypoint, command, started_at, status, properties


class TelemetryService:
    def __init__(self, config: ResolvedTelemetryConfig) -> None:
        self._config = config
        self._distinct_id = load_or_create_distinct_id(config)
        self._version = _package_version()
        self._platform = platform.system().lower()
        self._client = PosthogClient(config)
        atexit.register(self.shutdown)

    def capture_app_started(self, *, entrypoint: TelemetryEntrypoint) -> None:
        self._capture(
            event="app_started",
            entrypoint=entrypoint,
            properties={},
        )

    def capture_command_started(
        self,
        *,
        entrypoint: TelemetryEntrypoint,
        command: str,
        properties: dict[str, Any] | None = None,
    ) -> float:
        started_at = perf_counter()
        self._capture(
            event="command_started",
            entrypoint=entrypoint,
            properties={"command": command, **(properties or {})},
        )
        return started_at

    def capture_command_finished(
        self,
        *,
        entrypoint: TelemetryEntrypoint,
        command: str,
        started_at: float,
        status: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        duration_ms = max(0, int((perf_counter() - started_at) * 1000))
        self._capture(
            event="command_finished",
            entrypoint=entrypoint,
            properties={
                "command": command,
                "status": status,
                "duration_ms": duration_ms,
                **(properties or {}),
            },
        )

    def shutdown(self) -> None:
        self._client.shutdown()

    def _capture(self, *, event: str, entrypoint: TelemetryEntrypoint, properties: dict[str, Any]) -> None:
        payload = {
            "entrypoint": entrypoint,
            "version": self._version,
            "platform": self._platform,
            **properties,
        }
        self._client.capture(
            distinct_id=self._distinct_id,
            event=event,
            properties=payload,
        )


def build_telemetry_service(
    *,
    workspace_root=None,
) -> TelemetrySink:
    config = resolve_telemetry_config(workspace_root=workspace_root)
    if not config.enabled or not config.posthog_api_key:
        return NullTelemetryService()
    try:
        return TelemetryService(config)
    except Exception:
        return NullTelemetryService()
