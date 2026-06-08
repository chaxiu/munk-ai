from __future__ import annotations

from munk.adapters.shared.payload_models import (
    CaseBriefData,
    CaseDetailData,
    CaseSearchData,
    CaseSearchItemData,
    LatestOptimizeOperationData,
    PlanDetailData,
    PlanLatestRunSummaryData,
    PlanListData,
    PlanListItemData,
)
from munk.planning.index_store import IndexedCaseRecord, IndexedPlanRecord, PlanCaseIndexStore
from munk.planning.models import RequirementPlan
from munk.planning.storage import PlanStore
from munk.services.operations.registry import OperationRegistry
from munk.testing import TestCase


def list_plans_payload(
    *,
    index_store: PlanCaseIndexStore,
    app_id: str | None,
    source: str | None,
    case_count_mode: str | None,
    limit: int,
    offset: int,
    include_latest_run: bool = False,
) -> PlanListData:
    records, total = index_store.list_plans_page(
        app_id=app_id,
        source=source,
        case_count_mode=case_count_mode,
        limit=limit,
        offset=offset,
    )
    items = [build_plan_list_item(record) for record in records]
    if include_latest_run and items:
        enrich_plan_items_with_latest_runs(items)
    return PlanListData(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def search_cases_payload(
    *,
    index_store: PlanCaseIndexStore,
    app_id: str | None,
    plan_id: str | None,
    case_id: str | None,
    query: str | None,
    is_core_case: bool | None,
    start_mode: str | None,
    limit: int,
    offset: int,
) -> CaseSearchData:
    items, total = index_store.search_cases(
        app_id=app_id,
        plan_id=plan_id,
        case_id=case_id,
        query=query,
        is_core_case=is_core_case,
        start_mode=start_mode,
        limit=limit,
        offset=offset,
    )
    return CaseSearchData(
        items=[build_case_search_item(record) for record in items],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_plan_payload(*, plan_store: PlanStore, app_id: str, plan_id: str) -> PlanDetailData:
    return build_plan_detail_data(plan_store.load(app_id, plan_id))


def get_case_payload(*, plan_store: PlanStore, app_id: str, plan_id: str, case_id: str) -> CaseDetailData:
    plan = plan_store.load(app_id, plan_id)
    case = next((item for item in plan.cases if item.case_id == case_id), None)
    if case is None:
        raise LookupError(f"case '{case_id}' not found in plan '{app_id}/{plan_id}'")
    return build_case_detail_data(plan, case, latest_optimize=_find_latest_optimize_operation(app_id, plan_id, case_id))


def build_plan_detail_data(plan: RequirementPlan) -> PlanDetailData:
    return PlanDetailData(
        app_id=plan.app_id,
        plan_id=plan.plan_id,
        plan_name=display_plan_name(plan),
        source=plan.source,
        version=plan.version,
        case_count=len(plan.cases),
        cases=[build_case_brief_data(case) for case in plan.cases],
    )


def build_plan_list_item(record: IndexedPlanRecord) -> PlanListItemData:
    return PlanListItemData(
        app_id=record.app_id,
        plan_id=record.plan_id,
        plan_name=record.plan_name or record.plan_id,
        source=record.source,
        version=record.version,
        case_count=record.case_count,
        updated_at=record.updated_at,
    )


def build_case_brief_data(case: TestCase) -> CaseBriefData:
    return CaseBriefData(
        case_id=case.case_id,
        title=case.title,
        intent=case.intent,
        is_core_case=case.is_core_case,
        runner_goal=case.runner_goal,
        start_mode=case.start_state.mode,
        start_page_id=case.start_state.page_id,
    )


def build_case_detail_data(
    plan: RequirementPlan,
    case: TestCase,
    *,
    latest_optimize: LatestOptimizeOperationData | None = None,
) -> CaseDetailData:
    budget = case.budget
    return CaseDetailData(
        app_id=plan.app_id,
        plan_id=plan.plan_id,
        plan_source=plan.source,
        plan_version=plan.version,
        case_id=case.case_id,
        title=case.title,
        intent=case.intent,
        preconditions=list(case.preconditions),
        expected=list(case.expected),
        procedure=list(case.procedure),
        post_action=list(case.post_action),
        is_core_case=case.is_core_case,
        runner_goal=case.runner_goal,
        start_mode=case.start_state.mode,
        start_page_id=case.start_state.page_id,
        max_steps=budget.max_steps if budget is not None else None,
        max_seconds=budget.max_seconds if budget is not None else None,
        latest_optimize=latest_optimize,
    )


def build_case_search_item(record: IndexedCaseRecord) -> CaseSearchItemData:
    return CaseSearchItemData(
        app_id=record.app_id,
        plan_id=record.plan_id,
        plan_name=record.plan_name or record.plan_id,
        case_id=record.case_id,
        ordinal=record.ordinal,
        title=record.title,
        intent=record.intent,
        runner_goal=record.runner_goal,
        is_core_case=record.is_core_case,
        start_mode=record.start_mode,
        start_page_id=record.start_page_id,
        max_steps=record.max_steps,
        max_seconds=record.max_seconds,
    )


def display_plan_name(plan: RequirementPlan) -> str:
    return plan.name or plan.plan_id


def enrich_plan_items_with_latest_runs(items: list[PlanListItemData]) -> None:
    refs = [(item.app_id, item.plan_id) for item in items]
    latest_runs = OperationRegistry().list_latest_plan_runs(refs)
    for item in items:
        record = latest_runs.get((item.app_id, item.plan_id))
        if record is None:
            item.latest_run = None
            continue
        item.latest_run = PlanLatestRunSummaryData(
            operation_id=record.operation_id,
            status=record.status,
            verification_verdict=record.verification_verdict,
            created_at=record.created_at,
            started_at=record.started_at,
            finished_at=record.finished_at,
        )
def _find_latest_optimize_operation(app_id: str, plan_id: str, case_id: str) -> LatestOptimizeOperationData | None:
    records = OperationRegistry().list_operations(limit=50, kind="optimize_case")
    for record in records:
        if record.app_id != app_id or record.plan_id != plan_id or record.case_id != case_id:
            continue
        result_json = record.result_json if isinstance(record.result_json, dict) else {}
        patched_fields = result_json.get("patched_fields")
        return LatestOptimizeOperationData(
            operation_id=record.operation_id,
            status=record.status,
            created_at=record.created_at,
            started_at=record.started_at,
            finished_at=record.finished_at,
            summary=result_json.get("summary") if isinstance(result_json.get("summary"), str) else None,
            patched_fields=[item for item in patched_fields if isinstance(item, str) and item] if isinstance(patched_fields, list) else [],
            error_message=record.error_message,
        )
    return None
