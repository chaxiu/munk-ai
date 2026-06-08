from __future__ import annotations

from typing import Any

from munk.planning.health import PlanRuntimeHealth

from .service import PlanRuntimeService


class LocalPlanRuntime:
    def __init__(
        self,
        *,
        resolved_config: Any,
        plan_agent: Any | None = None,
        plan_id_factory=None,  # noqa: ANN001
        case_id_factory=None,  # noqa: ANN001
    ) -> None:
        self._service = PlanRuntimeService(
            resolved_config=resolved_config,
            plan_agent=plan_agent,
            plan_id_factory=plan_id_factory,
            case_id_factory=case_id_factory,
        )

    def plan(self, request, *, context, cancel_controller=None):  # noqa: ANN001
        return self._service.plan(request, context=context, cancel_controller=cancel_controller)


class LocalPlanRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config: Any) -> LocalPlanRuntime:
        return LocalPlanRuntime(resolved_config=resolved_config)

    def diagnose(self) -> PlanRuntimeHealth:
        return PlanRuntimeHealth(runtime_id=self.runtime_id, status="ok", message="plan local runtime is available")


def build_plan_runtime_factory() -> LocalPlanRuntimeFactory:
    return LocalPlanRuntimeFactory()
