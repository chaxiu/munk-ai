from __future__ import annotations

import sqlite3


def initialize_registry_schema(connection: sqlite3.Connection) -> None:
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
    ensure_column(connection, "schedule_runs", "triggered_at", "TEXT NULL")
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


def ensure_column(
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
