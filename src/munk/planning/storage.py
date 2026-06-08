from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from munk.paths import assets_root
from munk.planning.index_store import PlanCaseIndexStore
from munk.planning.models import PlanSnapshot, RequirementPlan
from munk.testing import TestCase


def _resolve_root_dir(root_dir: Path | None) -> Path:
    return root_dir or assets_root()


class CoreCaseRegistry:
    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = _resolve_root_dir(root_dir)
        self.apps_dir = self.root_dir / "apps"

    def load(self, app_id: str) -> dict[str, Any]:
        cases_path = self.apps_dir / app_id / "core_cases.yaml"
        if not cases_path.exists():
            return {"cases": []}
        with cases_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if data else {"cases": []}

    def save(self, app_id: str, data: dict[str, Any]) -> None:
        app_dir = self.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        cases_path = app_dir / "core_cases.yaml"
        with cases_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)

    def apply_to_cases(self, app_id: str, cases: list[TestCase]) -> list[TestCase]:
        data = self.load(app_id)
        explicit_ids = {
            str(item.get("case_id")).strip()
            for item in data.get("cases", [])
            if isinstance(item, dict) and isinstance(item.get("case_id"), str)
        }

        updated_cases: list[TestCase] = []
        for case in cases:
            is_core = case.case_id in explicit_ids
            if is_core == case.is_core_case:
                updated_cases.append(case)
                continue
            updated_cases.append(case.model_copy(update={"is_core_case": is_core}))
        return updated_cases


class PlanStore:
    def __init__(
        self,
        root_dir: Path | None = None,
        *,
        index_store: PlanCaseIndexStore | None = None,
    ) -> None:
        self.root_dir = _resolve_root_dir(root_dir)
        self.plans_dir = self.root_dir / "plans"
        self._index_store = index_store

    def save(self, plan: RequirementPlan) -> Path:
        app_dir = self.plans_dir / plan.app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        plan_path = app_dir / f"{plan.plan_id}.json"
        if plan_path.exists():
            raise FileExistsError(f"RequirementPlan already exists: {plan_path}")
        with plan_path.open("w", encoding="utf-8") as f:
            json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)
        self._resolve_index_store().upsert_plan(plan, plan_path=plan_path)
        return plan_path

    def load(self, app_id: str, plan_id: str) -> RequirementPlan:
        plan_path = self.plans_dir / app_id / f"{plan_id}.json"
        if not plan_path.exists():
            raise FileNotFoundError(f"RequirementPlan not found: {plan_path}")
        with plan_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return RequirementPlan(**data)

    def export_snapshot(self, plan: RequirementPlan) -> Path:
        snapshot = PlanSnapshot(
            snapshot_id=f"{plan.plan_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            source_plan_id=plan.plan_id,
            exported_at=datetime.now(timezone.utc).isoformat(),
            app_id=plan.app_id,
            plan_id=plan.plan_id,
            source=plan.source,
            version=plan.version,
            cases=plan.cases,
        )
        snapshot_dir = self.plans_dir / plan.app_id / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{snapshot.snapshot_id}.json"
        with snapshot_path.open("w", encoding="utf-8") as f:
            json.dump(snapshot.model_dump(), f, ensure_ascii=False, indent=2)
        return snapshot_path

    def load_snapshot(self, app_id: str, snapshot_id: str) -> PlanSnapshot:
        snapshot_path = self.plans_dir / app_id / "snapshots" / f"{snapshot_id}.json"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"PlanSnapshot not found: {snapshot_path}")
        with snapshot_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return PlanSnapshot(**data)

    def iter_plan_paths(self) -> list[Path]:
        if not self.plans_dir.exists():
            return []
        return [
            path
            for path in self.plans_dir.glob("*/*.json")
            if path.parent.name != "snapshots"
        ]

    def iter_plans(self) -> list[tuple[Path, RequirementPlan]]:
        return [
            (path, RequirementPlan(**json.loads(path.read_text(encoding="utf-8"))))
            for path in self.iter_plan_paths()
        ]

    def _resolve_index_store(self) -> PlanCaseIndexStore:
        if self._index_store is None:
            self._index_store = PlanCaseIndexStore(self.root_dir)
        return self._index_store
