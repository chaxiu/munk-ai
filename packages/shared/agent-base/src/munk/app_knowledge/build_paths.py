from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_APP_KNOWLEDGE_BUILD_DIRNAME = "knowledge_build"
DEFAULT_APP_KNOWLEDGE_DB_NAME = "app_knowledge.sqlite"
DEFAULT_APP_KNOWLEDGE_BUILD_MANIFEST_NAME = "build_manifest.json"


@dataclass(frozen=True)
class AppKnowledgeBuildPaths:
    app_dir: Path
    build_root: Path
    db_path: Path
    build_manifest_path: Path


def resolve_app_knowledge_build_paths(*, assets_root: Path, app_id: str) -> AppKnowledgeBuildPaths:
    normalized_app_id = app_id.strip()
    app_dir = assets_root / "apps" / normalized_app_id
    build_root = app_dir / DEFAULT_APP_KNOWLEDGE_BUILD_DIRNAME
    return AppKnowledgeBuildPaths(
        app_dir=app_dir,
        build_root=build_root,
        db_path=build_root / DEFAULT_APP_KNOWLEDGE_DB_NAME,
        build_manifest_path=build_root / DEFAULT_APP_KNOWLEDGE_BUILD_MANIFEST_NAME,
    )
