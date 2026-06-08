from __future__ import annotations


class KnowledgeEmbeddingError(RuntimeError):
    """Raised when the local knowledge embedding model cannot be loaded or used."""


class KnowledgeDbError(RuntimeError):
    """Raised when the knowledge database cannot be initialized."""
