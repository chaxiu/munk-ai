from __future__ import annotations

from typing import Any

from munk.running.health import RunnerRuntimeHealth

from munk.services.events import RunEventSink

from .service import RunnerRuntimeService


class LocalRunnerRuntime:
    runtime_id = "local"

    def __init__(
        self,
        *,
        resolved_config: Any,
        event_sink: RunEventSink | None = None,
    ) -> None:
        self._service = RunnerRuntimeService(
            resolved_config=resolved_config,
            event_sink=event_sink,
        )

    def run(self, request, *, context, cancel_controller=None):  # noqa: ANN001
        return self._service.run(request, context=context, cancel_controller=cancel_controller)


class LocalRunnerRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config: Any, event_sink=None) -> LocalRunnerRuntime:  # noqa: ANN001
        return LocalRunnerRuntime(resolved_config=resolved_config, event_sink=event_sink)

    def diagnose(self) -> RunnerRuntimeHealth:
        return RunnerRuntimeHealth(runtime_id=self.runtime_id, status="ok", message="runner local runtime is available")


def build_runner_runtime_factory() -> LocalRunnerRuntimeFactory:
    return LocalRunnerRuntimeFactory()
