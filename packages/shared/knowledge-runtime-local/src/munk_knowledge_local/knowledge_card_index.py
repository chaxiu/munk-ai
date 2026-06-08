from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from .knowledge_card_db import KnowledgeCardDb
from .sqlite_vec_compat import serialize_float32


@dataclass(frozen=True)
class KnowledgeCardIndexBuildResult:
    total_cards: int
    rebuilt_cards: int
    skipped_cards: int


class KnowledgeCardIndexService:
    def __init__(self, *, db: KnowledgeCardDb, embedding_service) -> None:  # noqa: ANN001
        self.db = db
        self.embedding_service = embedding_service

    def build(self, *, app_id: str, records) -> KnowledgeCardIndexBuildResult:  # noqa: ANN001
        connection = self.db.connect()
        total_cards = len(records)
        rebuilt_cards = 0
        skipped_cards = 0
        try:
            active_card_ids = {record.card_id for record in records}
            self._reconcile_deleted_cards(connection, app_id=app_id, active_card_ids=active_card_ids)
            rebuild_records = []
            for record in records:
                if self._is_cache_hit(connection, record=record):
                    skipped_cards += 1
                    continue
                rebuild_records.append(record)
            embeddings = self.embedding_service.encode_documents([record.embedding_text for record in rebuild_records]) if rebuild_records else []
            for index, record in enumerate(rebuild_records):
                embedding = embeddings[index]
                self._upsert_record(connection, record=record, embedding=embedding)
                rebuilt_cards += 1
            connection.commit()
        finally:
            connection.close()
        return KnowledgeCardIndexBuildResult(
            total_cards=total_cards,
            rebuilt_cards=rebuilt_cards,
            skipped_cards=skipped_cards,
        )

    def upsert_records(self, *, app_id: str, records) -> KnowledgeCardIndexBuildResult:  # noqa: ANN001
        connection = self.db.connect()
        total_cards = len(records)
        rebuilt_cards = 0
        skipped_cards = 0
        try:
            rebuild_records = []
            for record in records:
                if record.app_id != app_id:
                    raise ValueError(f"record app_id mismatch: expected '{app_id}', got '{record.app_id}'")
                if self._is_cache_hit(connection, record=record):
                    skipped_cards += 1
                    continue
                rebuild_records.append(record)
            embeddings = self.embedding_service.encode_documents([record.embedding_text for record in rebuild_records]) if rebuild_records else []
            for index, record in enumerate(rebuild_records):
                embedding = embeddings[index]
                self._upsert_record(connection, record=record, embedding=embedding)
                rebuilt_cards += 1
            connection.commit()
        finally:
            connection.close()
        return KnowledgeCardIndexBuildResult(
            total_cards=total_cards,
            rebuilt_cards=rebuilt_cards,
            skipped_cards=skipped_cards,
        )

    def delete_cards(self, *, app_id: str, card_ids: list[str]) -> int:
        if not card_ids:
            return 0
        connection = self.db.connect()
        try:
            deleted_count = self._delete_cards_by_ids(connection, app_id=app_id, card_ids=card_ids)
            connection.commit()
            return deleted_count
        finally:
            connection.close()

    def count_cards(self, *, app_id: str) -> int:
        connection = self.db.connect()
        try:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total_count
                FROM knowledge_cards
                WHERE app_id = ?
                """,
                (app_id,),
            ).fetchone()
            return int(row["total_count"]) if row is not None else 0
        finally:
            connection.close()

    def _is_cache_hit(self, connection, *, record) -> bool:  # noqa: ANN001
        content_hash = _record_content_hash(record)
        row = connection.execute(
            """
            SELECT content_hash, embedding_model_id, embedding_dim
            FROM knowledge_build_cache
            WHERE app_id = ? AND card_id = ?
            """,
            (record.app_id, record.card_id),
        ).fetchone()
        return (
            row is not None
            and row["content_hash"] == content_hash
            and row["embedding_model_id"] == self.embedding_service.model_id
            and int(row["embedding_dim"]) == int(self.embedding_service.embedding_dim)
        )

    @staticmethod
    def _reconcile_deleted_cards(connection, *, app_id: str, active_card_ids: set[str]) -> None:  # noqa: ANN001
        rows = connection.execute(
            """
            SELECT rowid, card_id
            FROM knowledge_cards
            WHERE app_id = ?
            """,
            (app_id,),
        ).fetchall()
        stale_rows = [row for row in rows if str(row["card_id"]) not in active_card_ids]
        if not stale_rows:
            return
        stale_card_ids = [str(row["card_id"]) for row in stale_rows]
        stale_rowids = [int(row["rowid"]) for row in stale_rows]
        _delete_card_rows(connection, app_id=app_id, stale_card_ids=stale_card_ids, stale_rowids=stale_rowids)

    def _upsert_record(self, connection, *, record, embedding) -> None:  # noqa: ANN001
        content_hash = _record_content_hash(record)
        connection.execute(
            """
            INSERT INTO knowledge_cards (
                app_id,
                card_id,
                card_type,
                title,
                status,
                confidence,
                updated_at,
                source_kind,
                source_ref,
                source_note,
                payload_json,
                flat_text,
                summary_text,
                content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(app_id, card_id) DO UPDATE SET
                card_type = excluded.card_type,
                title = excluded.title,
                status = excluded.status,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at,
                source_kind = excluded.source_kind,
                source_ref = excluded.source_ref,
                source_note = excluded.source_note,
                payload_json = excluded.payload_json,
                flat_text = excluded.flat_text,
                summary_text = excluded.summary_text,
                content_hash = excluded.content_hash
            """,
            (
                record.app_id,
                record.card_id,
                record.card_type,
                record.title,
                record.status,
                record.confidence,
                record.updated_at,
                record.source_kind,
                record.source_ref,
                record.source_note,
                record.payload_json,
                record.flat_text,
                record.summary_text,
                content_hash,
            ),
        )
        row = connection.execute(
            "SELECT rowid FROM knowledge_cards WHERE app_id = ? AND card_id = ?",
            (record.app_id, record.card_id),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"knowledge card upsert failed for {record.app_id}:{record.card_id}")
        card_rowid = int(row["rowid"])
        connection.execute(
            "DELETE FROM knowledge_cards_fts WHERE app_id = ? AND card_id = ?",
            (record.app_id, record.card_id),
        )
        connection.execute(
            """
            INSERT INTO knowledge_cards_fts(
                app_id,
                card_id,
                title,
                flat_text,
                summary_text,
                card_type,
                source_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.app_id,
                record.card_id,
                record.title,
                record.fts_text,
                record.summary_text,
                record.card_type,
                record.source_note or "",
            ),
        )
        connection.execute(
            "DELETE FROM knowledge_card_embeddings WHERE card_rowid = ?",
            (card_rowid,),
        )
        connection.execute(
            """
            INSERT INTO knowledge_card_embeddings(
                card_rowid,
                embedding,
                app_id,
                card_type
            ) VALUES (?, ?, ?, ?)
            """,
            (
                card_rowid,
                serialize_float32(embedding),
                record.app_id,
                record.card_type,
            ),
        )
        connection.execute(
            """
            INSERT INTO knowledge_build_cache(
                app_id,
                card_id,
                content_hash,
                embedding_model_id,
                embedding_dim,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(app_id, card_id) DO UPDATE SET
                content_hash = excluded.content_hash,
                embedding_model_id = excluded.embedding_model_id,
                embedding_dim = excluded.embedding_dim,
                updated_at = excluded.updated_at
            """,
            (
                record.app_id,
                record.card_id,
                content_hash,
                self.embedding_service.model_id,
                int(self.embedding_service.embedding_dim),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    @staticmethod
    def _delete_cards_by_ids(connection, *, app_id: str, card_ids: list[str]) -> int:  # noqa: ANN001
        rows = connection.execute(
            f"""
            SELECT rowid, card_id
            FROM knowledge_cards
            WHERE app_id = ? AND card_id IN ({", ".join("?" for _ in card_ids)})
            """,
            (app_id, *card_ids),
        ).fetchall()
        if not rows:
            return 0
        stale_card_ids = [str(row["card_id"]) for row in rows]
        stale_rowids = [int(row["rowid"]) for row in rows]
        _delete_card_rows(connection, app_id=app_id, stale_card_ids=stale_card_ids, stale_rowids=stale_rowids)
        return len(stale_card_ids)


def _record_content_hash(record) -> str:  # noqa: ANN001
    payload = "\n".join(
        [
            record.app_id,
            record.card_id,
            record.card_type,
            record.title,
            record.status,
            str(record.confidence),
            record.updated_at,
            record.source_kind,
            record.source_ref or "",
            record.source_note or "",
            record.payload_json,
            record.flat_text,
            record.fts_text,
            record.embedding_text,
            record.summary_text,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _delete_card_rows(connection, *, app_id: str, stale_card_ids: list[str], stale_rowids: list[int]) -> None:  # noqa: ANN001
    rowid_placeholders = ", ".join("?" for _ in stale_rowids)
    card_placeholders = ", ".join("?" for _ in stale_card_ids)
    connection.execute(
        f"DELETE FROM knowledge_card_embeddings WHERE card_rowid IN ({rowid_placeholders})",
        tuple(stale_rowids),
    )
    connection.execute(
        f"DELETE FROM knowledge_cards_fts WHERE app_id = ? AND card_id IN ({card_placeholders})",
        (app_id, *stale_card_ids),
    )
    connection.execute(
        f"DELETE FROM knowledge_build_cache WHERE app_id = ? AND card_id IN ({card_placeholders})",
        (app_id, *stale_card_ids),
    )
    connection.execute(
        f"DELETE FROM knowledge_cards WHERE app_id = ? AND card_id IN ({card_placeholders})",
        (app_id, *stale_card_ids),
    )
