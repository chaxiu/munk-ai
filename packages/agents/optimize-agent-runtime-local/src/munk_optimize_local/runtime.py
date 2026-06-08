from __future__ import annotations

from typing import Any

from munk.optimizing.health import OptimizeRuntimeHealth

from .service import OptimizeRuntimeService


class LocalOptimizeRuntime:
    runtime_id = "local"

    def __init__(self, *, resolved_config: Any) -> None:
        self._service = OptimizeRuntimeService(resolved_config=resolved_config)

    def optimize(self, request):  # noqa: ANN001
        return self._service.optimize(request)


class LocalOptimizeRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config: Any) -> LocalOptimizeRuntime:
        return LocalOptimizeRuntime(resolved_config=resolved_config)

    def diagnose(self) -> OptimizeRuntimeHealth:
        return OptimizeRuntimeHealth(runtime_id=self.runtime_id, status="ok", message="optimize local runtime is available")


def build_optimize_runtime_factory() -> LocalOptimizeRuntimeFactory:
    return LocalOptimizeRuntimeFactory()
