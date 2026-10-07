from __future__ import annotations

import sqlite3
from pathlib import Path

from .constants import DEFAULT_APP_KNOWLEDGE_EMBEDDING_DIM
from .sqlite_vec_compat import load_sqlite_vec


class KnowledgeCardDbError(RuntimeError):
    """Raised when the app knowledge database cannot be initialized."""


class KnowledgeCardDb:
    def __init__(self, db_path: Path, *, read_only: bool = False, embedding_dim: int = DEFAULT_APP_KNOWLEDGE_EMBEDDING_DIM) -> None:
        self.db_path = db_path
        self.read_only = read_only
        self.embedding_dim = embedding_dim

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
            raise KnowledgeCardDbError(
                "current Python SQLite build does not support loadable extensions; sqlite-vec requires enable_load_extension()"
            )
        connection.enable_load_extension(True)
        try:
            load_sqlite_vec(connection)
        except Exception as exc:  # pragma: no cover - depends on local runtime
            raise KnowledgeCardDbError(f"failed to load sqlite-vec extension: {exc}") from exc
        finally:
            connection.enable_load_extension(False)

    def _initialize_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            f"""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS knowledge_cards (
                rowid INTEGER PRIMARY KEY,
                app_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                card_type TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                confidence REAL NOT NULL,
                updated_at TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_ref TEXT,
                source_note TEXT,
                payload_json TEXT NOT NULL,
                flat_text TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                UNIQUE(app_id, card_id)
            );

            CREATE TABLE IF NOT EXISTS knowledge_build_cache (
                app_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding_model_id TEXT NOT NULL,
                embedding_dim INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (app_id, card_id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_cards_fts USING fts5(
                app_id UNINDEXED,
                card_id UNINDEXED,
                title,
                flat_text,
                summary_text,
                card_type,
                source_note
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_card_embeddings USING vec0(
                card_rowid INTEGER PRIMARY KEY,
                embedding float[{self.embedding_dim}] distance_metric=cosine,
                app_id TEXT,
                card_type TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_knowledge_cards_app_id ON knowledge_cards(app_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_cards_card_type ON knowledge_cards(card_type);
            CREATE INDEX IF NOT EXISTS idx_knowledge_cards_app_type ON knowledge_cards(app_id, card_type);
            """
        )
        connection.commit()
