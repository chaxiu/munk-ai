from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from munk_knowledge_local import (
    DEFAULT_APP_KNOWLEDGE_EMBEDDING_DIM,
    DEFAULT_APP_KNOWLEDGE_MODEL_ID,
    DEFAULT_APP_KNOWLEDGE_ONNX_FILE,
    KnowledgeCardDb,
    KnowledgeCardIndexService,
    OnnxEmbeddingService,
    default_app_knowledge_model_dir,
)

from .build_models import AppKnowledgeBuildManifest, AppKnowledgeBuildResult
from .build_paths import resolve_app_knowledge_build_paths
from .document_loader import app_knowledge_path, load_app_knowledge_document
from .normalizer import normalize_app_knowledge_document


class AppKnowledgeBuildService:
    def __init__(self, *, assets_root: Path, embedding_service: Any | None = None) -> None:
        self.assets_root = assets_root
        self.embedding_service = embedding_service or build_default_app_knowledge_embedding_service()

    def build(self, *, app_id: str, ref: str | None = None) -> AppKnowledgeBuildResult:
        knowledge_path = app_knowledge_path(self.assets_root, app_id, ref=ref)
        document = load_app_knowledge_document(app_id, assets_root=self.assets_root, ref=ref)
        if document is None:
            raise FileNotFoundError(f"app knowledge not found: {knowledge_path}")
        source_content_hash = compute_app_knowledge_source_hash(knowledge_path)
        paths = resolve_app_knowledge_build_paths(assets_root=self.assets_root, app_id=app_id)
        records = normalize_app_knowledge_document(document)
        existing_manifest = load_app_knowledge_build_manifest(paths.build_manifest_path)
        if (
            existing_manifest is not None
            and existing_manifest.source_content_hash == source_content_hash
            and existing_manifest.embedding_model_id == self.embedding_service.model_id
            and existing_manifest.embedding_dim == int(self.embedding_service.embedding_dim)
            and Path(existing_manifest.db_path).exists()
        ):
            return AppKnowledgeBuildResult(
                app_id=app_id,
                knowledge_ref=ref or knowledge_path.name,
                db_path=str(paths.db_path),
                build_manifest_path=str(paths.build_manifest_path),
                source_content_hash=source_content_hash,
                total_cards=existing_manifest.total_cards,
                rebuilt_cards=0,
                skipped_cards=existing_manifest.total_cards,
                cache_hit=True,
            )
        index_service = KnowledgeCardIndexService(
            db=KnowledgeCardDb(paths.db_path, embedding_dim=int(self.embedding_service.embedding_dim)),
            embedding_service=self.embedding_service,
        )
        index_result = index_service.build(app_id=app_id, records=records)
        manifest = write_app_knowledge_build_manifest(
            build_manifest_path=paths.build_manifest_path,
            app_id=app_id,
            schema_version=document.schema_version,
            knowledge_ref=ref or knowledge_path.name,
            source_path=knowledge_path,
            source_content_hash=source_content_hash,
            total_cards=index_result.total_cards,
            rebuilt_cards=index_result.rebuilt_cards,
            skipped_cards=index_result.skipped_cards,
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
            cache_hit=False,
        )


def build_app_knowledge_index(
    *,
    app_id: str,
    assets_root: Path,
    ref: str | None = None,
    embedding_service: Any | None = None,
) -> AppKnowledgeBuildResult:
    return AppKnowledgeBuildService(
        assets_root=assets_root,
        embedding_service=embedding_service,
    ).build(app_id=app_id, ref=ref)


def load_app_knowledge_build_manifest(path: Path) -> AppKnowledgeBuildManifest | None:
    if not path.exists() or not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    return AppKnowledgeBuildManifest.model_validate(json.loads(raw))


def compute_app_knowledge_source_hash(knowledge_path: Path) -> str:
    raw_content = knowledge_path.read_text(encoding="utf-8")
    return hashlib.sha256(raw_content.encode("utf-8")).hexdigest()


def write_app_knowledge_build_manifest(
    *,
    build_manifest_path: Path,
    app_id: str,
    schema_version: str,
    knowledge_ref: str,
    source_path: Path,
    source_content_hash: str,
    total_cards: int,
    rebuilt_cards: int,
    skipped_cards: int,
    embedding_model_id: str,
    embedding_dim: int,
    db_path: Path,
) -> AppKnowledgeBuildManifest:
    manifest = AppKnowledgeBuildManifest(
        app_id=app_id,
        schema_version=schema_version,
        knowledge_ref=knowledge_ref,
        source_path=str(source_path),
        source_content_hash=source_content_hash,
        total_cards=total_cards,
        rebuilt_cards=rebuilt_cards,
        skipped_cards=skipped_cards,
        embedding_model_id=embedding_model_id,
        embedding_dim=embedding_dim,
        db_path=str(db_path),
        built_at=datetime.now(timezone.utc).isoformat(),
    )
    build_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    build_manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return manifest


def build_default_app_knowledge_embedding_service() -> Any:
    model_dir = default_app_knowledge_model_dir()
    if not model_dir.exists():
        raise FileNotFoundError(
            "knowledge embedding model directory not found; expected bundled shared model resources at "
            f"{model_dir}"
        )
    return OnnxEmbeddingService(
        model_dir=model_dir,
        model_id=DEFAULT_APP_KNOWLEDGE_MODEL_ID,
        onnx_file=DEFAULT_APP_KNOWLEDGE_ONNX_FILE,
        embedding_dim=DEFAULT_APP_KNOWLEDGE_EMBEDDING_DIM,
    )
