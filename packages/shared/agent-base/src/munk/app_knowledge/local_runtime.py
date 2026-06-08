from __future__ import annotations

from pathlib import Path
from typing import Any

from munk_knowledge_local import KnowledgeCardDb, KnowledgeCardRetrievalService, row_to_knowledge_card_payload
from pydantic import TypeAdapter

from munk.knowledge import KnowledgeRuntimeHealth

from .approval_service import AppKnowledgeApprovalService
from .build_paths import resolve_app_knowledge_build_paths
from .build_service import AppKnowledgeBuildService
from .local_store import LocalKnowledgeCandidateStore
from .models import KnowledgeCard
from .runtime import (
    KnowledgeCandidateApproveOutput,
    KnowledgeCandidateApproveRequest,
    KnowledgeCandidateListOutput,
    KnowledgeCandidateListRequest,
    KnowledgeCandidateRejectOutput,
    KnowledgeCandidateRejectRequest,
    KnowledgeGetOutput,
    KnowledgeGetRequest,
    KnowledgeListOutput,
    KnowledgeListRequest,
    KnowledgeSearchOutput,
    KnowledgeSearchRequest,
    KnowledgeSubmitCandidateOutput,
    KnowledgeSubmitCandidateRequest,
)

_KNOWLEDGE_CARD_ADAPTER = TypeAdapter(KnowledgeCard)


class LocalKnowledgeRuntime:
    runtime_id = "local"

    def __init__(self, *, resolved_config: Any) -> None:
        self._resolved_config = resolved_config
        self._assets_root = _resolve_assets_root(resolved_config)
        self._candidate_store = LocalKnowledgeCandidateStore(root_dir=self._assets_root)
        self._build_service = AppKnowledgeBuildService(
            assets_root=self._assets_root,
            embedding_service=_resolve_embedding_service(resolved_config),
        )

    def search(self, request: KnowledgeSearchRequest, *, context, cancel_controller=None) -> KnowledgeSearchOutput:  # noqa: ANN001
        del context, cancel_controller
        retrieval = self._build_retrieval_service(request.app_id)
        rows = retrieval.search(
            app_id=request.app_id,
            query_text=request.query,
            card_types=list(request.card_types),
            limit=request.limit,
        )
        items = [_row_to_card(row) for row in rows]
        return KnowledgeSearchOutput(items=items, total_count=len(items))

    def get(self, request: KnowledgeGetRequest, *, context, cancel_controller=None) -> KnowledgeGetOutput:  # noqa: ANN001
        del context, cancel_controller
        if request.app_id is not None:
            retrieval = self._build_retrieval_service(request.app_id)
            row = retrieval.get_card(card_id=request.card_id, app_id=request.app_id)
            return KnowledgeGetOutput(card=_row_to_card(row) if row is not None else None)
        for app_id in self._iter_app_ids():
            retrieval = self._build_retrieval_service(app_id)
            row = retrieval.get_card(card_id=request.card_id, app_id=app_id)
            if row is not None:
                return KnowledgeGetOutput(card=_row_to_card(row))
        return KnowledgeGetOutput(card=None)

    def list(self, request: KnowledgeListRequest, *, context, cancel_controller=None) -> KnowledgeListOutput:  # noqa: ANN001
        del context, cancel_controller
        retrieval = self._build_retrieval_service(request.app_id)
        rows = retrieval.list_cards(
            app_id=request.app_id,
            card_type=request.card_type,
            limit=request.limit,
        )
        items = [_row_to_card(row) for row in rows]
        return KnowledgeListOutput(items=items, total_count=len(items))

    def submit_candidate(
        self,
        request: KnowledgeSubmitCandidateRequest,
        *,
        context,
        cancel_controller=None,
    ) -> KnowledgeSubmitCandidateOutput:  # noqa: ANN001
        del context, cancel_controller
        record = self._candidate_store.submit(request.submission)
        return KnowledgeSubmitCandidateOutput(candidate=record)

    def list_candidates(
        self,
        request: KnowledgeCandidateListRequest,
        *,
        context,
        cancel_controller=None,
    ) -> KnowledgeCandidateListOutput:  # noqa: ANN001
        del context, cancel_controller
        items = self._candidate_store.list_records(request.app_id, query=request.query)
        return KnowledgeCandidateListOutput(items=items, total_count=len(items))

    def approve_candidate(
        self,
        request: KnowledgeCandidateApproveRequest,
        *,
        context,
        cancel_controller=None,
    ) -> KnowledgeCandidateApproveOutput:  # noqa: ANN001
        del context, cancel_controller
        record = self._candidate_store.get_record(request.app_id, request.candidate_id)
        if record is None:
            raise FileNotFoundError(f"candidate '{request.candidate_id}' not found for app '{request.app_id}'")
        merge_result = AppKnowledgeApprovalService(
            assets_root=self._assets_root,
        ).merge_candidate(
            app_id=request.app_id,
            candidate=record.candidate,
            review_note=request.decision.review_note,
        )
        approved = self._candidate_store.approve(
            request.app_id,
            request.candidate_id,
            decision=request.decision,
            resolved_card_id=merge_result.resolved_card_id,
        )
        return KnowledgeCandidateApproveOutput(
            candidate=approved,
            resolved_card_id=merge_result.resolved_card_id,
        )

    def reject_candidate(
        self,
        request: KnowledgeCandidateRejectRequest,
        *,
        context,
        cancel_controller=None,
    ) -> KnowledgeCandidateRejectOutput:  # noqa: ANN001
        del context, cancel_controller
        record = self._candidate_store.reject(
            request.app_id,
            request.candidate_id,
            decision=request.decision,
        )
        return KnowledgeCandidateRejectOutput(candidate=record)

    def _build_retrieval_service(self, app_id: str) -> KnowledgeCardRetrievalService:
        build_result = self._build_service.build(app_id=app_id)
        db = KnowledgeCardDb(
            Path(build_result.db_path),
            read_only=True,
            embedding_dim=int(self._build_service.embedding_service.embedding_dim),
        )
        return KnowledgeCardRetrievalService(
            db=db,
            embedding_service=self._build_service.embedding_service,
        )

    def _iter_app_ids(self) -> list[str]:
        app_ids: list[str] = []
        apps_dir = self._assets_root / "apps"
        if not apps_dir.exists():
            return app_ids
        for app_dir in sorted(path for path in apps_dir.iterdir() if path.is_dir()):
            knowledge_path = resolve_app_knowledge_build_paths(
                assets_root=self._assets_root,
                app_id=app_dir.name,
            ).app_dir / "app_knowledge.json"
            if knowledge_path.exists():
                app_ids.append(app_dir.name)
        return app_ids


class LocalKnowledgeRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config: Any) -> LocalKnowledgeRuntime:
        return LocalKnowledgeRuntime(resolved_config=resolved_config)

    def diagnose(self) -> KnowledgeRuntimeHealth:
        return KnowledgeRuntimeHealth(
            runtime_id=self.runtime_id,
            status="ok",
            message="app knowledge local runtime supports build-backed hybrid retrieval and pending candidate submission",
            details={"phase": "4", "implementation": "local_build_backed"},
        )


def build_knowledge_runtime_factory() -> LocalKnowledgeRuntimeFactory:
    return LocalKnowledgeRuntimeFactory()


def _resolve_assets_root(resolved_config: Any) -> Path:
    if isinstance(resolved_config, dict):
        candidate = resolved_config.get("app_registry_root") or resolved_config.get("assets_root")
        if isinstance(candidate, (str, Path)):
            return Path(candidate)
    return Path.cwd()


def _resolve_embedding_service(resolved_config: Any) -> Any:
    if isinstance(resolved_config, dict):
        candidate = resolved_config.get("knowledge_embedding_service")
        if candidate is not None:
            return candidate
    return None


def _row_to_card(row: dict[str, Any] | None) -> KnowledgeCard | None:
    if row is None:
        return None
    return _KNOWLEDGE_CARD_ADAPTER.validate_python(row_to_knowledge_card_payload(row))
