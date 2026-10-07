from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, cast

from munk.services.operations.models import (
    CleanupClaimResult,
    DeviceClaimConflict,
    DeviceClaimRequest,
    OperationKind,
    OperationStatus,
    now_iso,
)

TERMINAL_STATUSES: set[OperationStatus] = {"succeeded", "failed", "cancelled", "interrupted"}
DEVICE_RESOURCE_TYPE = "device"


def insert_claim_locked(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    claim_request: DeviceClaimRequest,
    claimed_at: str,
) -> None:
    resource_key = resource_key_for_request(claim_request)
    connection.execute(
        """
        INSERT INTO operation_resource_claims (
            resource_type, resource_key, operation_id, claimed_at, released_at
        ) VALUES (?, ?, ?, ?, NULL)
        """,
        (DEVICE_RESOURCE_TYPE, resource_key, operation_id, claimed_at),
    )


def find_active_device_conflicts_locked(
    connection: sqlite3.Connection,
    claim_request: DeviceClaimRequest,
) -> list[DeviceClaimConflict]:
    rows = select_active_claim_rows(connection, claim_request)
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


def find_active_device_conflict_locked(
    connection: sqlite3.Connection,
    claim_request: DeviceClaimRequest,
) -> DeviceClaimConflict | None:
    conflicts = find_active_device_conflicts_locked(connection, claim_request)
    return conflicts[0] if conflicts else None


def cleanup_stale_claims_locked(
    connection: sqlite3.Connection,
    *,
    claim_request: DeviceClaimRequest | None,
    queue_startup_grace_seconds: int,
    load_json: Any,
) -> list[CleanupClaimResult]:
    rows = select_cleanup_candidate_rows(connection, claim_request)
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
            release_claim_locked(connection, claim_id)
            cleaned.append(
                CleanupClaimResult(
                    operation_id=operation_id,
                    resource_key=resource_key,
                    action="released_missing_owner",
                    detail="claim owner missing",
                )
            )
            continue

        if owner_status in TERMINAL_STATUSES:
            release_claim_locked(connection, claim_id)
            cleaned.append(
                CleanupClaimResult(
                    operation_id=operation_id,
                    resource_key=resource_key,
                    action="released_terminal_owner",
                    detail=f"owner already terminal: {owner_status}",
                )
            )
            continue

        if owner_kind == "interactive_session" and interactive_claim_expired(owner_progress_json, load_json):
            detail = "interactive session lease expired"
            from munk.services.operations.lifecycle_reconcile import finalize_owner_and_descendants_locked

            finalize_owner_and_descendants_locked(
                connection,
                operation_id=operation_id,
                status="failed",
                error_code="interactive_session_expired",
                error_message=detail,
            )
            release_claim_locked(connection, claim_id)
            cleaned.append(
                CleanupClaimResult(
                    operation_id=operation_id,
                    resource_key=resource_key,
                    action="released_dead_owner",
                    detail=detail,
                )
            )
            continue

        if owner_pid is not None and pid_exists(owner_pid):
            continue

        if owner_status == "queued" and not claim_wait_timed_out(claimed_at, queue_startup_grace_seconds):
            continue

        from munk.services.operations.lifecycle_reconcile import (
            FinalizeStatus,
            finalize_owner_and_descendants_locked,
        )

        if owner_status == "queued" and owner_pid is None:
            error_code = "owner_start_timeout"
            action = "released_start_timeout"
            detail = "queued owner did not publish a live pid before startup timeout"
            finalize_status: FinalizeStatus = "failed"
        else:
            error_code = "owner_pid_dead"
            action = "released_dead_owner"
            detail = "owner pid is no longer alive"
            finalize_status = "interrupted"
        finalize_owner_and_descendants_locked(
            connection,
            operation_id=operation_id,
            status=finalize_status,
            error_code=error_code,
            error_message=detail,
        )
        release_claim_locked(connection, claim_id)
        cleaned.append(
            CleanupClaimResult(
                operation_id=operation_id,
                resource_key=resource_key,
                action=cast(Any, action),
                detail=detail,
            )
        )
    return cleaned


def select_active_claim_rows(
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
    params: list[Any] = [DEVICE_RESOURCE_TYPE]
    resource_keys = claim_request.resource_keys()
    if resource_keys is not None:
        query += f" AND c.resource_key IN ({', '.join('?' for _ in resource_keys)})"
        params.extend(resource_keys)
    query += " ORDER BY c.claimed_at ASC"
    return connection.execute(query, params).fetchall()


def select_cleanup_candidate_rows(
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
    params: list[Any] = [DEVICE_RESOURCE_TYPE]
    if claim_request is not None:
        resource_keys = claim_request.resource_keys()
        if resource_keys is not None:
            query += f" AND c.resource_key IN ({', '.join('?' for _ in resource_keys)})"
            params.extend(resource_keys)
    query += " ORDER BY c.claimed_at ASC"
    return connection.execute(query, params).fetchall()


def resource_key_for_request(claim_request: DeviceClaimRequest) -> str:
    if claim_request.resource_scope == "device_ref" and claim_request.device_ref:
        return f"device:{claim_request.device_ref}"
    return "device:any"


def release_claim_locked(connection: sqlite3.Connection, claim_id: int) -> None:
    connection.execute(
        """
        UPDATE operation_resource_claims
        SET released_at = ?
        WHERE claim_id = ? AND released_at IS NULL
        """,
        (now_iso(), claim_id),
    )


def interactive_claim_expired(progress_json: str | None, load_json: Any) -> bool:
    payload = load_json(progress_json)
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


def mark_operation_failed_locked(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    error_code: str,
    error_message: str,
) -> None:
    from munk.services.operations.lifecycle_reconcile import mark_operation_terminal_locked

    mark_operation_terminal_locked(
        connection,
        operation_id=operation_id,
        status="failed",
        error_code=error_code,
        error_message=error_message,
    )


def claim_wait_timed_out(claimed_at: str, queue_startup_grace_seconds: int) -> bool:
    try:
        claimed = datetime.fromisoformat(claimed_at)
    except ValueError:
        return True
    if claimed.tzinfo is None:
        claimed = claimed.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - claimed.astimezone(timezone.utc)
    return delta.total_seconds() > queue_startup_grace_seconds


def pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
