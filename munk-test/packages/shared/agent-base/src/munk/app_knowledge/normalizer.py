from __future__ import annotations

import json

from .build_models import NormalizedKnowledgeCardRecord
from .models import AppKnowledgeImportDocument, KnowledgeCard
from .repository import flatten_knowledge_card_text, render_knowledge_card_summary


def normalize_app_knowledge_document(document: AppKnowledgeImportDocument) -> list[NormalizedKnowledgeCardRecord]:
    return [normalize_knowledge_card(card) for card in document.cards]


def normalize_knowledge_card(card: KnowledgeCard) -> NormalizedKnowledgeCardRecord:
    payload_json = json.dumps(card.payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    flat_text = flatten_knowledge_card_text(card)
    fts_text = _build_fts_text(card)
    embedding_text = _build_embedding_text(card)
    summary_text = render_knowledge_card_summary(card)
    return NormalizedKnowledgeCardRecord(
        app_id=card.app_id,
        card_id=card.card_id,
        card_type=card.card_type,
        title=card.title,
        status=card.status,
        confidence=card.confidence,
        updated_at=card.updated_at,
        source_kind=card.source.kind,
        source_ref=card.source.ref,
        source_note=card.source.note,
        payload_json=payload_json,
        flat_text=flat_text,
        fts_text=fts_text,
        embedding_text=embedding_text,
        summary_text=summary_text,
    )


def _build_fts_text(card: KnowledgeCard) -> str:
    parts = [
        card.card_id,
        card.title,
        card.card_type,
        card.source.ref or "",
        card.source.note or "",
        json.dumps(card.payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
    ]
    return "\n".join(part.strip() for part in parts if part and part.strip())


def _build_embedding_text(card: KnowledgeCard) -> str:
    payload = card.payload.model_dump(mode="json")
    parts = [
        f"app_id: {card.app_id}",
        f"card_id: {card.card_id}",
        f"card_type: {card.card_type}",
        f"title: {card.title}",
        f"status: {card.status}",
        f"source_kind: {card.source.kind}",
    ]
    if card.source.ref:
        parts.append(f"source_ref: {card.source.ref}")
    if card.source.note:
        parts.append(f"source_note: {card.source.note}")
    for key, value in payload.items():
        parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(parts)
