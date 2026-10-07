from __future__ import annotations

from munk.app_assets.storage import AppRegistry
from munk.app_knowledge import (
    KnowledgeDocumentError,
    parse_app_knowledge_document,
    validate_app_knowledge_document,
)


def load_app_knowledge_document(
    app_id: str,
    *,
    registry: AppRegistry,
    ref: str | None = None,
):
    try:
        raw = registry.load_knowledge(app_id, ref=ref)
    except FileNotFoundError:
        return None
    return validate_app_knowledge_document(raw, expected_app_id=app_id)


__all__ = [
    "KnowledgeDocumentError",
    "load_app_knowledge_document",
    "parse_app_knowledge_document",
    "validate_app_knowledge_document",
]
