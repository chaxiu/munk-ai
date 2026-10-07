from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from munk.planning.case_rewrite_service import CaseRewriteService
from munk.planning.import_service import PlanImportService
from munk.planning.index_store import PlanCaseIndexStore
from munk.planning.plan_mutation_service import PlanMutationService
from munk.planning.storage import PlanStore

from .plan_case_routes import register_plan_case_routes
from .plan_query_routes import register_plan_query_routes
from .plan_route_dependencies import PlanRouteDependencies


def build_plan_router(
    *,
    plan_store_factory: Callable[[], PlanStore] | None = None,
    index_store_factory: Callable[[], PlanCaseIndexStore] | None = None,
    mutation_service_factory: Callable[[], PlanMutationService] | None = None,
    rewrite_service_factory: Callable[[], CaseRewriteService] | None = None,
    import_service_factory: Callable[[], PlanImportService] | None = None,
) -> APIRouter:
    router = APIRouter()
    dependencies = PlanRouteDependencies(
        plan_store_factory=plan_store_factory,
        index_store_factory=index_store_factory,
        mutation_service_factory=mutation_service_factory,
        rewrite_service_factory=rewrite_service_factory,
        import_service_factory=import_service_factory,
    )
    register_plan_query_routes(router, dependencies)
    register_plan_case_routes(router, dependencies)
    return router
