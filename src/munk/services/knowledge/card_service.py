from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from munk_knowledge_local import KnowledgeCardDb, KnowledgeCardRetrievalService, row_to_knowledge_card_payload
from pydantic import TypeAdapter

from munk.app_assets.models import AppProfile
from munk.app_assets.storage import AppRegistry
from munk.app_knowledge import (
    AppKnowledgeBuildResult,
    AppKnowledgeImportDocument,
    AppKnowledgeIndexSyncService,
    KnowledgeCard,
    KnowledgeCardInput,
    KnowledgeCardStatus,
    KnowledgeCardType,
    build_app_knowledge_index,
    generate_candidate_card_id,
    load_app_knowledge_document,
    resolve_app_knowledge_build_paths,
    save_app_knowledge_document,
)

_KNOWLEDGE_CARD_ADAPTER = TypeAdapter(KnowledgeCard)


@dataclass(frozen=True)
class KnowledgeCardListResult:
    items: list[KnowledgeCard]
    total_count: int
    limit: int
    offset: int


@dataclass(frozen=True)
class KnowledgeCardMutationResult:
    card: KnowledgeCard
    build_result: AppKnowledgeBuildResult


@dataclass(frozen=True)
class KnowledgeCardDeleteResult:
    deleted_card_id: str
    build_result: AppKnowledgeBuildResult


class KnowledgeCardService:
    def __init__(self, *, assets_root: Path) -> None:
        self.assets_root = assets_root
        self.registry = AppRegistry(root_dir=assets_root)
        self.index_sync_service = AppKnowledgeIndexSyncService(assets_root=assets_root)

    def list_cards(
        self,
        *,
        app_id: str,
        query: str | None = None,
        card_type: KnowledgeCardType | None = None,
        status: KnowledgeCardStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> KnowledgeCardListResult:
        profile = self._load_profile(app_id)
        retrieval = self._build_retrieval_service(profile)
        items = [
            _KNOWLEDGE_CARD_ADAPTER.validate_python(row_to_knowledge_card_payload(row))
            for row in retrieval.list_cards(
                app_id=profile.app_id,
                card_type=card_type,
                status=status,
                query_text=query,
                limit=limit,
                offset=offset,
            )
        ]
        total_count = retrieval.count_cards(
            app_id=profile.app_id,
            card_type=card_type,
            status=status,
            query_text=query,
        )
        return KnowledgeCardListResult(
            items=items,
            total_count=total_count,
            limit=limit,
            offset=offset,
        )

    def get_card(self, *, app_id: str, card_id: str) -> KnowledgeCard:
        profile = self._load_profile(app_id)
        normalized_card_id = card_id.strip()
        if not normalized_card_id:
            raise ValueError("card_id must not be empty")
        retrieval = self._build_retrieval_service(profile)
        row = retrieval.get_card(app_id=profile.app_id, card_id=normalized_card_id)
        if row is not None:
            return _KNOWLEDGE_CARD_ADAPTER.validate_python(row_to_knowledge_card_payload(row))
        raise FileNotFoundError(f"card '{normalized_card_id}' not found for app '{profile.app_id}'")

    def create_card(self, *, app_id: str, card: KnowledgeCardInput) -> KnowledgeCardMutationResult:
        profile = self._load_profile(app_id)
        document = self._load_document(profile)
        self._validate_input_app_id(app_id=profile.app_id, card=card)
        resolved_card_id = card.card_id or generate_candidate_card_id(
            card_type=card.card_type,
            title=card.title,
            existing_cards=list(document.cards),
        )
        if any(existing.card_id == resolved_card_id for existing in document.cards):
            raise ValueError(f"card '{resolved_card_id}' already exists for app '{profile.app_id}'")
        materialized = self._materialize_card(card=card, resolved_card_id=resolved_card_id)
        next_document = AppKnowledgeImportDocument(
            schema_version=document.schema_version,
            app_id=profile.app_id,
            cards=[*document.cards, materialized],
        )
        return self._save_document(profile=profile, document=next_document, card=materialized)

    def update_card(
        self,
        *,
        app_id: str,
        card_id: str,
        card: KnowledgeCardInput,
    ) -> KnowledgeCardMutationResult:
        profile = self._load_profile(app_id)
        document = self._load_document(profile)
        normalized_card_id = card_id.strip()
        if not normalized_card_id:
            raise ValueError("card_id must not be empty")
        self._validate_input_app_id(app_id=profile.app_id, card=card)
        if card.card_id is not None and card.card_id != normalized_card_id:
            raise ValueError("request card_id must match path card_id when provided")
        materialized = self._materialize_card(card=card, resolved_card_id=normalized_card_id)
        next_cards: list[KnowledgeCard] = []
        replaced = False
        for existing in document.cards:
            if existing.card_id == normalized_card_id:
                next_cards.append(materialized)
                replaced = True
            else:
                next_cards.append(existing)
        if not replaced:
            raise FileNotFoundError(f"card '{normalized_card_id}' not found for app '{profile.app_id}'")
        next_document = AppKnowledgeImportDocument(
            schema_version=document.schema_version,
            app_id=profile.app_id,
            cards=next_cards,
        )
        return self._save_document(profile=profile, document=next_document, card=materialized)

    def delete_card(self, *, app_id: str, card_id: str) -> KnowledgeCardDeleteResult:
        profile = self._load_profile(app_id)
        document = self._load_document(profile)
        normalized_card_id = card_id.strip()
        if not normalized_card_id:
            raise ValueError("card_id must not be empty")
        next_cards = [card for card in document.cards if card.card_id != normalized_card_id]
        if len(next_cards) == len(document.cards):
            raise FileNotFoundError(f"card '{normalized_card_id}' not found for app '{profile.app_id}'")
        next_document = AppKnowledgeImportDocument(
            schema_version=document.schema_version,
            app_id=profile.app_id,
            cards=next_cards,
        )
        save_app_knowledge_document(
            next_document,
            assets_root=self.assets_root,
            ref=profile.app_knowledge_ref,
        )
        build_result = self.index_sync_service.delete_cards(
            app_id=profile.app_id,
            schema_version=next_document.schema_version,
            card_ids=[normalized_card_id],
            total_cards=len(next_cards),
            ref=profile.app_knowledge_ref,
        )
        return KnowledgeCardDeleteResult(
            deleted_card_id=normalized_card_id,
            build_result=build_result,
        )

    def _load_profile(self, app_id: str) -> AppProfile:
        return self.registry.load(app_id)

    def _load_document(self, profile: AppProfile) -> AppKnowledgeImportDocument:
        return load_app_knowledge_document(
            profile.app_id,
            assets_root=self.assets_root,
            ref=profile.app_knowledge_ref,
        ) or AppKnowledgeImportDocument(app_id=profile.app_id, cards=[])

    def _save_document(
        self,
        *,
        profile: AppProfile,
        document: AppKnowledgeImportDocument,
        card: KnowledgeCard,
    ) -> KnowledgeCardMutationResult:
        save_app_knowledge_document(
            document,
            assets_root=self.assets_root,
            ref=profile.app_knowledge_ref,
        )
        build_result = self.index_sync_service.upsert_cards(
            app_id=profile.app_id,
            schema_version=document.schema_version,
            cards=[card],
            total_cards=len(document.cards),
            ref=profile.app_knowledge_ref,
        )
        return KnowledgeCardMutationResult(card=card, build_result=build_result)

    @staticmethod
    def _validate_input_app_id(*, app_id: str, card: KnowledgeCardInput) -> None:
        if card.app_id != app_id:
            raise ValueError("card.app_id must match path app_id")

    @staticmethod
    def _materialize_card(*, card: KnowledgeCardInput, resolved_card_id: str) -> KnowledgeCard:
        payload = card.model_dump(mode="json")
        payload.update(
            {
                "card_id": resolved_card_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return _KNOWLEDGE_CARD_ADAPTER.validate_python(payload)

    def _build_retrieval_service(self, profile: AppProfile) -> KnowledgeCardRetrievalService:
        self._ensure_index_ready(profile)
        paths = resolve_app_knowledge_build_paths(assets_root=self.assets_root, app_id=profile.app_id)
        return KnowledgeCardRetrievalService(
            db=KnowledgeCardDb(
                paths.db_path,
                read_only=True,
                embedding_dim=int(self.index_sync_service.embedding_service.embedding_dim),
            ),
            embedding_service=self.index_sync_service.embedding_service,
        )

    def _ensure_index_ready(self, profile: AppProfile) -> None:
        paths = resolve_app_knowledge_build_paths(assets_root=self.assets_root, app_id=profile.app_id)
        if paths.db_path.exists() and paths.build_manifest_path.exists():
            return
        build_app_knowledge_index(
            app_id=profile.app_id,
            assets_root=self.assets_root,
            ref=profile.app_knowledge_ref,
            embedding_service=self.index_sync_service.embedding_service,
        )
