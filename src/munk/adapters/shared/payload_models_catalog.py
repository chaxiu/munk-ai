from __future__ import annotations

from pydantic import BaseModel, Field

from munk.app import AppTarget
from munk.app_assets.models import AppProfile
from munk.testing import AiGuidance


class AppListItemData(BaseModel):
    app_id: str
    app_name: str | None = None
    platform: str
    entry_identity: str | None = None
    introduction_exists: bool = True
    plan_count: int = 0
    case_count: int = 0


class AppListData(BaseModel):
    items: list[AppListItemData] = Field(default_factory=list)


class AppDetailData(BaseModel):
    profile: AppProfile
    introduction_markdown: str
    app_knowledge_content: str | None = None
    app_knowledge_exists: bool = False
    app_target: AppTarget
    plan_count: int = 0
    case_count: int = 0


class DashboardSummaryData(BaseModel):
    plan_count: int = 0
    case_count: int = 0
    recent_run_count: int = 0


class PlanLatestRunSummaryData(BaseModel):
    operation_id: str
    status: str
    verification_verdict: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class PlanListItemData(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    source: str
    version: str
    case_count: int = 0
    updated_at: str
    latest_run: PlanLatestRunSummaryData | None = None


class PlanListData(BaseModel):
    items: list[PlanListItemData] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


class CaseBriefData(BaseModel):
    case_id: str
    title: str
    intent: str
    is_core_case: bool
    runner_goal: str
    start_mode: str
    start_page_id: str | None = None


class PlanDetailData(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    source: str
    version: str
    case_count: int = 0
    cases: list[CaseBriefData] = Field(default_factory=list)


class LatestOptimizeOperationData(BaseModel):
    operation_id: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    summary: str | None = None
    patched_fields: list[str] = Field(default_factory=list)
    error_message: str | None = None


class CaseDetailData(BaseModel):
    app_id: str
    plan_id: str
    plan_source: str
    plan_version: str
    case_id: str
    title: str
    intent: str
    preconditions: list[str] = Field(default_factory=list)
    expected: list[str] = Field(default_factory=list)
    procedure: list[str] = Field(default_factory=list)
    post_action: list[str] = Field(default_factory=list)
    is_core_case: bool
    runner_goal: str
    start_mode: str
    start_page_id: str | None = None
    max_steps: int | None = None
    max_seconds: float | None = None
    ai_guidance: AiGuidance | None = None
    latest_optimize: LatestOptimizeOperationData | None = None


class CaseSearchItemData(BaseModel):
    app_id: str
    plan_id: str
    plan_name: str | None = None
    case_id: str
    ordinal: int
    title: str
    intent: str
    runner_goal: str
    is_core_case: bool
    start_mode: str
    start_page_id: str | None = None
    max_steps: int | None = None
    max_seconds: float | None = None


class CaseSearchData(BaseModel):
    items: list[CaseSearchItemData] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0
