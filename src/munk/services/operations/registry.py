from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from munk.services.errors import DeviceConflictError, OperationNotFoundError
from munk.services.operations.lifecycle_reconcile import (
    force_finalize_operation_tree,
    iter_descendant_operations,
    operation_tree_ids,
    reconcile_orphaned_operations,
    release_claims_operation_tree,
    request_cancel_operation_tree,
)
from munk.services.operations.models import (
    CleanupClaimResult,
    DeviceClaimConflict,
    DeviceClaimRequest,
    OperationEventRecord,
    OperationKind,
    OperationRecord,
    OperationStatus,
    ReconcileOperationResult,
    now_iso,
)
from munk.services.operations.paths import operations_db_path
from munk.services.operations.payload_storage import (
    LLM_EVENT_TYPES,
    LLM_TEXT_KEY,
    LLM_TEXT_PATH_KEY,
    extract_llm_text_for_storage,
    split_result_for_storage,
    write_external_llm_text,
    write_external_result,
)
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
    build_count_operations_query,
    build_latest_plan_runs_query,
    build_list_operations_page_query,
)
from munk.services.operations.registry_schema import initialize_registry_schema
from munk.services.operations.registry_serialization import dump_json, load_json, row_to_event, row_to_operation

_QUEUE_STARTUP_GRACE_SECONDS = 30
_logger = logging.getLogger(__name__)


class OperationRegistry:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or operations_db_path()
        self._operations_root = self._db_path.parent
        self._initialize()

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def operations_root(self) -> Path:
        return self._operations_root

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
        count_sql, count_params = build_count_operations_query(
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
            total_row = connection.execute(count_sql, count_params).fetchone()
        sql += """
            ORDER BY created_at DESC, operation_id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        records = [self._row_to_operation(row, hydrate_payloads=False) for row in rows]
        total = int(total_row["total"]) if total_row is not None else 0
        return records, total

    def count_operations(
        self,
        *,
        status: OperationStatus | None = None,
        kind: OperationKind | None = None,
        device_ref: str | None = None,
        surface: str | None = None,
        verification_verdict: str | None = None,
        platform: str | None = None,
        query: str | None = None,
        run_type: str | None = None,
    ) -> int:
        run_type_expr = run_type_sql_expr()
        platform_expr = platform_sql_expr()
        sql, params = build_count_operations_query(
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
            row = connection.execute(sql, params).fetchone()
        return int(row["total"]) if row is not None else 0

    def list_latest_plan_runs(self, plan_refs: list[tuple[str, str]]) -> dict[tuple[str, str], OperationRecord]:
        sql, params, unique_refs = build_latest_plan_runs_query(plan_refs)
        if sql is None:
            return {}
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        allowed_refs = set(unique_refs)
        latest_runs: dict[tuple[str, str], OperationRecord] = {}
        for row in rows:
            record = self._row_to_operation(row, hydrate_payloads=False)
            key = (record.app_id or "", record.plan_id or "")
            if key not in allowed_refs:
                continue
            latest_runs[key] = record
        return latest_runs

    def update_operation(self, operation_id: str, **fields: Any) -> OperationRecord:
        if not fields:
            return self.get_operation(operation_id)
        fields = self._prepare_update_fields(operation_id, fields)
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

    def reconcile_orphaned_operations(self) -> list[ReconcileOperationResult]:
        return reconcile_orphaned_operations(self)

    def iter_descendant_operations(self, root_operation_id: str) -> list[OperationRecord]:
        return iter_descendant_operations(self, root_operation_id)

    def force_finalize_operation_tree(
        self,
        root_operation_id: str,
        *,
        status: OperationStatus,
        error_code: str,
        error_message: str,
    ) -> list[str]:
        if status not in {"failed", "cancelled", "interrupted"}:
            raise ValueError(f"unsupported force-finalize status: {status}")
        return force_finalize_operation_tree(
            self,
            root_operation_id,
            status=status,  # type: ignore[arg-type]
            error_code=error_code,
            error_message=error_message,
        )

    def request_cancel_operation_tree(self, root_operation_id: str) -> list[str]:
        return request_cancel_operation_tree(self, root_operation_id)

    def release_claims_operation_tree(self, root_operation_id: str) -> int:
        return release_claims_operation_tree(self, root_operation_id)

    def operation_tree_ids(self, root_operation_id: str) -> list[str]:
        return operation_tree_ids(self, root_operation_id)

    def append_event(
        self,
        operation_id: str,
        *,
        timestamp: str,
        event_type: str,
        message: str | None,
        data_json: dict[str, Any] | None = None,
    ) -> OperationEventRecord:
        stored_payload = dict(data_json or {})
        external_llm_text: str | None = None
        if event_type in LLM_EVENT_TYPES:
            stored_payload, external_llm_text = extract_llm_text_for_storage(stored_payload)
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
                    self._dump_json(stored_payload),
                ),
            )
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("failed to append operation event")
            seq = int(row_id)
            if external_llm_text is not None:
                text_path = write_external_llm_text(
                    operation_id=operation_id,
                    seq=seq,
                    event_type=event_type,
                    text=external_llm_text,
                    root=self._operations_root,
                )
                stored_payload[LLM_TEXT_PATH_KEY] = text_path
                connection.execute(
                    "UPDATE operation_events SET data_json = ? WHERE seq = ?",
                    (self._dump_json(stored_payload), seq),
                )
        hydrated = dict(stored_payload)
        if external_llm_text is not None:
            hydrated[LLM_TEXT_KEY] = external_llm_text
        return OperationEventRecord(
            seq=seq,
            operation_id=operation_id,
            timestamp=timestamp,
            event_type=event_type,
            message=message,
            data_json=hydrated,
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
        return [row_to_event(row, hydrate_payloads=True) for row in rows]

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

    def _prepare_update_fields(self, operation_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        prepared = dict(fields)
        if "result_json" in prepared:
            inline_summary, external_payload = split_result_for_storage(
                prepared["result_json"] if isinstance(prepared["result_json"], dict) else None
            )
            if external_payload is not None:
                prepared["result_json"] = inline_summary
                prepared["result_path"] = write_external_result(
                    operation_id=operation_id,
                    payload=external_payload,
                    root=self._operations_root,
                )
            elif prepared.get("result_path") is None and "result_path" not in prepared:
                # Keep an existing result_path unless the caller clears/replaces it.
                pass
        if should_refresh_projection(prepared):
            current = self.get_operation(operation_id)
            projected = with_projected_fields(current.model_copy(update=prepared))
            prepared = {
                **prepared,
                "projected_run_type": projected.projected_run_type,
                "projected_platform": projected.projected_platform,
                "projected_title": projected.projected_title,
                "projected_source_recording_id": projected.projected_source_recording_id,
            }
        return prepared

    def _prepare_insert_record(self, record: OperationRecord) -> OperationRecord:
        inline_summary, external_payload = split_result_for_storage(record.result_json)
        if external_payload is None:
            return record
        result_path = write_external_result(
            operation_id=record.operation_id,
            payload=external_payload,
            root=self._operations_root,
        )
        return record.model_copy(update={"result_json": inline_summary, "result_path": result_path})

    def _insert_operation_locked(self, connection: sqlite3.Connection, record: OperationRecord) -> None:
        stored = self._prepare_insert_record(record)
        connection.execute(
            """
            INSERT INTO operations (
                operation_id, kind, status, verification_verdict, app_id, plan_id, case_id,
                parent_operation_id, batch_id, position_index, position_label,
                request_json, result_json, artifacts_json, progress_json,
                projected_run_type, projected_platform, projected_title, projected_source_recording_id,
                result_path,
                pid, cancel_requested,
                device_ref, resource_scope, conflict_reason,
                error_code, error_message, created_at, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stored.operation_id,
                stored.kind,
                stored.status,
                stored.verification_verdict,
                stored.app_id,
                stored.plan_id,
                stored.case_id,
                stored.parent_operation_id,
                stored.batch_id,
                stored.position_index,
                stored.position_label,
                self._dump_json(stored.request_json),
                self._dump_json(stored.result_json),
                self._dump_json(stored.artifacts_json),
                self._dump_json(stored.progress_json),
                stored.projected_run_type,
                stored.projected_platform,
                stored.projected_title,
                stored.projected_source_recording_id,
                stored.result_path,
                stored.pid,
                int(stored.cancel_requested),
                stored.device_ref,
                stored.resource_scope,
                stored.conflict_reason,
                stored.error_code,
                stored.error_message,
                stored.created_at,
                stored.started_at,
                stored.finished_at,
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

    def _row_to_operation(self, row: sqlite3.Row, *, hydrate_payloads: bool = True) -> OperationRecord:
        return row_to_operation(row, hydrate_payloads=hydrate_payloads)
