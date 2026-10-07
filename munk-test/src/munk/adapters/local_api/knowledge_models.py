from __future__ import annotations

from pydantic import BaseModel, Field

from munk.app_knowledge import KnowledgeCandidateRecord, KnowledgeCard, KnowledgeCardInput


class KnowledgeCandidateListData(BaseModel):
    items: list[KnowledgeCandidateRecord] = Field(default_factory=list)
    total_count: int = 0


class KnowledgeCandidateDecisionRequest(BaseModel):
    reviewed_by: str | None = None
    review_note: str | None = None


class KnowledgeCandidateApproveData(BaseModel):
    candidate: KnowledgeCandidateRecord
    resolved_card_id: str
    build_manifest_path: str
    db_path: str
    rebuilt_cards: int
    skipped_cards: int
    cache_hit: bool = False


class KnowledgeCandidateRejectData(BaseModel):
    candidate: KnowledgeCandidateRecord


class KnowledgeCardListData(BaseModel):
    items: list[KnowledgeCard] = Field(default_factory=list)
    total_count: int = 0
    limit: int = 0
    offset: int = 0


class KnowledgeCardGetData(BaseModel):
    card: KnowledgeCard


class KnowledgeCardWriteRequest(BaseModel):
    card: KnowledgeCardInput


class KnowledgeCardMutationData(BaseModel):
    card: KnowledgeCard
    build_manifest_path: str
    db_path: str
    total_cards: int
    rebuilt_cards: int
    skipped_cards: int
    cache_hit: bool = False


class KnowledgeCardDeleteData(BaseModel):
    deleted_card_id: str
    build_manifest_path: str
    db_path: str
    total_cards: int
    rebuilt_cards: int
    skipped_cards: int
    cache_hit: bool = False
