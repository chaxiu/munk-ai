from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from munk.services.operations.paths import operations_db_path
from munk.services.operations.payload_storage import (
    LLM_ENTRY_KEY,
    LLM_EVENT_TYPES,
    LLM_TEXT_KEY,
    LLM_TEXT_PATH_KEY,
    extract_llm_text_for_storage,
    should_externalize_result,
    split_result_for_storage,
    write_external_llm_text,
    write_external_result,
)

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PayloadMigrationSummary:
    operations_externalized: int
    events_externalized: int
    db_path: Path


def migrate_operations_payloads(
    db_path: Path | None = None,
    *,
    limit: int | None = None,
) -> PayloadMigrationSummary:
    """Externalize large inline result/event payloads already stored in SQLite."""
    resolved_db = db_path or operations_db_path()
    if not resolved_db.exists():
        return PayloadMigrationSummary(operations_externalized=0, events_externalized=0, db_path=resolved_db)

    operations_root = resolved_db.parent
    operations_externalized = 0
    events_externalized = 0
    connection = sqlite3.connect(resolved_db)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        _ensure_result_path_column(connection)
        operations_externalized = _migrate_operation_results(
            connection,
            operations_root=operations_root,
            limit=limit,
        )
        events_externalized = _migrate_llm_events(
            connection,
            operations_root=operations_root,
            limit=limit,
        )
        connection.commit()
    finally:
        connection.close()
    _logger.info(
        "operations payload migration complete db=%s operations=%s events=%s",
        resolved_db,
        operations_externalized,
        events_externalized,
    )
    return PayloadMigrationSummary(
        operations_externalized=operations_externalized,
        events_externalized=events_externalized,
        db_path=resolved_db,
    )


def _ensure_result_path_column(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(operations)").fetchall()
    existing = {str(row["name"]) for row in rows}
    if "result_path" not in existing:
        connection.execute("ALTER TABLE operations ADD COLUMN result_path TEXT NULL")


def _migrate_operation_results(
    connection: sqlite3.Connection,
    *,
    operations_root: Path,
    limit: int | None,
) -> int:
    sql = """
        SELECT operation_id, result_json, result_path
        FROM operations
        WHERE result_json IS NOT NULL
          AND result_json != ''
          AND result_json != 'null'
          AND (
            result_path IS NULL
            OR result_path = ''
          )
        ORDER BY created_at ASC
    """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    rows = connection.execute(sql).fetchall()
    migrated = 0
    for row in rows:
        raw = row["result_json"]
        if raw in {None, "", "null"}:
            continue
        try:
            result_json = json.loads(str(raw))
        except json.JSONDecodeError:
            continue
        if not isinstance(result_json, dict) or not should_externalize_result(result_json):
            continue
        inline_summary, external_payload = split_result_for_storage(result_json)
        if external_payload is None:
            continue
        operation_id = str(row["operation_id"])
        result_path = write_external_result(
            operation_id=operation_id,
            payload=external_payload,
            root=operations_root,
        )
        connection.execute(
            """
            UPDATE operations
            SET result_json = ?, result_path = ?
            WHERE operation_id = ?
            """,
            (json.dumps(inline_summary, ensure_ascii=False), result_path, operation_id),
        )
        migrated += 1
    return migrated


def _migrate_llm_events(
    connection: sqlite3.Connection,
    *,
    operations_root: Path,
    limit: int | None,
) -> int:
    placeholders = ", ".join("?" for _ in LLM_EVENT_TYPES)
    sql = f"""
        SELECT seq, operation_id, event_type, data_json
        FROM operation_events
        WHERE event_type IN ({placeholders})
          AND (
            instr(data_json, '"{LLM_TEXT_KEY}"') > 0
            OR instr(data_json, '"{LLM_ENTRY_KEY}"') > 0
          )
        ORDER BY seq ASC
    """
    params: list[Any] = list(LLM_EVENT_TYPES)
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    rows = connection.execute(sql, params).fetchall()
    migrated = 0
    for row in rows:
        try:
            data_json = json.loads(str(row["data_json"] or "{}"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data_json, dict):
            continue
        already_externalized = isinstance(data_json.get(LLM_TEXT_PATH_KEY), str)
        needs_strip = LLM_TEXT_KEY in data_json or LLM_ENTRY_KEY in data_json
        if not needs_strip:
            continue
        inline, text = extract_llm_text_for_storage(data_json)
        seq = int(row["seq"])
        operation_id = str(row["operation_id"])
        event_type = str(row["event_type"])
        if text is not None and not already_externalized:
            text_path = write_external_llm_text(
                operation_id=operation_id,
                seq=seq,
                event_type=event_type,
                text=text,
                root=operations_root,
            )
            inline[LLM_TEXT_PATH_KEY] = text_path
        elif already_externalized and isinstance(data_json.get(LLM_TEXT_PATH_KEY), str):
            inline[LLM_TEXT_PATH_KEY] = data_json[LLM_TEXT_PATH_KEY]
        connection.execute(
            "UPDATE operation_events SET data_json = ? WHERE seq = ?",
            (json.dumps(inline, ensure_ascii=False), seq),
        )
        migrated += 1
    return migrated
