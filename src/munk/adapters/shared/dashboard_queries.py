from __future__ import annotations

from munk.adapters.shared.payload_models import DashboardSummaryData
from munk.planning.index_store import PlanCaseIndexStore
from munk.services.operations.registry import OperationRegistry


def build_dashboard_summary_payload(
    *,
    index_store: PlanCaseIndexStore | None = None,
    operation_registry: OperationRegistry | None = None,
) -> DashboardSummaryData:
    resolved_index_store = index_store or PlanCaseIndexStore()
    resolved_registry = operation_registry or OperationRegistry()
    summary = resolved_index_store.summary()
    recent_runs = resolved_registry.list_operations(limit=10)
    return DashboardSummaryData(
        plan_count=summary.plan_count,
        case_count=summary.case_count,
        recent_run_count=len(recent_runs),
    )
