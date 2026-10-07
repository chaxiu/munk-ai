from __future__ import annotations

import importlib
from typing import Any, Protocol

from .models import ResolvedTelemetryConfig


class SupportsPosthogCapture(Protocol):
    def capture(self, distinct_id: str, event: str, properties: dict[str, Any]) -> None: ...

    def shutdown(self) -> None: ...


class PosthogClient:
    def __init__(self, config: ResolvedTelemetryConfig) -> None:
        if not config.posthog_api_key:
            raise ValueError("PostHog API key is required")
        module = importlib.import_module("posthog")
        posthog_cls = getattr(module, "Posthog")
        kwargs: dict[str, Any] = {}
        if config.posthog_host:
            kwargs["host"] = config.posthog_host
        self._client: SupportsPosthogCapture = posthog_cls(project_api_key=config.posthog_api_key, **kwargs)

    def capture(self, *, distinct_id: str, event: str, properties: dict[str, Any]) -> None:
        self._client.capture(distinct_id=distinct_id, event=event, properties=properties)

    def shutdown(self) -> None:
        self._client.shutdown()
