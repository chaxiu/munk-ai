from __future__ import annotations

import sqlite3


def initialize_registry_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS operations (
            operation_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            status TEXT NOT NULL,
            verification_verdict TEXT NULL,
            app_id TEXT NULL,
            plan_id TEXT NULL,
            case_id TEXT NULL,
            parent_operation_id TEXT NULL,
            batch_id TEXT NULL,
            position_index INTEGER NULL,
            position_label TEXT NULL,
            request_json TEXT NOT NULL,
            result_json TEXT NULL,
            artifacts_json TEXT NOT NULL,
            progress_json TEXT NOT NULL,
            projected_run_type TEXT NULL,
            projected_platform TEXT NULL,
            projected_title TEXT NULL,
            projected_source_recording_id TEXT NULL,
            result_path TEXT NULL,
            pid INTEGER NULL,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            device_ref TEXT NULL,
            resource_scope TEXT NOT NULL DEFAULT 'none',
            conflict_reason TEXT NULL,
            error_code TEXT NULL,
            error_message TEXT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT NULL,
            finished_at TEXT NULL
        );

        CREATE TABLE IF NOT EXISTS operation_events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NULL,
            data_json TEXT NOT NULL,
            FOREIGN KEY(operation_id) REFERENCES operations(operation_id)
        );

        CREATE TABLE IF NOT EXISTS operation_resource_claims (
            claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_type TEXT NOT NULL,
            resource_key TEXT NOT NULL,
            operation_id TEXT NOT NULL,
            claimed_at TEXT NOT NULL,
            released_at TEXT NULL,
            FOREIGN KEY(operation_id) REFERENCES operations(operation_id)
        );
        """
    )
    ensure_column(connection, "operations", "device_ref", "TEXT NULL")
    ensure_column(connection, "operations", "resource_scope", "TEXT NOT NULL DEFAULT 'none'")
    ensure_column(connection, "operations", "conflict_reason", "TEXT NULL")
    ensure_column(connection, "operations", "parent_operation_id", "TEXT NULL")
    ensure_column(connection, "operations", "batch_id", "TEXT NULL")
    ensure_column(connection, "operations", "position_index", "INTEGER NULL")
    ensure_column(connection, "operations", "position_label", "TEXT NULL")
    ensure_column(connection, "operations", "projected_run_type", "TEXT NULL")
    ensure_column(connection, "operations", "projected_platform", "TEXT NULL")
    ensure_column(connection, "operations", "projected_title", "TEXT NULL")
    ensure_column(connection, "operations", "projected_source_recording_id", "TEXT NULL")
    ensure_column(connection, "operations", "result_path", "TEXT NULL")
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_events_operation_id_seq
        ON operation_events(operation_id, seq)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operations_parent_operation_id
        ON operations(parent_operation_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operations_batch_id
        ON operations(batch_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operations_parent_position
        ON operations(parent_operation_id, position_index)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operations_created_at
        ON operations(created_at DESC, operation_id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operations_kind_created_at
        ON operations(kind, created_at DESC, operation_id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operations_run_center
        ON operations(projected_run_type, created_at DESC, operation_id DESC)
        WHERE projected_run_type IS NOT NULL
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operations_app_plan_kind_created
        ON operations(app_id, plan_id, kind, created_at DESC, operation_id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_claims_operation_id
        ON operation_resource_claims(operation_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_claims_resource
        ON operation_resource_claims(resource_type, resource_key)
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_operation_claims_active_unique
        ON operation_resource_claims(resource_type, resource_key)
        WHERE released_at IS NULL
        """
    )


def ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {str(row["name"]) for row in rows}
    if column_name in existing:
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
