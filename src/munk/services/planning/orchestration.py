from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from munk.app_assets.storage import AppRegistry
from munk.config import ResolvedConfig
from munk.planning.models import ChangePlanInput, RequirementInput
from munk.planning.runtime import PlanRuntime
from munk.planning.storage import CoreCaseRegistry, PlanStore

from .materializer import MaterializedPlanArtifacts, PlanArtifactMaterializer
from .runtime_host import build_plan_cancel_controller, build_plan_runtime_context

PlanRequest = RequirementInput | ChangePlanInput


class PlanTrackerLike(Protocol):
    @property
    def operation_id(self) -> str | None: ...

    def append_event(
        self,
        event_type: str,
        message: str | None,
        data: dict[str, object] | None = None,
    ) -> None: ...

    def update_progress(self, **progress: Any) -> None: ...

    def should_cancel(self) -> bool: ...


@dataclass(frozen=True)
class PlanningStorageBundle:
    app_registry: AppRegistry
    core_case_registry: CoreCaseRegistry
    plan_store: PlanStore


def build_planning_storage_bundle(
    *,
    assets_root: Path | None,
    default_app_registry: AppRegistry | None = None,
    default_core_case_registry: CoreCaseRegistry | None = None,
    default_plan_store: PlanStore | None = None,
) -> PlanningStorageBundle:
    if assets_root is None:
        return PlanningStorageBundle(
            app_registry=default_app_registry or AppRegistry(),
            core_case_registry=default_core_case_registry or CoreCaseRegistry(),
            plan_store=default_plan_store or PlanStore(),
        )
    return PlanningStorageBundle(
        app_registry=AppRegistry(assets_root),
        core_case_registry=CoreCaseRegistry(assets_root),
        plan_store=PlanStore(assets_root),
    )


def execute_plan_generation(
    *,
    request: PlanRequest,
    tracker: PlanTrackerLike,
    resolved_config: ResolvedConfig,
    storage: PlanningStorageBundle,
    runtime_factory: Callable[[ResolvedConfig], PlanRuntime],
) -> MaterializedPlanArtifacts:
    built = build_plan_runtime_context(
        tracker=cast(Any, tracker),
        request=request,
        storage=storage,
    )
    runtime = runtime_factory(resolved_config)
    runtime_output = runtime.plan(
        request,
        context=built.runtime_context,
        cancel_controller=build_plan_cancel_controller(tracker=cast(Any, tracker)),
    )
    return PlanArtifactMaterializer(storage=storage).materialize_success(
        runtime_output=runtime_output,
        host_paths=built.host_paths,
    )


def build_plan_saved_payload(materialized: MaterializedPlanArtifacts) -> dict[str, object]:
    payload: dict[str, object] = {
        "app_id": materialized.plan.app_id,
        "plan_id": materialized.plan.plan_id,
        "case_count": len(materialized.plan.cases),
        "plan_path": str(materialized.plan_path),
        "snapshot_path": str(materialized.snapshot_path),
    }
    if materialized.planning_usage is not None:
        payload["planning_usage"] = materialized.planning_usage.model_dump(mode="json")
    return payload
