from __future__ import annotations

from pathlib import Path

from munk.app_knowledge import AppKnowledgeImportDocument
from munk.paths import assets_root as default_assets_root
from munk.shared_tools import KnowledgeToolProvider

from .provider import build_knowledge_provider_from_document, build_runtime_backed_knowledge_provider


def resolve_effective_assets_root(explicit: Path | None) -> Path:
    return explicit if explicit is not None else default_assets_root()


def build_app_knowledge_tools(
    *,
    app_id: str,
    assets_root: Path | None,
    document: AppKnowledgeImportDocument | None,
    resolved_config: object | None = None,
) -> KnowledgeToolProvider:
    normalized = document or AppKnowledgeImportDocument(app_id=app_id, cards=[])
    if not normalized.cards:
        return build_knowledge_provider_from_document(normalized)
    effective_assets_root = resolve_effective_assets_root(assets_root)
    config_payload = dict(resolved_config) if isinstance(resolved_config, dict) else {}
    config_payload["app_registry_root"] = effective_assets_root
    return build_runtime_backed_knowledge_provider(
        app_id=app_id,
        assets_root=effective_assets_root,
        resolved_config=config_payload,
    )
