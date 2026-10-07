from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import TypeAdapter

from .build_models import AppKnowledgeBuildResult
from .card_id import generate_candidate_card_id
from .document_loader import load_app_knowledge_document, save_app_knowledge_document
from .index_sync_service import AppKnowledgeIndexSyncService
from .models import AppKnowledgeImportDocument, KnowledgeCandidateDraft, KnowledgeCard

_KNOWLEDGE_CARD_ADAPTER = TypeAdapter(KnowledgeCard)


@dataclass(frozen=True)
class CandidateMergeResult:
    document: AppKnowledgeImportDocument
    resolved_card_id: str
    replaced_existing: bool
    build_result: AppKnowledgeBuildResult


class AppKnowledgeApprovalService:
    def __init__(self, *, assets_root: Path, knowledge_ref: str | None = None) -> None:
        self.assets_root = assets_root
        self.knowledge_ref = knowledge_ref
        self.index_sync_service = AppKnowledgeIndexSyncService(assets_root=assets_root)

    def merge_candidate(
        self,
        *,
        app_id: str,
        candidate: KnowledgeCandidateDraft,
        review_note: str | None = None,
    ) -> CandidateMergeResult:
        document = load_app_knowledge_document(
            app_id,
            assets_root=self.assets_root,
            ref=self.knowledge_ref,
        ) or AppKnowledgeImportDocument(app_id=app_id, cards=[])
        resolved_card_id = candidate.card_id or generate_candidate_card_id(
            card_type=candidate.card_type,
            title=candidate.title,
            existing_cards=list(document.cards),
        )
        materialized = self._materialize_card(
            candidate=candidate,
            resolved_card_id=resolved_card_id,
            review_note=review_note,
        )
        next_cards: list[KnowledgeCard] = []
        replaced_existing = False
        for card in document.cards:
            if card.card_id == resolved_card_id:
                next_cards.append(materialized)
                replaced_existing = True
            else:
                next_cards.append(card)
        if not replaced_existing:
            next_cards.append(materialized)
        next_document = AppKnowledgeImportDocument(
            schema_version=document.schema_version,
            app_id=app_id,
            cards=next_cards,
        )
        save_app_knowledge_document(next_document, assets_root=self.assets_root, ref=self.knowledge_ref)
        build_result = self.index_sync_service.upsert_cards(
            app_id=app_id,
            schema_version=next_document.schema_version,
            cards=[materialized],
            total_cards=len(next_document.cards),
            ref=self.knowledge_ref,
        )
        return CandidateMergeResult(
            document=next_document,
            resolved_card_id=resolved_card_id,
            replaced_existing=replaced_existing,
            build_result=build_result,
        )

    @staticmethod
    def _materialize_card(
        *,
        candidate: KnowledgeCandidateDraft,
        resolved_card_id: str,
        review_note: str | None,
    ) -> KnowledgeCard:
        source_payload = candidate.source.model_dump(mode="json")
        source_note = source_payload.get("note")
        merge_context = review_note.strip() if review_note else ""
        if merge_context and source_note:
            source_payload["note"] = f"{source_note}; approval_note={merge_context}"
        elif merge_context:
            source_payload["note"] = f"approval_note={merge_context}"
        payload = candidate.model_dump(mode="json")
        payload.update(
            {
                "card_id": resolved_card_id,
                "status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": source_payload,
            }
        )
        return _KNOWLEDGE_CARD_ADAPTER.validate_python(payload)
