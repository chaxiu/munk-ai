from __future__ import annotations

from pathlib import Path

from munk.app_assets.storage import AppRegistry
from munk.app_knowledge import (
    AppKnowledgeApprovalService,
    KnowledgeCandidateApproveRequest,
    KnowledgeCandidateListOutput,
    KnowledgeCandidateListRequest,
    KnowledgeCandidateQuery,
    KnowledgeCandidateRejectRequest,
    KnowledgeReviewDecision,
    LocalKnowledgeCandidateStore,
)

from .approval_models import CandidateApprovalResult, CandidateRejectionResult


class KnowledgeCandidateApprovalService:
    def __init__(self, *, assets_root: Path) -> None:
        self.assets_root = assets_root
        self.registry = AppRegistry(root_dir=assets_root)
        self.store = LocalKnowledgeCandidateStore(root_dir=assets_root)

    def list_candidates(
        self,
        *,
        app_id: str,
        status: str | None = None,
        candidate_id: str | None = None,
        limit: int = 20,
    ) -> KnowledgeCandidateListOutput:
        self._load_profile(app_id)
        query = KnowledgeCandidateQuery(status=status, candidate_id=candidate_id, limit=limit)
        items = self.store.list_records(app_id, query=query)
        return KnowledgeCandidateListOutput(items=items, total_count=len(items))

    def approve_candidate(
        self,
        *,
        app_id: str,
        candidate_id: str,
        reviewed_by: str | None = None,
        review_note: str | None = None,
    ) -> CandidateApprovalResult:
        profile = self._load_profile(app_id)
        record = self.store.get_record(app_id, candidate_id)
        if record is None:
            raise FileNotFoundError(f"candidate '{candidate_id}' not found for app '{app_id}'")
        approval_service = AppKnowledgeApprovalService(
            assets_root=self.assets_root,
            knowledge_ref=profile.app_knowledge_ref,
        )
        merge_result = approval_service.merge_candidate(
            app_id=app_id,
            candidate=record.candidate,
            review_note=review_note,
        )
        updated_record = self.store.approve(
            app_id,
            candidate_id,
            decision=KnowledgeReviewDecision(reviewed_by=reviewed_by, review_note=review_note),
            resolved_card_id=merge_result.resolved_card_id,
        )
        return CandidateApprovalResult(
            candidate=updated_record,
            resolved_card_id=merge_result.resolved_card_id,
            build_manifest_path=merge_result.build_result.build_manifest_path,
            db_path=merge_result.build_result.db_path,
            rebuilt_cards=merge_result.build_result.rebuilt_cards,
            skipped_cards=merge_result.build_result.skipped_cards,
            cache_hit=merge_result.build_result.cache_hit,
        )

    def reject_candidate(
        self,
        *,
        app_id: str,
        candidate_id: str,
        reviewed_by: str | None = None,
        review_note: str | None = None,
    ) -> CandidateRejectionResult:
        self._load_profile(app_id)
        updated_record = self.store.reject(
            app_id,
            candidate_id,
            decision=KnowledgeReviewDecision(reviewed_by=reviewed_by, review_note=review_note),
        )
        return CandidateRejectionResult(candidate=updated_record)

    def build_list_request(
        self,
        *,
        app_id: str,
        status: str | None = None,
        candidate_id: str | None = None,
        limit: int = 20,
    ) -> KnowledgeCandidateListRequest:
        return KnowledgeCandidateListRequest(
            app_id=app_id,
            query=KnowledgeCandidateQuery(status=status, candidate_id=candidate_id, limit=limit),
        )

    @staticmethod
    def build_approve_request(
        *,
        app_id: str,
        candidate_id: str,
        reviewed_by: str | None = None,
        review_note: str | None = None,
    ) -> KnowledgeCandidateApproveRequest:
        return KnowledgeCandidateApproveRequest(
            app_id=app_id,
            candidate_id=candidate_id,
            decision=KnowledgeReviewDecision(reviewed_by=reviewed_by, review_note=review_note),
        )

    @staticmethod
    def build_reject_request(
        *,
        app_id: str,
        candidate_id: str,
        reviewed_by: str | None = None,
        review_note: str | None = None,
    ) -> KnowledgeCandidateRejectRequest:
        return KnowledgeCandidateRejectRequest(
            app_id=app_id,
            candidate_id=candidate_id,
            decision=KnowledgeReviewDecision(reviewed_by=reviewed_by, review_note=review_note),
        )

    def _load_profile(self, app_id: str):
        return self.registry.load(app_id)
