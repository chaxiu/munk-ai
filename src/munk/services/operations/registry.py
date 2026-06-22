from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from munk.services.errors import DeviceConflictError, OperationNotFoundError
from munk.services.operations.models import (
    CleanupClaimResult,
    DeviceClaimConflict,
    DeviceClaimRequest,
    OperationEventRecord,
    OperationKind,
    OperationRecord,
    OperationStatus,
    now_iso,
)
from munk.services.operations.paths import operations_db_path
from munk.services.operations.payloads import with_projected_fields
from munk.services.operations.registry_claims import (
    cleanup_stale_claims_locked,
    find_active_device_conflict_locked,
    find_active_device_conflicts_locked,
    insert_claim_locked,
)
from munk.services.operations.registry_projections import (
    platform_sql_expr,
    run_type_sql_expr,
    should_refresh_projection,
)
from munk.services.operations.registry_queries import (
    build_latest_plan_runs_query,
    build_list_operations_page_query,
)
from munk.services.operations.registry_schema import initialize_registry_schema
from munk.services.operations.registry_serialization import dump_json, load_json, row_to_operation

_QUEUE_STARTUP_GRACE_SECONDS = 30
_logger = logging.getLogger(__name__)


class OperationRegistry:
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
        try:
            connection.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            _logger.warning(
                "failed to enable WAL for operations db %s; falling back to default journal mode",
                self._db_path,
            )
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            initialize_registry_schema(connection)

    def create_operation(self, record: OperationRecord) -> OperationRecord:
        with self._connect() as connection:
            self._insert_operation_locked(connection, record)
        return self.get_operation(record.operation_id)

    def create_operation_with_claim(
        self,
        record: OperationRecord,
        *,
        claim_request: DeviceClaimRequest | None,
    ) -> OperationRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if claim_request is not None and claim_request.resource_scope != "none":
                self._cleanup_stale_claims_locked(
                    connection,
                    claim_request=claim_request,
                    queue_startup_grace_seconds=_QUEUE_STARTUP_GRACE_SECONDS,
                )
                conflict = self._find_active_device_conflict_locked(connection, claim_request)
                if conflict is not None:
                    raise DeviceConflictError(
                        requested_device_ref=conflict.requested_device_ref,
                        blocking_operation_id=conflict.blocking_operation_id,
                        blocking_kind=conflict.blocking_kind,
                        blocking_status=conflict.blocking_status,
                        blocking_device_ref=conflict.blocking_device_ref,
                        reason=conflict.reason,
                    )
            self._insert_operation_locked(connection, record)
            if claim_request is not None and claim_request.resource_scope != "none":
                self._insert_claim_locked(
                    connection,
                    operation_id=record.operation_id,
                    claim_request=claim_request,
                    claimed_at=record.created_at,
                )
        return self.get_operation(record.operation_id)

    def get_operation(self, operation_id: str) -> OperationRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            raise OperationNotFoundError(f"operation not found: {operation_id}")
        return self._row_to_operation(row)

    def list_operations(
        self,
        *,
        limit: int = 20,
        status: OperationStatus | None = None,
        kind: OperationKind | None = None,
        device_ref: str | None = None,
        surface: str | None = None,
        verification_verdict: str | None = None,
        platform: str | None = None,
        query: str | None = None,
    ) -> list[OperationRecord]:
        items, _total = self.list_operations_page(
            limit=limit,
            offset=0,
            status=status,
            kind=kind,
            device_ref=device_ref,
            surface=surface,
            verification_verdict=verification_verdict,
            platform=platform,
            query=query,
        )
        return items

    def list_operations_page(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: OperationStatus | None = None,
        kind: OperationKind | None = None,
        device_ref: str | None = None,
        surface: str | None = None,
        verification_verdict: str | None = None,
        platform: str | None = None,
        query: str | None = None,
        run_type: str | None = None,
    ) -> tuple[list[OperationRecord], int]:
        run_type_expr = run_type_sql_expr()
        platform_expr = platform_sql_expr()
        sql, params = build_list_operations_page_query(
            status=status,
            kind=kind,
            device_ref=device_ref,
            surface=surface,
            verification_verdict=verification_verdict,
            platform=platform,
            query=query,
            run_type=run_type,
            run_type_expr=run_type_expr,
            platform_expr=platform_expr,
        )
        with self._connect() as connection:
            total_row = connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM ({sql}) filtered_operations
                """,
                params,
            ).fetchone()
        sql += """
            ORDER BY datetime(created_at) DESC, operation_id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        records = [self._row_to_operation(row) for row in rows]
        total = int(total_row["total"]) if total_row is not None else 0
        return records, total

    def list_latest_plan_runs(self, plan_refs: list[tuple[str, str]]) -> dict[tuple[str, str], OperationRecord]:
        sql, params, unique_refs = build_latest_plan_runs_query(plan_refs)
        if sql is None:
            return {}
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        latest_runs: dict[tuple[str, str], OperationRecord] = {}
        seen_refs = set(unique_refs)
        for row in rows:
            record = self._row_to_operation(row)
            key = (record.app_id or "", record.plan_id or "")
            if key not in seen_refs or key in latest_runs:
                continue
            latest_runs[key] = record
            if len(latest_runs) == len(unique_refs):
                break
        return latest_runs

    def update_operation(self, operation_id: str, **fields: Any) -> OperationRecord:
        if not fields:
            return self.get_operation(operation_id)
        if should_refresh_projection(fields):
            current = self.get_operation(operation_id)
            projected = with_projected_fields(current.model_copy(update=fields))
            fields = {
                **fields,
                "projected_run_type": projected.projected_run_type,
                "projected_platform": projected.projected_platform,
                "projected_title": projected.projected_title,
                "projected_source_recording_id": projected.projected_source_recording_id,
            }
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            if key in {"request_json", "result_json", "artifacts_json", "progress_json"}:
                values.append(self._dump_json(value))
            elif key == "cancel_requested":
                values.append(int(bool(value)))
            else:
                values.append(value)
        values.append(operation_id)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE operations SET {', '.join(assignments)} WHERE operation_id = ?",
                values,
            )
            if cursor.rowcount == 0:
                raise OperationNotFoundError(f"operation not found: {operation_id}")
        return self.get_operation(operation_id)

    def release_claims(self, operation_id: str, *, released_at: str | None = None) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE operation_resource_claims
                SET released_at = ?
                WHERE operation_id = ? AND released_at IS NULL
                """,
                (released_at or now_iso(), operation_id),
            )
            return int(cursor.rowcount or 0)

    def find_active_device_conflicts(self, claim_request: DeviceClaimRequest) -> list[DeviceClaimConflict]:
        with self._connect() as connection:
            return self._find_active_device_conflicts_locked(connection, claim_request)

    def cleanup_stale_claims(
        self,
        *,
        claim_request: DeviceClaimRequest | None = None,
        queue_startup_grace_seconds: int = _QUEUE_STARTUP_GRACE_SECONDS,
    ) -> list[CleanupClaimResult]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return self._cleanup_stale_claims_locked(
                connection,
                claim_request=claim_request,
                queue_startup_grace_seconds=queue_startup_grace_seconds,
            )

    def cleanup_stale_claims_for_request(self, claim_request: DeviceClaimRequest) -> list[CleanupClaimResult]:
        return self.cleanup_stale_claims(claim_request=claim_request)

    def append_event(
        self,
        operation_id: str,
        *,
        timestamp: str,
        event_type: str,
        message: str | None,
        data_json: dict[str, Any] | None = None,
    ) -> OperationEventRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO operation_events (operation_id, timestamp, event_type, message, data_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    timestamp,
                    event_type,
                    message,
                    self._dump_json(data_json or {}),
                ),
            )
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("failed to append operation event")
            seq = int(row_id)
        return OperationEventRecord(
            seq=seq,
            operation_id=operation_id,
            timestamp=timestamp,
            event_type=event_type,
            message=message,
            data_json=data_json or {},
        )

    def list_events(
        self,
        operation_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[OperationEventRecord]:
        self.get_operation(operation_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT seq, operation_id, timestamp, event_type, message, data_json
                FROM operation_events
                WHERE operation_id = ? AND seq > ?
                ORDER BY seq ASC
                LIMIT ?
                """,
                (operation_id, after_seq, limit),
            ).fetchall()
        return [
            OperationEventRecord(
                seq=int(row["seq"]),
                operation_id=str(row["operation_id"]),
                timestamp=str(row["timestamp"]),
                event_type=str(row["event_type"]),
                message=str(row["message"]) if row["message"] is not None else None,
                data_json=self._load_json(row["data_json"]),
            )
            for row in rows
        ]

    def list_child_operations(self, parent_operation_id: str) -> list[OperationRecord]:
        self.get_operation(parent_operation_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM operations
                WHERE parent_operation_id = ?
                ORDER BY
                    CASE WHEN position_index IS NULL THEN 1 ELSE 0 END ASC,
                    position_index ASC,
                    datetime(created_at) ASC,
                    operation_id ASC
                """,
                (parent_operation_id,),
            ).fetchall()
        return [self._row_to_operation(row) for row in rows]

    def count_child_operations(self, parent_operation_id: str) -> int:
        self.get_operation(parent_operation_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS child_count FROM operations WHERE parent_operation_id = ?",
                (parent_operation_id,),
            ).fetchone()
        return int(row["child_count"]) if row is not None else 0

    def request_cancel(self, operation_id: str) -> OperationRecord:
        return self.update_operation(operation_id, cancel_requested=True)

    @staticmethod
    def _dump_json(value: Any) -> str:
        return dump_json(value)

    @staticmethod
    def _load_json(value: Any) -> Any:
        return load_json(value)

    def _insert_operation_locked(self, connection: sqlite3.Connection, record: OperationRecord) -> None:
        connection.execute(
            """
            INSERT INTO operations (
                operation_id, kind, status, verification_verdict, app_id, plan_id, case_id,
                parent_operation_id, batch_id, position_index, position_label,
                request_json, result_json, artifacts_json, progress_json,
                projected_run_type, projected_platform, projected_title, projected_source_recording_id,
                pid, cancel_requested,
                device_ref, resource_scope, conflict_reason,
                error_code, error_message, created_at, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.operation_id,
                record.kind,
                record.status,
                record.verification_verdict,
                record.app_id,
                record.plan_id,
                record.case_id,
                record.parent_operation_id,
                record.batch_id,
                record.position_index,
                record.position_label,
                self._dump_json(record.request_json),
                self._dump_json(record.result_json),
                self._dump_json(record.artifacts_json),
                self._dump_json(record.progress_json),
                record.projected_run_type,
                record.projected_platform,
                record.projected_title,
                record.projected_source_recording_id,
                record.pid,
                int(record.cancel_requested),
                record.device_ref,
                record.resource_scope,
                record.conflict_reason,
                record.error_code,
                record.error_message,
                record.created_at,
                record.started_at,
                record.finished_at,
            ),
        )

    def _insert_claim_locked(
        self,
        connection: sqlite3.Connection,
        *,
        operation_id: str,
        claim_request: DeviceClaimRequest,
        claimed_at: str,
    ) -> None:
        insert_claim_locked(
            connection,
            operation_id=operation_id,
            claim_request=claim_request,
            claimed_at=claimed_at,
        )

    def _find_active_device_conflicts_locked(
        self,
        connection: sqlite3.Connection,
        claim_request: DeviceClaimRequest,
    ) -> list[DeviceClaimConflict]:
        return find_active_device_conflicts_locked(connection, claim_request)

    def _find_active_device_conflict_locked(
        self,
        connection: sqlite3.Connection,
        claim_request: DeviceClaimRequest,
    ) -> DeviceClaimConflict | None:
        return find_active_device_conflict_locked(connection, claim_request)

    def _cleanup_stale_claims_locked(
        self,
        connection: sqlite3.Connection,
        *,
        claim_request: DeviceClaimRequest | None,
        queue_startup_grace_seconds: int,
    ) -> list[CleanupClaimResult]:
        return cleanup_stale_claims_locked(
            connection,
            claim_request=claim_request,
            queue_startup_grace_seconds=queue_startup_grace_seconds,
            load_json=self._load_json,
        )

    def _row_to_operation(self, row: sqlite3.Row) -> OperationRecord:
        return row_to_operation(row)
