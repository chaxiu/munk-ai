from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from munk.app_assets.storage import AppRegistry
from munk.planning.case_rewrite_service import CaseRewriteService
from munk.planning.import_service import PlanImportService
from munk.planning.index_store import PlanCaseIndexStore
from munk.planning.plan_mutation_service import PlanMutationService
from munk.planning.storage import PlanStore


@dataclass(frozen=True)
class PlanRouteDependencies:
    plan_store_factory: Callable[[], PlanStore] | None = None
    index_store_factory: Callable[[], PlanCaseIndexStore] | None = None
    mutation_service_factory: Callable[[], PlanMutationService] | None = None
    rewrite_service_factory: Callable[[], CaseRewriteService] | None = None
    import_service_factory: Callable[[], PlanImportService] | None = None

    def get_plan_store(self) -> PlanStore:
        if self.plan_store_factory is not None:
            return self.plan_store_factory()
        return PlanStore()

    def get_index_store(self) -> PlanCaseIndexStore:
        if self.index_store_factory is not None:
            return self.index_store_factory()
        return PlanCaseIndexStore()

    def get_mutation_service(self) -> PlanMutationService:
        if self.mutation_service_factory is not None:
            return self.mutation_service_factory()
        return PlanMutationService(plan_store=self.get_plan_store())

    def get_rewrite_service(self) -> CaseRewriteService:
        if self.rewrite_service_factory is not None:
            return self.rewrite_service_factory()
        plan_store = self.get_plan_store()
        return CaseRewriteService(
            workspace_root=Path.cwd(),
            plan_store=plan_store,
            app_registry=AppRegistry(plan_store.root_dir),
        )

    def get_import_service(self) -> PlanImportService:
        if self.import_service_factory is not None:
            return self.import_service_factory()
        plan_store = self.get_plan_store()
        return PlanImportService(
            plan_store=plan_store,
            app_registry=AppRegistry(plan_store.root_dir),
        )
