from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from munk.scheduling.models import ScheduleRecord, ScheduleRunRecord, ScheduleRunStatus, ScheduleTriggerKind
from munk.services.errors import ScheduleNotFoundError
from munk.services.operations.paths import operations_db_path


class ScheduleRegistry:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or operations_db_path()
        self._initialize()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    app_id TEXT NOT NULL,
                    device_ref TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    trigger_kind TEXT NOT NULL,
                    cron_expr TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    next_run_at TEXT NULL,
                    last_run_at TEXT NULL,
                    last_schedule_run_id TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schedule_runs (
                    schedule_run_id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    operation_id TEXT NULL,
                    error_code TEXT NULL,
                    error_message TEXT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT NULL,
                    triggered_at TEXT NULL,
                    finished_at TEXT NULL,
                    FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id) ON DELETE CASCADE
                );
                """
            )
            self._ensure_column(connection, "schedule_runs", "triggered_at", "TEXT NULL")
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_schedules_enabled_next_run_at
                ON schedules(enabled, next_run_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_schedules_app_id
                ON schedules(app_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_schedule_runs_schedule_id_created_at
                ON schedule_runs(schedule_id, created_at DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_schedule_runs_operation_id
                ON schedule_runs(operation_id)
                """
            )

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_sql: str,
    ) -> None:
        row = connection.execute(
            f"SELECT 1 FROM pragma_table_info('{table_name}') WHERE name = ?",
            (column_name,),
        ).fetchone()
        if row is None:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    def create_schedule(self, record: ScheduleRecord) -> ScheduleRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO schedules (
                    schedule_id, name, app_id, device_ref, timezone, enabled, trigger_kind, cron_expr,
                    request_json, next_run_at, last_run_at, last_schedule_run_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.schedule_id,
                    record.name,
                    record.app_id,
                    record.device_ref,
                    record.timezone,
                    int(record.enabled),
                    record.trigger_kind,
                    record.cron_expr,
                    self._dump_json(record.request_json),
                    record.next_run_at,
                    record.last_run_at,
                    record.last_schedule_run_id,
                    record.created_at,
                    record.updated_at,
                ),
            )
        return self.get_schedule(record.schedule_id)

    def update_schedule(self, record: ScheduleRecord) -> ScheduleRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE schedules
                SET name = ?, app_id = ?, device_ref = ?, timezone = ?, enabled = ?, trigger_kind = ?,
                    cron_expr = ?, request_json = ?, next_run_at = ?, last_run_at = ?, last_schedule_run_id = ?,
                    updated_at = ?
                WHERE schedule_id = ?
                """,
                (
                    record.name,
                    record.app_id,
                    record.device_ref,
                    record.timezone,
                    int(record.enabled),
                    record.trigger_kind,
                    record.cron_expr,
                    self._dump_json(record.request_json),
                    record.next_run_at,
                    record.last_run_at,
                    record.last_schedule_run_id,
                    record.updated_at,
                    record.schedule_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ScheduleNotFoundError(record.schedule_id)
        return self.get_schedule(record.schedule_id)

    def update_schedule_fields(self, schedule_id: str, **fields: Any) -> ScheduleRecord:
        if not fields:
            return self.get_schedule(schedule_id)
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = [self._dump_json(value) if key == "request_json" else value for key, value in fields.items()]
        values.append(schedule_id)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE schedules SET {assignments} WHERE schedule_id = ?",
                values,
            )
            if cursor.rowcount == 0:
                raise ScheduleNotFoundError(schedule_id)
        return self.get_schedule(schedule_id)

    def get_schedule(self, schedule_id: str) -> ScheduleRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM schedules WHERE schedule_id = ?",
                (schedule_id,),
            ).fetchone()
        if row is None:
            raise ScheduleNotFoundError(schedule_id)
        return self._row_to_schedule(row)

    def list_schedules(
        self,
        *,
        enabled: bool | None = None,
        app_id: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ScheduleRecord], int]:
        where_sql = """
            WHERE 1 = 1
        """
        params: list[Any] = []
        if enabled is not None:
            where_sql += " AND enabled = ?"
            params.append(int(enabled))
        if app_id is not None:
            where_sql += " AND app_id = ?"
            params.append(app_id)
        normalized_keyword = keyword.strip() if keyword is not None else ""
        if normalized_keyword:
            keyword_pattern = f"%{normalized_keyword.lower()}%"
            where_sql += """
                AND (
                    LOWER(name) LIKE ?
                    OR LOWER(schedule_id) LIKE ?
                    OR LOWER(device_ref) LIKE ?
                )
            """
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
        sql = """
            SELECT *
            FROM schedules
        """ + where_sql
        count_sql = """
            SELECT COUNT(*) AS count
            FROM schedules
        """ + where_sql
        sql += " ORDER BY datetime(created_at) DESC, schedule_id DESC LIMIT ? OFFSET ?"
        query_params: list[Any] = [*params, limit, offset]
        with self._connect() as connection:
            total_row = connection.execute(count_sql, params).fetchone()
            rows = connection.execute(sql, query_params).fetchall()
        total = int(total_row["count"]) if total_row is not None else 0
        return [self._row_to_schedule(row) for row in rows], total

    def delete_schedule(self, schedule_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM schedules WHERE schedule_id = ?", (schedule_id,))
            if cursor.rowcount == 0:
                raise ScheduleNotFoundError(schedule_id)

    def set_schedule_enabled(
        self,
        schedule_id: str,
        *,
        enabled: bool,
        next_run_at: str | None,
        updated_at: str,
    ) -> ScheduleRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE schedules
                SET enabled = ?, next_run_at = ?, updated_at = ?
                WHERE schedule_id = ?
                """,
                (int(enabled), next_run_at, updated_at, schedule_id),
            )
            if cursor.rowcount == 0:
                raise ScheduleNotFoundError(schedule_id)
        return self.get_schedule(schedule_id)

    def create_schedule_run(self, record: ScheduleRunRecord) -> ScheduleRunRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO schedule_runs (
                    schedule_run_id, schedule_id, scheduled_for, status, operation_id, error_code,
                    error_message, created_at, started_at, triggered_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.schedule_run_id,
                    record.schedule_id,
                    record.scheduled_for,
                    record.status,
                    record.operation_id,
                    record.error_code,
                    record.error_message,
                    record.created_at,
                    record.started_at,
                    record.triggered_at,
                    record.finished_at,
                ),
            )
        return self.get_schedule_run(record.schedule_run_id)

    def update_schedule_run(self, schedule_run_id: str, **fields: Any) -> ScheduleRunRecord:
        if not fields:
            return self.get_schedule_run(schedule_run_id)
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = [fields[key] for key in fields]
        values.append(schedule_run_id)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE schedule_runs SET {assignments} WHERE schedule_run_id = ?",
                values,
            )
            if cursor.rowcount == 0:
                raise ScheduleNotFoundError(f"schedule run not found: {schedule_run_id}")
        return self.get_schedule_run(schedule_run_id)

    def get_schedule_run(self, schedule_run_id: str) -> ScheduleRunRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM schedule_runs WHERE schedule_run_id = ?",
                (schedule_run_id,),
            ).fetchone()
        if row is None:
            raise ScheduleNotFoundError(f"schedule run not found: {schedule_run_id}")
        return self._row_to_schedule_run(row)

    def list_schedule_runs(self, schedule_id: str, *, limit: int = 20) -> list[ScheduleRunRecord]:
        with self._connect() as connection:
            schedule_row = connection.execute(
                "SELECT schedule_id FROM schedules WHERE schedule_id = ?",
                (schedule_id,),
            ).fetchone()
            if schedule_row is None:
                raise ScheduleNotFoundError(schedule_id)
            rows = connection.execute(
                """
                SELECT *
                FROM schedule_runs
                WHERE schedule_id = ?
                ORDER BY datetime(created_at) DESC, schedule_run_id DESC
                LIMIT ?
                """,
                (schedule_id, limit),
            ).fetchall()
        return [self._row_to_schedule_run(row) for row in rows]

    def count_runs_for_schedule(self, schedule_id: str, *, statuses: list[ScheduleRunStatus]) -> int:
        if not statuses:
            return 0
        placeholders = ",".join("?" for _ in statuses)
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM schedule_runs
                WHERE schedule_id = ? AND status IN ({placeholders})
                """,
                [schedule_id, *statuses],
            ).fetchone()
        return int(row["count"]) if row is not None else 0

    def has_schedule_runs_in_statuses(
        self,
        schedule_id: str,
        *,
        statuses: list[ScheduleRunStatus],
    ) -> bool:
        return self.count_runs_for_schedule(schedule_id, statuses=statuses) > 0

    def list_runs_by_statuses(
        self,
        *,
        statuses: list[ScheduleRunStatus],
        limit: int = 100,
    ) -> list[ScheduleRunRecord]:
        if not statuses:
            return []
        placeholders = ",".join("?" for _ in statuses)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM schedule_runs
                WHERE status IN ({placeholders})
                ORDER BY datetime(scheduled_for) ASC, datetime(created_at) ASC, schedule_run_id ASC
                LIMIT ?
                """,
                [*statuses, limit],
            ).fetchall()
        return [self._row_to_schedule_run(row) for row in rows]

    def list_due_schedules(self, *, now_iso: str, limit: int = 100) -> list[ScheduleRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM schedules
                WHERE enabled = 1 AND next_run_at IS NOT NULL AND datetime(next_run_at) <= datetime(?)
                ORDER BY datetime(next_run_at) ASC, datetime(created_at) ASC, schedule_id ASC
                LIMIT ?
                """,
                (now_iso, limit),
            ).fetchall()
        return [self._row_to_schedule(row) for row in rows]

    def find_active_schedule_run(self) -> ScheduleRunRecord | None:
        runs = self.list_runs_by_statuses(statuses=["dispatching", "triggered"], limit=1)
        return runs[0] if runs else None

    def find_active_or_queued_run_for_schedule(self, schedule_id: str) -> ScheduleRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM schedule_runs
                WHERE schedule_id = ? AND status IN ('queued', 'dispatching', 'triggered')
                ORDER BY datetime(created_at) ASC, schedule_run_id ASC
                LIMIT 1
                """,
                (schedule_id,),
            ).fetchone()
        return self._row_to_schedule_run(row) if row is not None else None

    def create_queued_run_if_absent(
        self,
        *,
        schedule_id: str,
        scheduled_for: str,
        schedule_run_id: str,
        created_at: str,
    ) -> ScheduleRunRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            schedule_row = connection.execute(
                "SELECT schedule_id FROM schedules WHERE schedule_id = ?",
                (schedule_id,),
            ).fetchone()
            if schedule_row is None:
                raise ScheduleNotFoundError(schedule_id)
            existing = connection.execute(
                """
                SELECT schedule_run_id
                FROM schedule_runs
                WHERE schedule_id = ? AND status IN ('queued', 'dispatching', 'triggered')
                LIMIT 1
                """,
                (schedule_id,),
            ).fetchone()
            if existing is not None:
                return None
            connection.execute(
                """
                INSERT INTO schedule_runs (
                    schedule_run_id, schedule_id, scheduled_for, status, operation_id, error_code,
                    error_message, created_at, started_at, triggered_at, finished_at
                ) VALUES (?, ?, ?, 'queued', NULL, NULL, NULL, ?, NULL, NULL, NULL)
                """,
                (schedule_run_id, schedule_id, scheduled_for, created_at),
            )
            connection.execute(
                """
                UPDATE schedules
                SET last_schedule_run_id = ?, updated_at = ?
                WHERE schedule_id = ?
                """,
                (schedule_run_id, created_at, schedule_id),
            )
        return self.get_schedule_run(schedule_run_id)

    def claim_next_queued_run(self, *, claimed_at: str) -> ScheduleRunRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = connection.execute(
                """
                SELECT schedule_run_id
                FROM schedule_runs
                WHERE status IN ('dispatching', 'triggered')
                LIMIT 1
                """
            ).fetchone()
            if active is not None:
                return None
            row = connection.execute(
                """
                SELECT schedule_run_id
                FROM schedule_runs
                WHERE status = 'queued'
                ORDER BY datetime(scheduled_for) ASC, datetime(created_at) ASC, schedule_run_id ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            schedule_run_id = str(row["schedule_run_id"])
            connection.execute(
                """
                UPDATE schedule_runs
                SET status = 'dispatching', started_at = ?
                WHERE schedule_run_id = ? AND status = 'queued'
                """,
                (claimed_at, schedule_run_id),
            )
        return self.get_schedule_run(schedule_run_id)

    @staticmethod
    def _dump_json(value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _load_json(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        loaded = json.loads(value)
        return cast(dict[str, Any], loaded if isinstance(loaded, dict) else {})

    def _row_to_schedule(self, row: sqlite3.Row) -> ScheduleRecord:
        return ScheduleRecord(
            schedule_id=str(row["schedule_id"]),
            name=str(row["name"]),
            app_id=str(row["app_id"]),
            device_ref=str(row["device_ref"]),
            timezone=str(row["timezone"]),
            enabled=bool(row["enabled"]),
            trigger_kind=cast(ScheduleTriggerKind, str(row["trigger_kind"])),
            cron_expr=str(row["cron_expr"]),
            request_json=self._load_json(row["request_json"]),
            next_run_at=row["next_run_at"],
            last_run_at=row["last_run_at"],
            last_schedule_run_id=row["last_schedule_run_id"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _row_to_schedule_run(row: sqlite3.Row) -> ScheduleRunRecord:
        return ScheduleRunRecord(
            schedule_run_id=str(row["schedule_run_id"]),
            schedule_id=str(row["schedule_id"]),
            scheduled_for=str(row["scheduled_for"]),
            status=cast(ScheduleRunStatus, str(row["status"])),
            operation_id=row["operation_id"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=str(row["created_at"]),
            started_at=row["started_at"],
            triggered_at=row["triggered_at"],
            finished_at=row["finished_at"],
        )
