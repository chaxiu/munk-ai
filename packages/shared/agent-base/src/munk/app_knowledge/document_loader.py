from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import AppKnowledgeImportDocument


class KnowledgeDocumentError(ValueError):
    """Raised when app knowledge content cannot be parsed as a knowledge document."""


def parse_app_knowledge_document(raw: str | None) -> AppKnowledgeImportDocument:
    if raw is None or not raw.strip():
        raise KnowledgeDocumentError("app knowledge content must not be empty")
    cleaned = raw.strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise KnowledgeDocumentError("app knowledge content must be valid JSON") from exc
    try:
        return AppKnowledgeImportDocument.model_validate(payload)
    except ValidationError as exc:
        raise KnowledgeDocumentError(f"app knowledge content does not match AppKnowledgeImportDocument: {exc}") from exc


def validate_app_knowledge_document(
    raw: str,
    *,
    expected_app_id: str | None = None,
) -> AppKnowledgeImportDocument:
    document = parse_app_knowledge_document(raw)
    if expected_app_id is not None and document.app_id != expected_app_id.strip():
        raise KnowledgeDocumentError(
            f"app knowledge document app_id mismatch: expected {expected_app_id.strip()}, got {document.app_id}"
        )
    return document


def app_knowledge_path(assets_root: Path, app_id: str, *, ref: str | None = None) -> Path:
    return assets_root / "apps" / app_id.strip() / (ref or "app_knowledge.json")


def load_app_knowledge_document(
    app_id: str,
    *,
    assets_root: Path,
    ref: str | None = None,
) -> AppKnowledgeImportDocument | None:
    path = app_knowledge_path(assets_root, app_id, ref=ref)
    if not path.exists() or not path.is_file():
        return None
    return validate_app_knowledge_document(path.read_text(encoding="utf-8"), expected_app_id=app_id)


def save_app_knowledge_document(
    document: AppKnowledgeImportDocument,
    *,
    assets_root: Path,
    ref: str | None = None,
) -> Path:
    path = app_knowledge_path(assets_root, document.app_id, ref=ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    return path
