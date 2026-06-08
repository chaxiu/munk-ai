from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from munk.services.errors import DeviceConflictError, OperationNotFoundError
from munk.services.operations.models import (
    CleanupClaimResult,
    DeviceClaimConflict,
    DeviceClaimRequest,
    OperationEventRecord,
    OperationKind,
    OperationRecord,
    OperationStatus,
    ResourceScope,
    now_iso,
)
from munk.services.operations.paths import operations_db_path
from munk.services.operations.payloads import infer_run_type
from munk.services.operations.payloads import matches_query as payload_matches_query

_TERMINAL_STATUSES: set[OperationStatus] = {"succeeded", "failed", "cancelled"}
_DEVICE_RESOURCE_TYPE = "device"
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
            self._ensure_column(connection, "operations", "device_ref", "TEXT NULL")
            self._ensure_column(connection, "operations", "resource_scope", "TEXT NOT NULL DEFAULT 'none'")
            self._ensure_column(connection, "operations", "conflict_reason", "TEXT NULL")
            self._ensure_column(connection, "operations", "parent_operation_id", "TEXT NULL")
            self._ensure_column(connection, "operations", "batch_id", "TEXT NULL")
            self._ensure_column(connection, "operations", "position_index", "INTEGER NULL")
            self._ensure_column(connection, "operations", "position_label", "TEXT NULL")
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
        run_type_expr = _run_type_sql_expr()
        platform_expr = _platform_sql_expr()
        sql = """
            SELECT *
            FROM operations
            WHERE 1 = 1
        """
        params: list[Any] = []
        if kind is None:
            sql += " AND kind != ?"
            params.append("interactive_session")
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind)
        if device_ref is not None:
            sql += " AND device_ref = ?"
            params.append(device_ref)
        if verification_verdict is not None:
            sql += " AND verification_verdict = ?"
            params.append(verification_verdict)
        if surface == "run_center":
            sql += f" AND ({run_type_expr}) IS NOT NULL"
        if platform is not None:
            sql += f" AND ({platform_expr}) = ?"
            params.append(platform)
        if run_type is not None:
            sql += f" AND ({run_type_expr}) = ?"
            params.append(run_type)
        if query is not None and query.strip():
            normalized_query = f"%{query.strip().lower()}%"
            sql += """
                AND (
                    LOWER(operation_id) LIKE ?
                    OR LOWER(COALESCE(app_id, '')) LIKE ?
                    OR LOWER(COALESCE(plan_id, '')) LIKE ?
                    OR LOWER(COALESCE(case_id, '')) LIKE ?
                    OR LOWER(COALESCE(json_extract(request_json, '$.case_title'), '')) LIKE ?
                    OR LOWER(COALESCE(json_extract(request_json, '$.change_summary'), '')) LIKE ?
                    OR LOWER(COALESCE(json_extract(result_json, '$.change_summary'), '')) LIKE ?
                    OR LOWER(COALESCE(json_extract(result_json, '$.summary'), '')) LIKE ?
                    OR LOWER(COALESCE(json_extract(request_json, '$.recording_id'), '')) LIKE ?
                    OR LOWER(COALESCE(json_extract(result_json, '$.recording_id'), '')) LIKE ?
                    OR LOWER(COALESCE(json_extract(progress_json, '$.recording_id'), '')) LIKE ?
                )
            """
            params.extend([normalized_query] * 11)
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
        normalized_refs = [
            (app_id.strip(), plan_id.strip())
            for app_id, plan_id in plan_refs
            if isinstance(app_id, str) and app_id.strip() and isinstance(plan_id, str) and plan_id.strip()
        ]
        if not normalized_refs:
            return {}

        unique_refs: list[tuple[str, str]] = []
        seen_refs: set[tuple[str, str]] = set()
        for ref in normalized_refs:
            if ref in seen_refs:
                continue
            seen_refs.add(ref)
            unique_refs.append(ref)

        clauses: list[str] = []
        params: list[Any] = ["run_plan"]
        for app_id, plan_id in unique_refs:
            clauses.append("(app_id = ? AND plan_id = ?)")
            params.extend([app_id, plan_id])

        sql = f"""
            SELECT *
            FROM operations
            WHERE kind = ?
              AND ({' OR '.join(clauses)})
            ORDER BY datetime(created_at) DESC, operation_id DESC
        """
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        latest_runs: dict[tuple[str, str], OperationRecord] = {}
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
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _load_json(value: Any) -> Any:
        if value in {None, ""}:
            return None
        return json.loads(str(value))

    def _insert_operation_locked(self, connection: sqlite3.Connection, record: OperationRecord) -> None:
        connection.execute(
            """
            INSERT INTO operations (
                operation_id, kind, status, verification_verdict, app_id, plan_id, case_id,
                parent_operation_id, batch_id, position_index, position_label,
                request_json, result_json, artifacts_json, progress_json, pid, cancel_requested,
                device_ref, resource_scope, conflict_reason,
                error_code, error_message, created_at, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        resource_key = self._resource_key_for_request(claim_request)
        connection.execute(
            """
            INSERT INTO operation_resource_claims (
                resource_type, resource_key, operation_id, claimed_at, released_at
            ) VALUES (?, ?, ?, ?, NULL)
            """,
            (_DEVICE_RESOURCE_TYPE, resource_key, operation_id, claimed_at),
        )

    def _find_active_device_conflicts_locked(
        self,
        connection: sqlite3.Connection,
        claim_request: DeviceClaimRequest,
    ) -> list[DeviceClaimConflict]:
        rows = self._select_active_claim_rows(connection, claim_request)
        conflicts: list[DeviceClaimConflict] = []
        for row in rows:
            conflicts.append(
                DeviceClaimConflict(
                    requested_device_ref=claim_request.device_ref,
                    blocking_operation_id=str(row["operation_id"]),
                    blocking_kind=cast(OperationKind, str(row["kind"])),
                    blocking_status=cast(OperationStatus, str(row["status"])),
                    blocking_device_ref=str(row["device_ref"]) if row["device_ref"] is not None else None,
                    reason="device_any_claim_active"
                    if str(row["resource_key"]) == "device:any"
                    else "device_ref_claim_active",
                )
            )
        return conflicts

    def _find_active_device_conflict_locked(
        self,
        connection: sqlite3.Connection,
        claim_request: DeviceClaimRequest,
    ) -> DeviceClaimConflict | None:
        conflicts = self._find_active_device_conflicts_locked(connection, claim_request)
        return conflicts[0] if conflicts else None

    def _cleanup_stale_claims_locked(
        self,
        connection: sqlite3.Connection,
        *,
        claim_request: DeviceClaimRequest | None,
        queue_startup_grace_seconds: int,
    ) -> list[CleanupClaimResult]:
        rows = self._select_cleanup_candidate_rows(connection, claim_request)
        cleaned: list[CleanupClaimResult] = []
        for row in rows:
            claim_id = int(row["claim_id"])
            operation_id = str(row["operation_id"]) if row["operation_id"] is not None else None
            resource_key = str(row["resource_key"])
            claimed_at = str(row["claimed_at"])
            owner_kind = str(row["kind"]) if row["kind"] is not None else None
            owner_status = str(row["status"]) if row["status"] is not None else None
            owner_pid = int(row["pid"]) if row["pid"] is not None else None
            owner_progress_json = row["progress_json"]

            if operation_id is None or owner_status is None:
                self._release_claim_locked(connection, claim_id)
                cleaned.append(
                    CleanupClaimResult(
                        operation_id=operation_id,
                        resource_key=resource_key,
                        action="released_missing_owner",
                        detail="claim owner missing",
                    )
                )
                continue

            if owner_status in _TERMINAL_STATUSES:
                self._release_claim_locked(connection, claim_id)
                cleaned.append(
                    CleanupClaimResult(
                        operation_id=operation_id,
                        resource_key=resource_key,
                        action="released_terminal_owner",
                        detail=f"owner already terminal: {owner_status}",
                    )
                )
                continue

            if owner_kind == "interactive_session":
                if self._interactive_claim_expired(owner_progress_json):
                    detail = "interactive session lease expired"
                    self._mark_operation_failed_locked(
                        connection,
                        operation_id=operation_id,
                        error_code="interactive_session_expired",
                        error_message=detail,
                    )
                    self._release_claim_locked(connection, claim_id)
                    cleaned.append(
                        CleanupClaimResult(
                            operation_id=operation_id,
                            resource_key=resource_key,
                            action="released_dead_owner",
                            detail=detail,
                        )
                    )
                    continue

            if owner_pid is not None and self._pid_exists(owner_pid):
                continue

            if owner_status == "queued" and not self._claim_wait_timed_out(
                claimed_at,
                queue_startup_grace_seconds,
            ):
                continue

            error_code = "owner_start_timeout" if owner_status == "queued" and owner_pid is None else "stale_claim_owner_dead"
            action = "released_start_timeout" if error_code == "owner_start_timeout" else "released_dead_owner"
            detail = (
                "queued owner did not publish a live pid before startup timeout"
                if error_code == "owner_start_timeout"
                else "owner pid is no longer alive"
            )
            self._mark_operation_failed_locked(
                connection,
                operation_id=operation_id,
                error_code=error_code,
                error_message=detail,
            )
            self._release_claim_locked(connection, claim_id)
            cleaned.append(
                CleanupClaimResult(
                    operation_id=operation_id,
                    resource_key=resource_key,
                    action=cast(Any, action),
                    detail=detail,
                )
            )
        return cleaned

    def _select_active_claim_rows(
        self,
        connection: sqlite3.Connection,
        claim_request: DeviceClaimRequest,
    ) -> list[sqlite3.Row]:
        query = """
            SELECT
                c.claim_id,
                c.resource_key,
                c.operation_id,
                o.kind,
                o.status,
                o.device_ref
            FROM operation_resource_claims c
            JOIN operations o ON o.operation_id = c.operation_id
            WHERE c.resource_type = ?
              AND c.released_at IS NULL
        """
        params: list[Any] = [_DEVICE_RESOURCE_TYPE]
        resource_keys = claim_request.resource_keys()
        if resource_keys is not None:
            query += f" AND c.resource_key IN ({', '.join('?' for _ in resource_keys)})"
            params.extend(resource_keys)
        query += " ORDER BY c.claimed_at ASC"
        return connection.execute(query, params).fetchall()

    def _select_cleanup_candidate_rows(
        self,
        connection: sqlite3.Connection,
        claim_request: DeviceClaimRequest | None,
    ) -> list[sqlite3.Row]:
        query = """
            SELECT
                c.claim_id,
                c.resource_key,
                c.operation_id,
                c.claimed_at,
                o.kind,
                o.status,
                o.pid,
                o.progress_json
            FROM operation_resource_claims c
            LEFT JOIN operations o ON o.operation_id = c.operation_id
            WHERE c.resource_type = ?
              AND c.released_at IS NULL
        """
        params: list[Any] = [_DEVICE_RESOURCE_TYPE]
        if claim_request is not None:
            resource_keys = claim_request.resource_keys()
            if resource_keys is not None:
                query += f" AND c.resource_key IN ({', '.join('?' for _ in resource_keys)})"
                params.extend(resource_keys)
        query += " ORDER BY c.claimed_at ASC"
        return connection.execute(query, params).fetchall()

    @staticmethod
    def _resource_key_for_request(claim_request: DeviceClaimRequest) -> str:
        if claim_request.resource_scope == "device_ref" and claim_request.device_ref:
            return f"device:{claim_request.device_ref}"
        return "device:any"

    @staticmethod
    def _release_claim_locked(connection: sqlite3.Connection, claim_id: int) -> None:
        connection.execute(
            """
            UPDATE operation_resource_claims
            SET released_at = ?
            WHERE claim_id = ? AND released_at IS NULL
            """,
            (now_iso(), claim_id),
        )

    def _interactive_claim_expired(self, progress_json: str | None) -> bool:
        payload = self._load_json(progress_json)
        if not isinstance(payload, dict):
            return False
        payload_dict = cast(dict[str, object], payload)
        session_state = payload_dict.get("interactive_session")
        if not isinstance(session_state, dict):
            return False
        session_state_dict = cast(dict[str, object], session_state)
        now = datetime.now(timezone.utc)
        for key in ("expires_at", "idle_expires_at"):
            value = session_state_dict.get(key)
            if not isinstance(value, str):
                continue
            try:
                deadline = datetime.fromisoformat(value)
            except ValueError:
                continue
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if deadline.astimezone(timezone.utc) <= now:
                return True
        return False

    @staticmethod
    def _mark_operation_failed_locked(
        connection: sqlite3.Connection,
        *,
        operation_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        connection.execute(
            """
            UPDATE operations
            SET status = 'failed',
                error_code = ?,
                error_message = ?,
                finished_at = COALESCE(finished_at, ?)
            WHERE operation_id = ?
            """,
            (error_code, error_message, now_iso(), operation_id),
        )

    @staticmethod
    def _claim_wait_timed_out(claimed_at: str, queue_startup_grace_seconds: int) -> bool:
        try:
            claimed = datetime.fromisoformat(claimed_at)
        except ValueError:
            return True
        if claimed.tzinfo is None:
            claimed = claimed.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - claimed.astimezone(timezone.utc)
        return delta.total_seconds() > queue_startup_grace_seconds

    @staticmethod
    def _pid_exists(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _ensure_column(
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

    def _row_to_operation(self, row: sqlite3.Row) -> OperationRecord:
        return OperationRecord(
            operation_id=str(row["operation_id"]),
            kind=cast(OperationKind, str(row["kind"])),
            status=cast(OperationStatus, str(row["status"])),
            verification_verdict=row["verification_verdict"],
            app_id=row["app_id"],
            plan_id=row["plan_id"],
            case_id=row["case_id"],
            parent_operation_id=str(row["parent_operation_id"]) if row["parent_operation_id"] is not None else None,
            batch_id=str(row["batch_id"]) if row["batch_id"] is not None else None,
            position_index=int(row["position_index"]) if row["position_index"] is not None else None,
            position_label=str(row["position_label"]) if row["position_label"] is not None else None,
            request_json=self._load_json(row["request_json"]) or {},
            result_json=self._load_json(row["result_json"]),
            artifacts_json=self._load_json(row["artifacts_json"]) or {},
            progress_json=self._load_json(row["progress_json"]) or {},
            pid=int(row["pid"]) if row["pid"] is not None else None,
            cancel_requested=bool(row["cancel_requested"]),
            device_ref=str(row["device_ref"]) if row["device_ref"] is not None else None,
            resource_scope=cast(ResourceScope, str(row["resource_scope"]) if row["resource_scope"] is not None else "none"),
            conflict_reason=str(row["conflict_reason"]) if row["conflict_reason"] is not None else None,
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=str(row["created_at"]),
            started_at=str(row["started_at"]) if row["started_at"] is not None else None,
            finished_at=str(row["finished_at"]) if row["finished_at"] is not None else None,
        )


def _include_in_run_center(record: OperationRecord) -> bool:
    return _infer_run_type(record) is not None


def _recording_id_sql_expr() -> str:
    return (
        "COALESCE("
        "NULLIF(json_extract(request_json, '$.recording_id'), ''), "
        "NULLIF(json_extract(result_json, '$.recording_id'), ''), "
        "NULLIF(json_extract(progress_json, '$.recording_id'), '')"
        ")"
    )


def _run_type_sql_expr() -> str:
    recording_id_expr = _recording_id_sql_expr()
    return f"""
        CASE
            WHEN kind = 'run_plans' THEN 'plan_batch_run'
            WHEN kind = 'run_plan' THEN 'plan_run'
            WHEN kind = 'optimize_case' THEN 'optimize_case'
            WHEN kind = 'knowledge_post_action' THEN 'knowledge_post_action'
            WHEN kind = 'verify_change' THEN 'verify_change'
            WHEN kind = 'run_case'
             AND (
                COALESCE(plan_id, '') LIKE 'recording-replay:%'
                OR {recording_id_expr} IS NOT NULL
             ) THEN 'replay'
            WHEN kind = 'run_case' THEN 'case_run'
            ELSE NULL
        END
    """


def _platform_sql_expr() -> str:
    return """
        COALESCE(
            NULLIF(json_extract(request_json, '$.platform'), ''),
            NULLIF(json_extract(request_json, '$.app_target.platform'), ''),
            NULLIF(json_extract(result_json, '$.platform'), ''),
            NULLIF(json_extract(progress_json, '$.platform'), ''),
            CASE
                WHEN json_extract(request_json, '$.base_url') IS NOT NULL THEN 'web'
                ELSE NULL
            END,
            CASE
                WHEN json_extract(request_json, '$.bundle_id') IS NOT NULL THEN 'ios'
                ELSE NULL
            END,
            CASE
                WHEN json_extract(request_json, '$.package') IS NOT NULL THEN 'android'
                ELSE NULL
            END
        )
    """


def _infer_run_type(record: OperationRecord) -> str | None:
    return infer_run_type(record)


def _infer_platform(record: OperationRecord) -> str | None:
    request = _json_dict(record.request_json)
    result = _json_dict(record.result_json)
    progress = _json_dict(record.progress_json)
    request_target = request.get("app_target")
    request_target_dict = cast(dict[str, object] | None, request_target) if isinstance(request_target, dict) else None
    for candidate in (
        request.get("platform"),
        request_target_dict.get("platform") if request_target_dict is not None else None,
        result.get("platform"),
        progress.get("platform"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    if request.get("base_url"):
        return "web"
    if request.get("bundle_id"):
        return "ios"
    if request.get("package"):
        return "android"
    return None


def _matches_query(record: OperationRecord, query: str) -> bool:
    # Keep list filtering aligned with the title/query fields used by API payloads.
    return payload_matches_query(record, query)


def _infer_title(record: OperationRecord) -> str:
    request = _json_dict(record.request_json)
    result = _json_dict(record.result_json)
    run_type = _infer_run_type(record)
    if run_type == "verify_change":
        for candidate in (
            request.get("change_summary"),
            result.get("change_summary"),
            record.plan_id,
            record.operation_id,
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        return record.operation_id
    if run_type == "plan_run":
        return record.plan_id or record.operation_id
    if run_type == "replay":
        return record.case_id or _source_recording_id(record) or record.operation_id
    if run_type == "case_run":
        return record.case_id or record.operation_id
    return record.case_id or record.plan_id or record.operation_id


def _infer_target_label(record: OperationRecord) -> str:
    parts = [record.app_id, record.plan_id, record.case_id]
    label = " / ".join(part for part in parts if part)
    return label or record.operation_id


def _source_recording_id(record: OperationRecord) -> str | None:
    request = _json_dict(record.request_json)
    result = _json_dict(record.result_json)
    progress = _json_dict(record.progress_json)
    for candidate in (
        request.get("recording_id"),
        result.get("recording_id"),
        progress.get("recording_id"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _json_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
