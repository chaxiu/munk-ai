from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from .retrieval_primitives import build_fts_query, merge_ranked_candidates
from .sqlite_vec_compat import serialize_float32


class KnowledgeCardRetrievalService:
    def __init__(self, *, db, embedding_service) -> None:  # noqa: ANN001
        self.db = db
        self.embedding_service = embedding_service

    def search(
        self,
        *,
        app_id: str,
        query_text: str,
        card_types: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        connection = self.db.connect()
        try:
            filter_rows = self._run_filter_query(
                connection,
                app_id=app_id,
                query_text=query_text,
                card_types=card_types,
                limit=max(limit * 2, limit),
            )
            fts_rows = self._run_fts_query(
                connection,
                app_id=app_id,
                query_text=query_text,
                card_types=card_types,
                limit=max(limit * 2, limit),
            )
            vector_rows = self._run_vector_query(
                connection,
                app_id=app_id,
                query_text=query_text,
                card_types=card_types,
                limit=max(limit * 2, limit),
            )
        finally:
            connection.close()
        return merge_ranked_candidates(
            filter_rows=filter_rows,
            fts_rows=fts_rows,
            vector_rows=vector_rows,
            id_field="card_key",
            limit=limit,
        )

    def list_cards(
        self,
        *,
        app_id: str,
        card_type: str | None,
        status: str | None = None,
        query_text: str | None = None,
        limit: int,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        connection = self.db.connect()
        try:
            query = self._build_management_query(
                app_id=app_id,
                card_type=card_type,
                status=status,
                query_text=query_text,
                include_order=True,
            )
            rows = connection.execute(
                f"{query['sql']} LIMIT ? OFFSET ?",
                (*query["params"], limit, offset),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def count_cards(
        self,
        *,
        app_id: str,
        card_type: str | None = None,
        status: str | None = None,
        query_text: str | None = None,
    ) -> int:
        connection = self.db.connect()
        try:
            query = self._build_management_query(
                app_id=app_id,
                card_type=card_type,
                status=status,
                query_text=query_text,
                include_order=False,
            )
            row = connection.execute(
                f"SELECT COUNT(*) AS total_count FROM ({query['sql']})",
                tuple(query["params"]),
            ).fetchone()
            return int(row["total_count"]) if row is not None else 0
        finally:
            connection.close()

    def get_card(self, *, card_id: str, app_id: str | None = None) -> dict[str, Any] | None:
        connection = self.db.connect()
        try:
            if app_id is not None:
                row = connection.execute(
                    """
                    SELECT
                        app_id,
                        card_id,
                        app_id || ':' || card_id AS card_key,
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
                        summary_text
                    FROM knowledge_cards
                    WHERE app_id = ? AND card_id = ?
                    LIMIT 1
                    """,
                    (app_id, card_id),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT
                        app_id,
                        card_id,
                        app_id || ':' || card_id AS card_key,
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
                        summary_text
                    FROM knowledge_cards
                    WHERE card_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (card_id,),
                ).fetchone()
            return dict(row) if row is not None else None
        finally:
            connection.close()

    @staticmethod
    def _run_filter_query(
        connection,  # noqa: ANN001
        *,
        app_id: str,
        query_text: str,
        card_types: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses = ["app_id = ?"]
        params: list[Any] = [app_id]
        if card_types:
            placeholders = ", ".join("?" for _ in card_types)
            clauses.append(f"card_type IN ({placeholders})")
            params.extend(card_types)
        trimmed = query_text.strip()
        if trimmed:
            like = f"%{trimmed}%"
            clauses.append("(card_id LIKE ? OR title LIKE ? OR flat_text LIKE ?)")
            params.extend([like, like, like])
        rows = connection.execute(
            f"""
            SELECT
                app_id,
                card_id,
                app_id || ':' || card_id AS card_key,
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
                1.0 AS filter_score
            FROM knowledge_cards
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at DESC, title ASC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _run_fts_query(
        connection,  # noqa: ANN001
        *,
        app_id: str,
        query_text: str,
        card_types: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        fts_query = build_fts_query(query_text)
        if not fts_query:
            return []
        clauses = ["knowledge_cards_fts MATCH ?", "c.app_id = ?"]
        params: list[Any] = [fts_query, app_id]
        if card_types:
            placeholders = ", ".join("?" for _ in card_types)
            clauses.append(f"c.card_type IN ({placeholders})")
            params.extend(card_types)
        rows = connection.execute(
            f"""
            SELECT
                c.app_id,
                c.card_id,
                c.app_id || ':' || c.card_id AS card_key,
                c.card_type,
                c.title,
                c.status,
                c.confidence,
                c.updated_at,
                c.source_kind,
                c.source_ref,
                c.source_note,
                c.payload_json,
                c.flat_text,
                c.summary_text,
                bm25(knowledge_cards_fts) * -1.0 AS fts_score
            FROM knowledge_cards_fts
            JOIN knowledge_cards c ON c.app_id = knowledge_cards_fts.app_id AND c.card_id = knowledge_cards_fts.card_id
            WHERE {' AND '.join(clauses)}
            ORDER BY fts_score DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def _run_vector_query(
        self,
        connection,  # noqa: ANN001
        *,
        app_id: str,
        query_text: str,
        card_types: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        trimmed = query_text.strip()
        if not trimmed:
            return []
        query_embedding = self.embedding_service.encode_query(trimmed)
        clauses = ["embedding MATCH ?", "k = ?", "app_id = ?"]
        params: list[Any] = [serialize_float32(query_embedding), limit, app_id]
        if card_types:
            placeholders = ", ".join("?" for _ in card_types)
            clauses.append(f"card_type IN ({placeholders})")
            params.extend(card_types)
        rows = connection.execute(
            f"""
            WITH vector_hits AS (
                SELECT
                    card_rowid,
                    distance
                FROM knowledge_card_embeddings
                WHERE {' AND '.join(clauses)}
                ORDER BY distance
            )
            SELECT
                c.app_id,
                c.card_id,
                c.app_id || ':' || c.card_id AS card_key,
                c.card_type,
                c.title,
                c.status,
                c.confidence,
                c.updated_at,
                c.source_kind,
                c.source_ref,
                c.source_note,
                c.payload_json,
                c.flat_text,
                c.summary_text,
                vector_hits.distance AS vector_distance
            FROM vector_hits
            JOIN knowledge_cards c ON c.rowid = vector_hits.card_rowid
            ORDER BY vector_hits.distance ASC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _build_management_query(
        *,
        app_id: str,
        card_type: str | None,
        status: str | None,
        query_text: str | None,
        include_order: bool,
    ) -> dict[str, Any]:
        ctes: list[str] = []
        joins: list[str] = []
        clauses = ["c.app_id = ?"]
        params: list[Any] = [app_id]
        trimmed = (query_text or "").strip()

        if trimmed:
            fts_query = build_fts_query(trimmed)
            if fts_query:
                ctes.append(
                    """
                    fts_hits AS (
                        SELECT app_id, card_id, bm25(knowledge_cards_fts) * -1.0 AS fts_score
                        FROM knowledge_cards_fts
                        WHERE knowledge_cards_fts MATCH ? AND app_id = ?
                    )
                    """
                )
                params = [fts_query, app_id, *params]
                joins.append("LEFT JOIN fts_hits f ON f.app_id = c.app_id AND f.card_id = c.card_id")
            else:
                joins.append("LEFT JOIN (SELECT NULL AS app_id, NULL AS card_id, NULL AS fts_score) f ON 1 = 0")
            like = f"%{trimmed}%"
            clauses.append("(c.card_id LIKE ? OR c.title LIKE ? OR c.flat_text LIKE ? OR f.card_id IS NOT NULL)")
            params.extend([like, like, like])
        else:
            joins.append("LEFT JOIN (SELECT NULL AS app_id, NULL AS card_id, NULL AS fts_score) f ON 1 = 0")

        if card_type is not None:
            clauses.append("c.card_type = ?")
            params.append(card_type)
        if status is not None:
            clauses.append("c.status = ?")
            params.append(status)

        with_clause = f"WITH {', '.join(ctes)} " if ctes else ""
        sql = f"""
            {with_clause}
            SELECT
                c.app_id,
                c.card_id,
                c.app_id || ':' || c.card_id AS card_key,
                c.card_type,
                c.title,
                c.status,
                c.confidence,
                c.updated_at,
                c.source_kind,
                c.source_ref,
                c.source_note,
                c.payload_json,
                c.flat_text,
                c.summary_text,
                COALESCE(f.fts_score, 0.0) AS fts_score
            FROM knowledge_cards c
            {' '.join(joins)}
            WHERE {' AND '.join(clauses)}
        """
        if include_order:
            sql += """
            ORDER BY
                CASE WHEN f.card_id IS NOT NULL THEN 0 ELSE 1 END ASC,
                COALESCE(f.fts_score, 0.0) DESC,
                c.updated_at DESC,
                c.title ASC
            """
        return {"sql": sql, "params": params}


def row_to_knowledge_card_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "card_id": row["card_id"],
        "app_id": row["app_id"],
        "title": row["title"],
        "card_type": row["card_type"],
        "status": row["status"],
        "confidence": row["confidence"],
        "updated_at": row["updated_at"],
        "source": {
            "kind": row["source_kind"],
            "ref": row.get("source_ref"),
            "note": row.get("source_note"),
        },
        "payload": json.loads(row["payload_json"]),
    }
