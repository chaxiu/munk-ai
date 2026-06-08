from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from munk.app_assets.models import AppProfile
from munk.app_assets.storage import AppRegistry
from munk.planning.index_store import PlanCaseIndexStore
from munk.planning.storage import PlanStore


@dataclass(frozen=True)
class AppUsageSummary:
    plan_count: int
    case_count: int


@dataclass(frozen=True)
class AppDetail:
    profile: AppProfile
    introduction_markdown: str
    app_knowledge_content: str | None
    app_knowledge_exists: bool
    usage: AppUsageSummary


class AppAssetService:
    def __init__(
        self,
        root_dir: Path | None = None,
        *,
        app_registry: AppRegistry | None = None,
        plan_store: PlanStore | None = None,
        index_store: PlanCaseIndexStore | None = None,
    ) -> None:
        self._app_registry = app_registry or AppRegistry(root_dir)
        root = self._app_registry.root_dir if root_dir is None else root_dir
        self._plan_store = plan_store or PlanStore(root)
        self._index_store = index_store or PlanCaseIndexStore(root)

    @property
    def app_registry(self) -> AppRegistry:
        return self._app_registry

    def list_profiles(self, *, platform: str | None = None) -> list[AppProfile]:
        items = self._app_registry.list()
        if platform is None:
            return items
        return [item for item in items if item.platform == platform]

    def get_app_usage(self, app_id: str) -> AppUsageSummary:
        plan_count = sum(1 for _path, plan in self._plan_store.iter_plans() if plan.app_id == app_id)
        _items, total = self._index_store.search_cases(app_id=app_id, limit=10_000)
        case_count = total
        return AppUsageSummary(plan_count=plan_count, case_count=case_count)

    def build_app_detail(self, app_id: str) -> AppDetail:
        profile = self._app_registry.load(app_id)
        introduction_markdown = self._app_registry.load_introduction(
            app_id,
            ref=profile.app_introduction_ref,
        )
        knowledge_path = self._app_registry.knowledge_path(
            app_id,
            ref=profile.app_knowledge_ref,
        )
        app_knowledge_exists = knowledge_path.exists()
        app_knowledge_content = None
        if app_knowledge_exists:
            app_knowledge_content = self._app_registry.load_knowledge(
                app_id,
                ref=profile.app_knowledge_ref,
            )
        usage = self.get_app_usage(app_id)
        return AppDetail(
            profile=profile,
            introduction_markdown=introduction_markdown,
            app_knowledge_content=app_knowledge_content,
            app_knowledge_exists=app_knowledge_exists,
            usage=usage,
        )

    def assert_app_deletable(self, app_id: str) -> None:
        usage = self.get_app_usage(app_id)
        if usage.plan_count > 0 or usage.case_count > 0:
            raise ValueError(
                f"app '{app_id}' is still referenced by {usage.plan_count} plans and {usage.case_count} cases"
            )
