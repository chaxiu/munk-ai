from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from munk.planning.models import RequirementPlan
from munk.planning.runtime import PlanRuntimeOutput
from munk.token_usage import TokenUsage

from .runtime_host import PlanHostManagedPaths


@dataclass(frozen=True)
class MaterializedPlanArtifacts:
    plan: RequirementPlan
    plan_path: Path
    snapshot_path: Path
    planning_usage: TokenUsage | None = None

    @property
    def artifacts(self) -> dict[str, str]:
        return {
            "plan": str(self.plan_path),
            "snapshot": str(self.snapshot_path),
        }


class PlanArtifactMaterializer:
    def __init__(self, *, storage) -> None:  # noqa: ANN001
        self._storage = storage

    def materialize_success(
        self,
        *,
        runtime_output: PlanRuntimeOutput,
        host_paths: PlanHostManagedPaths,
    ) -> MaterializedPlanArtifacts:
        plan = self._storage.core_case_registry.apply_to_cases(
            runtime_output.result_data.plan.app_id,
            list(runtime_output.result_data.plan.cases),
        )
        materialized_plan = runtime_output.result_data.plan.model_copy(update={"cases": plan})
        plan_path = self._storage.plan_store.save(materialized_plan)
        snapshot_path = self._storage.plan_store.export_snapshot(materialized_plan)
        if plan_path != host_paths.plan_path:
            host_paths.plan_path.write_text(plan_path.read_text(encoding="utf-8"), encoding="utf-8")
        if snapshot_path != host_paths.snapshot_path:
            host_paths.snapshot_path.write_text(snapshot_path.read_text(encoding="utf-8"), encoding="utf-8")
        return MaterializedPlanArtifacts(
            plan=materialized_plan,
            plan_path=plan_path,
            snapshot_path=snapshot_path,
            planning_usage=runtime_output.token_usage,
        )
