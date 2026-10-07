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
    # Align with Home recent-runs list: run_center surface only.
    recent_run_count = resolved_registry.count_operations(surface="run_center")
    return DashboardSummaryData(
        plan_count=summary.plan_count,
        case_count=summary.case_count,
        recent_run_count=recent_run_count,
    )
