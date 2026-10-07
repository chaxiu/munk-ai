from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .constants import (
    DEFAULT_REVIEW_BUILD_MANIFEST_NAME,
    DEFAULT_REVIEW_EMBEDDING_DIM,
    default_review_build_root,
)
from .embedding_service import ReviewEmbeddingService
from .knowledge_db import ReviewKnowledgeDb, default_review_db_path
from .knowledge_models import KnowledgeCaseDocument
from .knowledge_source import KnowledgeSourceLoader, review_knowledge_root
from .sqlite_vec_compat import serialize_float32


@dataclass(frozen=True)
class ReviewKnowledgeBuildResult:
    db_path: Path
    build_manifest_path: Path
    total_cases: int
    rebuilt_cases: int
    skipped_cases: int


class ReviewKnowledgeBuildService:
    def __init__(
        self,
        *,
        root_dir: Path | None = None,
        build_root: Path | None = None,
        db: ReviewKnowledgeDb | None = None,
        loader: KnowledgeSourceLoader | None = None,
        embedding_service: ReviewEmbeddingService | None = None,
    ) -> None:
        self.root_dir = review_knowledge_root(root_dir)
        self.build_root = default_review_build_root(source_root=self.root_dir if root_dir is not None else None, build_root=build_root)
        self.db = db or ReviewKnowledgeDb(
            default_review_db_path(
                self.root_dir if root_dir is not None else None,
                build_root=self.build_root,
            )
        )
        self.loader = loader or KnowledgeSourceLoader(self.root_dir)
        self.embedding_service = embedding_service or ReviewEmbeddingService()

    def build(self) -> ReviewKnowledgeBuildResult:
        documents = self.loader.load_all()
        active_case_ids = {document.case_id for document in documents}
        connection = self.db.connect()
        rebuilt_cases = 0
        skipped_cases = 0
        try:
            self._reconcile_deleted_cases(connection, active_case_ids)
            for document in documents:
                if self._is_cache_hit(connection, document):
                    skipped_cases += 1
                    continue
                self._upsert_document(connection, document)
                rebuilt_cases += 1
            connection.commit()
        finally:
            connection.close()
        build_manifest_path = self.build_root / DEFAULT_REVIEW_BUILD_MANIFEST_NAME
        self._write_build_manifest(
            build_manifest_path,
            total_cases=len(documents),
            rebuilt_cases=rebuilt_cases,
            skipped_cases=skipped_cases,
        )
        return ReviewKnowledgeBuildResult(
            db_path=self.db.db_path,
            build_manifest_path=build_manifest_path,
            total_cases=len(documents),
            rebuilt_cases=rebuilt_cases,
            skipped_cases=skipped_cases,
        )

    def _is_cache_hit(self, connection, document: KnowledgeCaseDocument) -> bool:  # noqa: ANN001
        row = connection.execute(
            """
            SELECT content_hash, embedding_model_id, embedding_dim
            FROM knowledge_build_cache
            WHERE case_id = ?
            """,
            (document.case_id,),
        ).fetchone()
        return (
            row is not None
            and row["content_hash"] == document.content_hash
            and row["embedding_model_id"] == self.embedding_service.model_id
            and int(row["embedding_dim"]) == DEFAULT_REVIEW_EMBEDDING_DIM
        )

    @staticmethod
    def _reconcile_deleted_cases(connection, active_case_ids: set[str]) -> None:  # noqa: ANN001
        rows = connection.execute(
            """
            SELECT rowid, case_id
            FROM knowledge_cases
            """
        ).fetchall()
        stale_rows = [row for row in rows if row["case_id"] not in active_case_ids]
        if not stale_rows:
            return
        stale_case_ids = [str(row["case_id"]) for row in stale_rows]
        stale_rowids = [int(row["rowid"]) for row in stale_rows]
        case_placeholders = ", ".join("?" for _ in stale_case_ids)
        rowid_placeholders = ", ".join("?" for _ in stale_rowids)
        connection.execute(
            f"DELETE FROM knowledge_case_embeddings WHERE case_rowid IN ({rowid_placeholders})",
            tuple(stale_rowids),
        )
        for table_name in ("knowledge_cases_fts", "knowledge_case_tags", "knowledge_build_cache", "knowledge_cases"):
            connection.execute(
                f"DELETE FROM {table_name} WHERE case_id IN ({case_placeholders})",
                tuple(stale_case_ids),
            )

    def _upsert_document(self, connection, document: KnowledgeCaseDocument) -> None:  # noqa: ANN001
        embedding_text = self._build_embedding_text(document)
        embedding = self.embedding_service.encode_documents([embedding_text])[0]
        payload = document.manifest
        cursor = connection.execute(
            """
            INSERT INTO knowledge_cases (
                case_id,
                platform,
                domain,
                topic,
                case_type,
                title,
                summary,
                body_md,
                source_dir,
                manifest_path,
                body_path,
                content_hash,
                tags_json,
                code_languages_json,
                recommended_checks_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                platform = excluded.platform,
                domain = excluded.domain,
                topic = excluded.topic,
                case_type = excluded.case_type,
                title = excluded.title,
                summary = excluded.summary,
                body_md = excluded.body_md,
                source_dir = excluded.source_dir,
                manifest_path = excluded.manifest_path,
                body_path = excluded.body_path,
                content_hash = excluded.content_hash,
                tags_json = excluded.tags_json,
                code_languages_json = excluded.code_languages_json,
                recommended_checks_json = excluded.recommended_checks_json
            """,
            (
                payload.case_id,
                payload.platform,
                payload.domain,
                payload.topic,
                payload.case_type,
                payload.title,
                payload.summary,
                document.body_md,
                str(document.source_dir),
                str(document.manifest_path),
                str(document.body_path),
                document.content_hash,
                json.dumps(payload.tags, ensure_ascii=False),
                json.dumps(payload.code_languages, ensure_ascii=False),
                json.dumps(payload.recommended_checks, ensure_ascii=False),
            ),
        )
        row = connection.execute(
            "SELECT rowid FROM knowledge_cases WHERE case_id = ?",
            (payload.case_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"knowledge case upsert failed for {payload.case_id}")
        case_rowid = int(row["rowid"])
        del cursor
        connection.execute("DELETE FROM knowledge_case_tags WHERE case_id = ?", (payload.case_id,))
        connection.executemany(
            "INSERT INTO knowledge_case_tags(case_id, tag) VALUES (?, ?)",
            [(payload.case_id, tag) for tag in payload.tags],
        )
        connection.execute("DELETE FROM knowledge_cases_fts WHERE case_id = ?", (payload.case_id,))
        connection.execute(
            """
            INSERT INTO knowledge_cases_fts(
                case_id,
                title,
                summary,
                body_md,
                tags_text,
                recommended_checks_text
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.case_id,
                payload.title,
                payload.summary,
                document.body_md,
                " ".join(payload.tags),
                " ".join(payload.recommended_checks),
            ),
        )
        connection.execute(
            "DELETE FROM knowledge_case_embeddings WHERE case_rowid = ?",
            (case_rowid,),
        )
        connection.execute(
            """
            INSERT INTO knowledge_case_embeddings(
                case_rowid,
                embedding,
                platform,
                domain,
                case_type
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                case_rowid,
                serialize_float32(embedding),
                payload.platform,
                payload.domain,
                payload.case_type,
            ),
        )
        connection.execute(
            """
            INSERT INTO knowledge_build_cache(
                case_id,
                content_hash,
                embedding_model_id,
                embedding_dim,
                updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                content_hash = excluded.content_hash,
                embedding_model_id = excluded.embedding_model_id,
                embedding_dim = excluded.embedding_dim,
                updated_at = excluded.updated_at
            """,
            (
                payload.case_id,
                document.content_hash,
                self.embedding_service.model_id,
                DEFAULT_REVIEW_EMBEDDING_DIM,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    @staticmethod
    def _build_embedding_text(document: KnowledgeCaseDocument) -> str:
        manifest = document.manifest
        parts = [
            manifest.platform,
            manifest.domain,
            manifest.topic,
            manifest.case_type,
            manifest.title,
            manifest.summary,
            " ".join(manifest.tags),
            " ".join(manifest.recommended_checks),
            document.body_md,
        ]
        return "\n".join(part for part in parts if part.strip())

    @staticmethod
    def _write_build_manifest(
        path: Path,
        *,
        total_cases: int,
        rebuilt_cases: int,
        skipped_cases: int,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_cases": total_cases,
                    "rebuilt_cases": rebuilt_cases,
                    "skipped_cases": skipped_cases,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
