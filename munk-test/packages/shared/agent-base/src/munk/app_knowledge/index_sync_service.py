from __future__ import annotations

from pathlib import Path
from typing import Any

from munk_knowledge_local import KnowledgeCardDb, KnowledgeCardIndexService

from .build_models import AppKnowledgeBuildResult
from .build_paths import resolve_app_knowledge_build_paths
from .build_service import (
    build_app_knowledge_index,
    build_default_app_knowledge_embedding_service,
    compute_app_knowledge_source_hash,
    write_app_knowledge_build_manifest,
)
from .document_loader import app_knowledge_path
from .models import KnowledgeCard
from .normalizer import normalize_knowledge_card


class AppKnowledgeIndexSyncService:
    def __init__(self, *, assets_root: Path, embedding_service: Any | None = None) -> None:
        self.assets_root = assets_root
        self.embedding_service = embedding_service or build_default_app_knowledge_embedding_service()

    def upsert_cards(
        self,
        *,
        app_id: str,
        schema_version: str,
        cards: list[KnowledgeCard],
        total_cards: int,
        ref: str | None = None,
    ) -> AppKnowledgeBuildResult:
        paths = resolve_app_knowledge_build_paths(assets_root=self.assets_root, app_id=app_id)
        if not paths.db_path.exists():
            return build_app_knowledge_index(
                app_id=app_id,
                assets_root=self.assets_root,
                ref=ref,
                embedding_service=self.embedding_service,
            )
        index_service = KnowledgeCardIndexService(
            db=KnowledgeCardDb(paths.db_path, embedding_dim=int(self.embedding_service.embedding_dim)),
            embedding_service=self.embedding_service,
        )
        index_result = index_service.upsert_records(
            app_id=app_id,
            records=[normalize_knowledge_card(card) for card in cards],
        )
        return self._write_result(
            app_id=app_id,
            schema_version=schema_version,
            ref=ref,
            total_cards=total_cards,
            rebuilt_cards=index_result.rebuilt_cards,
            skipped_cards=max(total_cards - index_result.rebuilt_cards, 0),
            cache_hit=index_result.rebuilt_cards == 0 and total_cards > 0,
        )

    def delete_cards(
        self,
        *,
        app_id: str,
        schema_version: str,
        card_ids: list[str],
        total_cards: int,
        ref: str | None = None,
    ) -> AppKnowledgeBuildResult:
        paths = resolve_app_knowledge_build_paths(assets_root=self.assets_root, app_id=app_id)
        if not paths.db_path.exists():
            return build_app_knowledge_index(
                app_id=app_id,
                assets_root=self.assets_root,
                ref=ref,
                embedding_service=self.embedding_service,
            )
        index_service = KnowledgeCardIndexService(
            db=KnowledgeCardDb(paths.db_path, embedding_dim=int(self.embedding_service.embedding_dim)),
            embedding_service=self.embedding_service,
        )
        index_service.delete_cards(app_id=app_id, card_ids=card_ids)
        return self._write_result(
            app_id=app_id,
            schema_version=schema_version,
            ref=ref,
            total_cards=total_cards,
            rebuilt_cards=0,
            skipped_cards=total_cards,
            cache_hit=False,
        )

    def _write_result(
        self,
        *,
        app_id: str,
        schema_version: str,
        ref: str | None,
        total_cards: int,
        rebuilt_cards: int,
        skipped_cards: int,
        cache_hit: bool,
    ) -> AppKnowledgeBuildResult:
        paths = resolve_app_knowledge_build_paths(assets_root=self.assets_root, app_id=app_id)
        knowledge_path = app_knowledge_path(self.assets_root, app_id, ref=ref)
        source_content_hash = compute_app_knowledge_source_hash(knowledge_path)
        manifest = write_app_knowledge_build_manifest(
            build_manifest_path=paths.build_manifest_path,
            app_id=app_id,
            schema_version=schema_version,
            knowledge_ref=ref or knowledge_path.name,
            source_path=knowledge_path,
            source_content_hash=source_content_hash,
            total_cards=total_cards,
            rebuilt_cards=rebuilt_cards,
            skipped_cards=skipped_cards,
            embedding_model_id=self.embedding_service.model_id,
            embedding_dim=int(self.embedding_service.embedding_dim),
            db_path=paths.db_path,
        )
        return AppKnowledgeBuildResult(
            app_id=app_id,
            knowledge_ref=manifest.knowledge_ref,
            db_path=manifest.db_path,
            build_manifest_path=str(paths.build_manifest_path),
            source_content_hash=manifest.source_content_hash,
            total_cards=manifest.total_cards,
            rebuilt_cards=manifest.rebuilt_cards,
            skipped_cards=manifest.skipped_cards,
            cache_hit=cache_hit,
        )
