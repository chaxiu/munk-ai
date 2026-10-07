from __future__ import annotations

from munk.config import ResolvedConfig
from munk.planning.errors import PlanRuntimeUnavailableError
from munk.planning.health import PlanRuntimeHealth
from munk.planning.runtime import create_plan_runtime, diagnose_plan_runtime


def resolve_plan_runtime(*, resolved_config: ResolvedConfig):
    try:
        return create_plan_runtime(resolved_config=resolved_config)
    except LookupError as exc:
        raise PlanRuntimeUnavailableError(str(exc)) from exc


def plan_runtime_health() -> PlanRuntimeHealth:
    return diagnose_plan_runtime()
