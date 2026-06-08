from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import (
    KnowledgeCandidateQuery,
    KnowledgeCandidateRecord,
    KnowledgeCandidateStatus,
    KnowledgeCandidateSubmission,
    KnowledgeReviewDecision,
)

DEFAULT_CANDIDATE_FILE_NAME = "knowledge_candidates.json"


class LocalKnowledgeCandidateStore:
    def __init__(
        self,
        *,
        root_dir: Path,
        file_name: str = DEFAULT_CANDIDATE_FILE_NAME,
    ) -> None:
        self._root_dir = root_dir
        self._file_name = file_name

    def path_for_app(self, app_id: str) -> Path:
        return self._root_dir / "apps" / app_id.strip() / self._file_name

    def submit(self, submission: KnowledgeCandidateSubmission) -> KnowledgeCandidateRecord:
        record = KnowledgeCandidateRecord(
            candidate_id=self._new_candidate_id(),
            app_id=submission.app_id,
            status="pending_review",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            candidate=submission.candidate,
            evidence_refs=list(submission.evidence_refs),
        )
        path = self.path_for_app(submission.app_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        records = self.list_records(submission.app_id)
        records.append(record)
        path.write_text(
            json.dumps([item.model_dump(mode="json") for item in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record

    def get_record(self, app_id: str, candidate_id: str) -> KnowledgeCandidateRecord | None:
        normalized_candidate_id = candidate_id.strip()
        for record in self.list_records(app_id):
            if record.candidate_id == normalized_candidate_id:
                return record
        return None

    def list_records(
        self,
        app_id: str,
        *,
        query: KnowledgeCandidateQuery | None = None,
    ) -> list[KnowledgeCandidateRecord]:
        path = self.path_for_app(app_id)
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        payload = json.loads(raw)
        if not isinstance(payload, list):
            return []
        records: list[KnowledgeCandidateRecord] = []
        for item in payload:
            if isinstance(item, dict):
                records.append(KnowledgeCandidateRecord.model_validate(item))
        return self._apply_query(records, query=query)

    def approve(
        self,
        app_id: str,
        candidate_id: str,
        *,
        decision: KnowledgeReviewDecision,
        resolved_card_id: str,
    ) -> KnowledgeCandidateRecord:
        return self._transition_record(
            app_id,
            candidate_id,
            next_status="approved",
            decision=decision,
            resolved_card_id=resolved_card_id,
        )

    def reject(
        self,
        app_id: str,
        candidate_id: str,
        *,
        decision: KnowledgeReviewDecision,
    ) -> KnowledgeCandidateRecord:
        return self._transition_record(
            app_id,
            candidate_id,
            next_status="rejected",
            decision=decision,
            resolved_card_id=None,
        )

    def _transition_record(
        self,
        app_id: str,
        candidate_id: str,
        *,
        next_status: KnowledgeCandidateStatus,
        decision: KnowledgeReviewDecision,
        resolved_card_id: str | None,
    ) -> KnowledgeCandidateRecord:
        path = self.path_for_app(app_id)
        records = self.list_records(app_id)
        normalized_candidate_id = candidate_id.strip()
        updated_record: KnowledgeCandidateRecord | None = None
        next_records: list[KnowledgeCandidateRecord] = []
        for record in records:
            if record.candidate_id != normalized_candidate_id:
                next_records.append(record)
                continue
            if record.status != "pending_review":
                raise ValueError(f"candidate '{normalized_candidate_id}' is already {record.status}")
            updated_record = record.model_copy(
                update={
                    "status": next_status,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": decision.reviewed_by,
                    "review_note": decision.review_note,
                    "resolved_card_id": resolved_card_id,
                }
            )
            next_records.append(updated_record)
        if updated_record is None:
            raise FileNotFoundError(f"candidate '{normalized_candidate_id}' not found for app '{app_id}'")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([item.model_dump(mode="json") for item in next_records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return updated_record

    @staticmethod
    def _apply_query(
        records: list[KnowledgeCandidateRecord],
        *,
        query: KnowledgeCandidateQuery | None,
    ) -> list[KnowledgeCandidateRecord]:
        if query is None:
            return records
        filtered = records
        if query.candidate_id is not None:
            filtered = [record for record in filtered if record.candidate_id == query.candidate_id]
        if query.status is not None:
            filtered = [record for record in filtered if record.status == query.status]
        return filtered[: query.limit]

    @staticmethod
    def _new_candidate_id() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"kcand_{timestamp}_{uuid4().hex[:8]}"
