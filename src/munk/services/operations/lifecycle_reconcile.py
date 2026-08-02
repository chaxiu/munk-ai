from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Literal

from munk.services.operations.models import (
    OperationRecord,
    ReconcileOperationResult,
    now_iso,
)
from munk.services.operations.registry_claims import TERMINAL_STATUSES, pid_exists

if TYPE_CHECKING:
    from munk.services.operations.registry import OperationRegistry

FinalizeStatus = Literal["failed", "cancelled", "interrupted"]


def owner_pid_reachable(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    return pid_exists(pid)


def is_orphaned_operation(record: OperationRecord) -> bool:
    if record.status not in {"queued", "running"}:
        return False
    if owner_pid_reachable(record.pid):
        return False
    if record.pid is not None and record.pid > 0:
        return True
    # Running without a live pid cannot make progress; queued without pid may still be starting.
    return record.status == "running"


def should_force_cancel(record: OperationRecord) -> bool:
    if owner_pid_reachable(record.pid):
        return False
    if record.pid is not None and record.pid > 0:
        return True
    return record.status == "running"


def iter_descendant_operations(registry: OperationRegistry, root_operation_id: str) -> list[OperationRecord]:
    descendants: list[OperationRecord] = []
    queue = [root_operation_id]
    seen: set[str] = {root_operation_id}
    while queue:
        parent_id = queue.pop(0)
        for child in registry.list_child_operations(parent_id):
            if child.operation_id in seen:
                continue
            seen.add(child.operation_id)
            descendants.append(child)
            queue.append(child.operation_id)
    return descendants


def force_finalize_operation_tree(
    registry: OperationRegistry,
    root_operation_id: str,
    *,
    status: FinalizeStatus,
    error_code: str,
    error_message: str,
) -> list[str]:
    root = registry.get_operation(root_operation_id)
    targets = [root, *iter_descendant_operations(registry, root_operation_id)]
    finalized: list[str] = []
    finished_at = now_iso()
    for record in targets:
        if record.status in TERMINAL_STATUSES:
            continue
        registry.update_operation(
            record.operation_id,
            status=status,
            verification_verdict=None,
            error_code=error_code,
            error_message=error_message,
            finished_at=finished_at,
        )
        registry.release_claims(record.operation_id)
        finalized.append(record.operation_id)
    return finalized


def request_cancel_operation_tree(registry: OperationRegistry, root_operation_id: str) -> list[str]:
    root = registry.request_cancel(root_operation_id)
    cancelled_ids = [root.operation_id]
    for record in iter_descendant_operations(registry, root_operation_id):
        if record.status in TERMINAL_STATUSES:
            continue
        registry.request_cancel(record.operation_id)
        cancelled_ids.append(record.operation_id)
    return cancelled_ids


def release_claims_operation_tree(registry: OperationRegistry, root_operation_id: str) -> int:
    """Release device claims for root and descendants immediately (cancel hot path)."""
    root = registry.get_operation(root_operation_id)
    targets = [root, *iter_descendant_operations(registry, root_operation_id)]
    released = 0
    for record in targets:
        released += registry.release_claims(record.operation_id)
    return released


def operation_tree_ids(registry: OperationRegistry, root_operation_id: str) -> list[str]:
    root = registry.get_operation(root_operation_id)
    return [root.operation_id, *[item.operation_id for item in iter_descendant_operations(registry, root_operation_id)]]


def reconcile_orphaned_operations(registry: OperationRegistry) -> list[ReconcileOperationResult]:
    candidates = [
        *registry.list_operations(limit=10_000, status="queued"),
        *registry.list_operations(limit=10_000, status="running"),
    ]
    orphans: list[OperationRecord] = []
    for record in candidates:
        current = registry.get_operation(record.operation_id)
        if current.status in TERMINAL_STATUSES:
            continue
        if not is_orphaned_operation(current):
            continue
        orphans.append(current)

    orphan_ids = {item.operation_id for item in orphans}
    results: list[ReconcileOperationResult] = []
    for current in orphans:
        # Descendants are finalized with their orphaned ancestor to keep one tree action.
        if current.parent_operation_id is not None and current.parent_operation_id in orphan_ids:
            continue
        refreshed = registry.get_operation(current.operation_id)
        if refreshed.status in TERMINAL_STATUSES:
            continue
        if refreshed.cancel_requested:
            status: FinalizeStatus = "cancelled"
            error_code = "operation_cancelled"
            detail = "orphaned operation finalized after cancel request; owner pid is no longer alive"
        else:
            status = "interrupted"
            error_code = "owner_pid_dead"
            detail = "orphaned operation interrupted; owner pid is no longer alive"
        finalized_ids = force_finalize_operation_tree(
            registry,
            refreshed.operation_id,
            status=status,
            error_code=error_code,
            error_message=detail,
        )
        results.append(
            ReconcileOperationResult(
                operation_id=refreshed.operation_id,
                status=status,
                error_code=error_code,
                detail=detail,
                finalized_operation_ids=finalized_ids,
            )
        )
    return results


def list_nonterminal_descendant_ids_locked(
    connection: sqlite3.Connection,
    root_operation_id: str,
) -> list[str]:
    descendant_ids: list[str] = []
    queue = [root_operation_id]
    seen: set[str] = {root_operation_id}
    while queue:
        parent_id = queue.pop(0)
        rows = connection.execute(
            """
            SELECT operation_id, status
            FROM operations
            WHERE parent_operation_id = ?
            ORDER BY
                CASE WHEN position_index IS NULL THEN 1 ELSE 0 END ASC,
                position_index ASC,
                datetime(created_at) ASC,
                operation_id ASC
            """,
            (parent_id,),
        ).fetchall()
        for row in rows:
            child_id = str(row["operation_id"])
            if child_id in seen:
                continue
            seen.add(child_id)
            queue.append(child_id)
            if str(row["status"]) not in TERMINAL_STATUSES:
                descendant_ids.append(child_id)
    return descendant_ids


def mark_operation_terminal_locked(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    status: FinalizeStatus,
    error_code: str,
    error_message: str,
) -> None:
    connection.execute(
        """
        UPDATE operations
        SET status = ?,
            verification_verdict = NULL,
            error_code = ?,
            error_message = ?,
            finished_at = COALESCE(finished_at, ?)
        WHERE operation_id = ?
          AND status NOT IN ('succeeded', 'failed', 'cancelled', 'interrupted')
        """,
        (status, error_code, error_message, now_iso(), operation_id),
    )


def cascade_finalize_descendants_locked(
    connection: sqlite3.Connection,
    root_operation_id: str,
    *,
    status: FinalizeStatus,
    error_code: str,
    error_message: str,
) -> list[str]:
    descendant_ids = list_nonterminal_descendant_ids_locked(connection, root_operation_id)
    for operation_id in descendant_ids:
        mark_operation_terminal_locked(
            connection,
            operation_id=operation_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
        )
        connection.execute(
            """
            UPDATE operation_resource_claims
            SET released_at = ?
            WHERE operation_id = ? AND released_at IS NULL
            """,
            (now_iso(), operation_id),
        )
    return descendant_ids


def finalize_owner_and_descendants_locked(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    status: FinalizeStatus,
    error_code: str,
    error_message: str,
) -> list[str]:
    mark_operation_terminal_locked(
        connection,
        operation_id=operation_id,
        status=status,
        error_code=error_code,
        error_message=error_message,
    )
    cascaded = cascade_finalize_descendants_locked(
        connection,
        operation_id,
        status=status,
        error_code=error_code,
        error_message=error_message,
    )
    return [operation_id, *cascaded]
