from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from munk.app_knowledge import KnowledgeCandidateRecord


class CandidateApprovalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: KnowledgeCandidateRecord
    resolved_card_id: str
    build_manifest_path: str
    db_path: str
    rebuilt_cards: int
    skipped_cards: int
    cache_hit: bool = False


class CandidateRejectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: KnowledgeCandidateRecord
