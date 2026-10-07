from __future__ import annotations

import sqlite3
from pathlib import Path

from .constants import (
    DEFAULT_REVIEW_DB_NAME,
    DEFAULT_REVIEW_EMBEDDING_DIM,
    default_review_build_root,
    resolve_runtime_review_build_root,
)
from .sqlite_vec_compat import load_sqlite_vec


class ReviewKnowledgeDbError(RuntimeError):
    """Raised when the review knowledge database cannot be initialized."""


def default_review_db_path(
    source_root: Path | None = None,
    *,
    build_root: Path | None = None,
) -> Path:
    return default_review_build_root(source_root=source_root, build_root=build_root) / DEFAULT_REVIEW_DB_NAME


def resolve_runtime_review_db_path() -> Path:
    return resolve_runtime_review_build_root() / DEFAULT_REVIEW_DB_NAME


class ReviewKnowledgeDb:
    def __init__(self, db_path: Path | None = None, *, read_only: bool = False) -> None:
        self.db_path = db_path or default_review_db_path()
        self.read_only = read_only

    def connect(self) -> sqlite3.Connection:
        if self.read_only:
            connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        self._load_sqlite_vec(connection)
        if not self.read_only:
            self._initialize_schema(connection)
        return connection

    def _load_sqlite_vec(self, connection: sqlite3.Connection) -> None:
        enable_extension = getattr(connection, "enable_load_extension", None)
        if enable_extension is None:
            raise ReviewKnowledgeDbError(
                "current Python SQLite build does not support loadable extensions; sqlite-vec requires a Python/SQLite build with enable_load_extension()"
            )
        connection.enable_load_extension(True)
        try:
            load_sqlite_vec(connection)
        except Exception as exc:  # pragma: no cover - depends on local runtime
            raise ReviewKnowledgeDbError(f"failed to load sqlite-vec extension: {exc}") from exc
        finally:
            connection.enable_load_extension(False)

    def _initialize_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            f"""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS knowledge_cases (
                rowid INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL,
                domain TEXT NOT NULL,
                topic TEXT NOT NULL,
                case_type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                body_md TEXT NOT NULL,
                source_dir TEXT NOT NULL,
                manifest_path TEXT NOT NULL,
                body_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                code_languages_json TEXT NOT NULL,
                recommended_checks_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_case_tags (
                case_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (case_id, tag)
            );

            CREATE TABLE IF NOT EXISTS knowledge_build_cache (
                case_id TEXT NOT NULL PRIMARY KEY,
                content_hash TEXT NOT NULL,
                embedding_model_id TEXT NOT NULL,
                embedding_dim INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_cases_fts USING fts5(
                case_id UNINDEXED,
                title,
                summary,
                body_md,
                tags_text,
                recommended_checks_text
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_case_embeddings USING vec0(
                case_rowid INTEGER PRIMARY KEY,
                embedding float[{DEFAULT_REVIEW_EMBEDDING_DIM}] distance_metric=cosine,
                platform TEXT,
                domain TEXT,
                case_type TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_knowledge_cases_platform ON knowledge_cases(platform);
            CREATE INDEX IF NOT EXISTS idx_knowledge_cases_domain ON knowledge_cases(domain);
            CREATE INDEX IF NOT EXISTS idx_knowledge_cases_topic ON knowledge_cases(topic);
            CREATE INDEX IF NOT EXISTS idx_knowledge_cases_case_type ON knowledge_cases(case_type);
            CREATE INDEX IF NOT EXISTS idx_knowledge_case_tags_tag ON knowledge_case_tags(tag);
            """
        )
        connection.commit()
