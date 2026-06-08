from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from munk.paths import assets_root
from munk.planning.models import RequirementPlan

if TYPE_CHECKING:
    from munk.planning.storage import PlanStore


def _resolve_root_dir(root_dir: Path | None) -> Path:
    return root_dir or assets_root()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class IndexSummary:
    plan_count: int
    case_count: int


@dataclass(frozen=True)
class RebuildSummary:
    plan_count: int
    case_count: int
    db_path: Path


@dataclass(frozen=True)
class IndexedCaseRecord:
    app_id: str
    plan_id: str
    plan_name: str | None
    case_id: str
    ordinal: int
    title: str
    intent: str
    runner_goal: str
    is_core_case: bool
    start_mode: str
    start_page_id: str | None
    max_steps: int | None
    max_seconds: float | None


@dataclass(frozen=True)
class IndexedPlanRecord:
    app_id: str
    plan_id: str
    plan_name: str | None
    source: str
    version: str
    case_count: int
    updated_at: str


class PlanCaseIndexStore:
    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = _resolve_root_dir(root_dir)
        self.db_path = self.root_dir / "plans" / "_index" / "plan_case_index.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        rebuild_from_store = self.db_path.exists() and not self._schema_is_current()
        if rebuild_from_store:
            self.db_path.unlink()
        self._initialize()
        if rebuild_from_store:
            from munk.planning.storage import PlanStore

            self.rebuild_from_plan_store(PlanStore(self.root_dir))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    app_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    name TEXT NULL,
                    source TEXT NOT NULL,
                    version TEXT NOT NULL,
                    plan_path TEXT NOT NULL,
                    snapshot_path TEXT NULL,
                    case_count INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(app_id, plan_id)
                );

                CREATE TABLE IF NOT EXISTS cases (
                    app_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    runner_goal TEXT NOT NULL,
                    is_core_case INTEGER NOT NULL,
                    start_mode TEXT NOT NULL,
                    start_page_id TEXT NULL,
                    has_budget INTEGER NOT NULL,
                    max_steps INTEGER NULL,
                    max_seconds REAL NULL,
                    expected_json TEXT NOT NULL,
                    preconditions_json TEXT NOT NULL,
                    procedure_json TEXT NOT NULL,
                    post_action_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(app_id, plan_id, case_id),
                    FOREIGN KEY(app_id, plan_id) REFERENCES plans(app_id, plan_id) ON DELETE CASCADE
                );
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plan_case_cases_app_plan
                ON cases(app_id, plan_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plan_case_cases_app_case
                ON cases(app_id, case_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plan_case_cases_core
                ON cases(is_core_case)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plan_case_cases_start_mode
                ON cases(start_mode)
                """
            )

    def upsert_plan(
        self,
        plan: RequirementPlan,
        *,
        plan_path: Path,
        snapshot_path: Path | None = None,
    ) -> None:
        timestamp = _now_iso()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM cases WHERE app_id = ? AND plan_id = ?",
                (plan.app_id, plan.plan_id),
            )
            connection.execute(
                """
                INSERT INTO plans (
                    app_id, plan_id, name, source, version, plan_path, snapshot_path, case_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_id, plan_id) DO UPDATE SET
                    name = excluded.name,
                    source = excluded.source,
                    version = excluded.version,
                    plan_path = excluded.plan_path,
                    snapshot_path = excluded.snapshot_path,
                    case_count = excluded.case_count,
                    updated_at = excluded.updated_at
                """,
                (
                    plan.app_id,
                    plan.plan_id,
                    plan.name,
                    plan.source,
                    plan.version,
                    str(plan_path),
                    None if snapshot_path is None else str(snapshot_path),
                    len(plan.cases),
                    timestamp,
                ),
            )
            for ordinal, case in enumerate(plan.cases):
                budget = case.budget
                connection.execute(
                    """
                    INSERT INTO cases (
                        app_id, plan_id, case_id, ordinal, title, intent, runner_goal, is_core_case,
                        start_mode, start_page_id, has_budget, max_steps, max_seconds,
                        expected_json, preconditions_json, procedure_json, post_action_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.app_id,
                        plan.plan_id,
                        case.case_id,
                        ordinal,
                        case.title,
                        case.intent,
                        case.runner_goal,
                        int(case.is_core_case),
                        case.start_state.mode,
                        case.start_state.page_id,
                        int(budget is not None),
                        None if budget is None else budget.max_steps,
                        None if budget is None else budget.max_seconds,
                        json.dumps(case.expected, ensure_ascii=False),
                        json.dumps(case.preconditions, ensure_ascii=False),
                        json.dumps(case.procedure, ensure_ascii=False),
                        json.dumps(case.post_action, ensure_ascii=False),
                        timestamp,
                    ),
                )

    def remove_plan(self, *, app_id: str, plan_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM plans WHERE app_id = ? AND plan_id = ?",
                (app_id, plan_id),
            )

    def search_cases(
        self,
        *,
        app_id: str | None = None,
        plan_id: str | None = None,
        case_id: str | None = None,
        query: str | None = None,
        is_core_case: bool | None = None,
        start_mode: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[IndexedCaseRecord], int]:
        self._self_heal_if_needed()
        sql = """
            SELECT
                cases.app_id,
                cases.plan_id,
                plans.name AS plan_name,
                cases.case_id,
                cases.ordinal,
                cases.title,
                cases.intent,
                cases.runner_goal,
                cases.is_core_case,
                cases.start_mode,
                cases.start_page_id,
                cases.max_steps,
                cases.max_seconds
            FROM cases
            JOIN plans
              ON plans.app_id = cases.app_id
             AND plans.plan_id = cases.plan_id
            WHERE 1 = 1
        """
        params: list[object] = []
        if app_id is not None:
            sql += " AND cases.app_id = ?"
            params.append(app_id)
        if plan_id is not None:
            sql += " AND cases.plan_id = ?"
            params.append(plan_id)
        if case_id is not None:
            sql += " AND cases.case_id = ?"
            params.append(case_id)
        if query is not None and query.strip():
            normalized_query = f"%{query.strip().lower()}%"
            sql += """
                AND (
                    LOWER(cases.title) LIKE ?
                    OR LOWER(cases.intent) LIKE ?
                    OR LOWER(cases.runner_goal) LIKE ?
                    OR LOWER(cases.case_id) LIKE ?
                    OR LOWER(COALESCE(plans.name, '')) LIKE ?
                    OR LOWER(cases.plan_id) LIKE ?
                )
            """
            params.extend([normalized_query] * 6)
        if is_core_case is not None:
            sql += " AND cases.is_core_case = ?"
            params.append(int(is_core_case))
        if start_mode is not None:
            sql += " AND cases.start_mode = ?"
            params.append(start_mode)
        with self._connect() as connection:
            total_row = connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM ({sql}) filtered_cases
                """,
                params,
            ).fetchone()
        sql += """
            ORDER BY datetime(plans.updated_at) DESC, cases.app_id ASC, cases.plan_id ASC, cases.ordinal ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        items = [
            IndexedCaseRecord(
                app_id=str(row["app_id"]),
                plan_id=str(row["plan_id"]),
                plan_name=str(row["plan_name"]) if row["plan_name"] is not None else None,
                case_id=str(row["case_id"]),
                ordinal=int(row["ordinal"]),
                title=str(row["title"]),
                intent=str(row["intent"]),
                runner_goal=str(row["runner_goal"]),
                is_core_case=bool(row["is_core_case"]),
                start_mode=str(row["start_mode"]),
                start_page_id=str(row["start_page_id"]) if row["start_page_id"] is not None else None,
                max_steps=int(row["max_steps"]) if row["max_steps"] is not None else None,
                max_seconds=float(row["max_seconds"]) if row["max_seconds"] is not None else None,
            )
            for row in rows
        ]
        total = int(total_row["total"]) if total_row is not None else 0
        return items, total

    def list_plans_page(
        self,
        *,
        app_id: str | None = None,
        source: str | None = None,
        case_count_mode: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[IndexedPlanRecord], int]:
        self._self_heal_if_needed()
        sql = """
            SELECT
                app_id,
                plan_id,
                name,
                source,
                version,
                case_count,
                updated_at
            FROM plans
            WHERE 1 = 1
        """
        params: list[object] = []
        if app_id is not None:
            sql += " AND app_id = ?"
            params.append(app_id)
        if source is not None:
            sql += " AND source = ?"
            params.append(source)
        if case_count_mode == "single":
            sql += " AND case_count = 1"
        elif case_count_mode == "multi":
            sql += " AND case_count > 1"
        with self._connect() as connection:
            total_row = connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM ({sql}) filtered_plans
                """,
                params,
            ).fetchone()
        sql += """
            ORDER BY datetime(updated_at) DESC, app_id ASC, plan_id ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        items = [
            IndexedPlanRecord(
                app_id=str(row["app_id"]),
                plan_id=str(row["plan_id"]),
                plan_name=str(row["name"]) if row["name"] is not None else None,
                source=str(row["source"]),
                version=str(row["version"]),
                case_count=int(row["case_count"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]
        total = int(total_row["total"]) if total_row is not None else 0
        return items, total

    def summary(self) -> IndexSummary:
        self._self_heal_if_needed()
        return self._summary_unchecked()

    def _summary_unchecked(self) -> IndexSummary:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM plans) AS plan_count,
                    (SELECT COUNT(*) FROM cases) AS case_count
                """
            ).fetchone()
        if row is None:
            return IndexSummary(plan_count=0, case_count=0)
        return IndexSummary(
            plan_count=int(row["plan_count"] or 0),
            case_count=int(row["case_count"] or 0),
        )

    def rebuild_from_plan_store(self, plan_store: PlanStore) -> RebuildSummary:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM cases")
            connection.execute("DELETE FROM plans")
        for plan_path, plan in plan_store.iter_plans():
            self.upsert_plan(plan, plan_path=plan_path)
        summary = self._summary_unchecked()
        return RebuildSummary(
            plan_count=summary.plan_count,
            case_count=summary.case_count,
            db_path=self.db_path,
        )

    def _self_heal_if_needed(self) -> None:
        from munk.planning.storage import PlanStore

        plan_store = PlanStore(self.root_dir)
        plan_paths = plan_store.iter_plan_paths()
        indexed_plans = self._indexed_plan_rows()
        actual_path_strings = {str(path) for path in plan_paths}
        indexed_path_strings = {path for path, _updated_at in indexed_plans}
        if actual_path_strings != indexed_path_strings:
            self.rebuild_from_plan_store(plan_store)
            return
        for path, indexed_updated_at in indexed_plans:
            plan_path = Path(path)
            if not plan_path.exists():
                self.rebuild_from_plan_store(plan_store)
                return
            indexed_timestamp = datetime.fromisoformat(indexed_updated_at).timestamp()
            if plan_path.stat().st_mtime > indexed_timestamp:
                self.rebuild_from_plan_store(plan_store)
                return

    def _indexed_plan_rows(self) -> list[tuple[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT plan_path, updated_at
                FROM plans
                """
            ).fetchall()
        return [
            (str(row["plan_path"]), str(row["updated_at"]))
            for row in rows
        ]

    def _schema_is_current(self) -> bool:
        with self._connect() as connection:
            plan_rows = connection.execute("PRAGMA table_info(plans)").fetchall()
            case_rows = connection.execute("PRAGMA table_info(cases)").fetchall()
        if not plan_rows:
            return True
        plan_columns = {str(row["name"]) for row in plan_rows}
        case_columns = {str(row["name"]) for row in case_rows}
        return "name" in plan_columns and "post_action_json" in case_columns
