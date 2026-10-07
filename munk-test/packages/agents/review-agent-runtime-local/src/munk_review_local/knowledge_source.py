from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from yaml import YAMLError

from .constants import default_review_source_root
from .knowledge_models import KnowledgeCaseDocument, KnowledgeCaseManifest
from .knowledge_quality import KnowledgeQualityReport, KnowledgeQualityValidator


def review_knowledge_root(root_dir: Path | None = None) -> Path:
    return root_dir or default_review_source_root()


class KnowledgeSourceError(ValueError):
    """Raised when the structured review knowledge source is invalid."""


class KnowledgeSourceLoader:
    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = review_knowledge_root(root_dir)

    def load_all(self) -> list[KnowledgeCaseDocument]:
        if not self.root_dir.exists():
            return []
        documents: list[KnowledgeCaseDocument] = []
        seen_case_ids: set[str] = set()
        for manifest_path in sorted(self.root_dir.rglob("manifest.yaml")):
            if "build" in manifest_path.parts:
                continue
            document = self.load_case(manifest_path.parent)
            if document.case_id in seen_case_ids:
                raise KnowledgeSourceError(f"duplicate knowledge case_id: {document.case_id}")
            seen_case_ids.add(document.case_id)
            documents.append(document)
        return documents

    def load_case(self, case_dir: Path) -> KnowledgeCaseDocument:
        manifest_path = case_dir / "manifest.yaml"
        body_path = case_dir / "body.md"
        if not manifest_path.exists():
            raise KnowledgeSourceError(f"knowledge case missing manifest.yaml: {case_dir}")
        if not body_path.exists():
            raise KnowledgeSourceError(f"knowledge case missing body.md: {case_dir}")
        try:
            raw_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except YAMLError as exc:
            raise KnowledgeSourceError(f"knowledge manifest is invalid YAML: {manifest_path}") from exc
        if not isinstance(raw_manifest, dict):
            raise KnowledgeSourceError(f"knowledge manifest root must be a mapping: {manifest_path}")
        manifest = KnowledgeCaseManifest.model_validate(raw_manifest)
        body_md = body_path.read_text(encoding="utf-8").strip()
        if not body_md:
            raise KnowledgeSourceError(f"knowledge body.md is empty: {body_path}")
        self._validate_directory_contract(case_dir=case_dir, manifest=manifest)
        content_hash = self._build_content_hash(manifest=manifest, body_md=body_md)
        return KnowledgeCaseDocument(
            manifest=manifest,
            source_dir=case_dir,
            manifest_path=manifest_path,
            body_path=body_path,
            body_md=body_md,
            content_hash=content_hash,
        )

    def build_quality_report(
        self,
        *,
        documents: list[KnowledgeCaseDocument] | None = None,
        validator: KnowledgeQualityValidator | None = None,
    ) -> KnowledgeQualityReport:
        docs = self.load_all() if documents is None else documents
        quality_validator = validator or KnowledgeQualityValidator()
        return quality_validator.validate_documents(docs)

    def _validate_directory_contract(
        self,
        *,
        case_dir: Path,
        manifest: KnowledgeCaseManifest,
    ) -> None:
        relative_parts = case_dir.relative_to(self.root_dir).parts
        if len(relative_parts) != 4:
            raise KnowledgeSourceError(
                f"knowledge case path must be <platform>/<domain>/<topic>/<case_id>: {case_dir}"
            )
        platform, domain, topic, case_id = relative_parts
        if platform != manifest.platform:
            raise KnowledgeSourceError(
                f"knowledge manifest platform mismatch: path={platform} manifest={manifest.platform} dir={case_dir}"
            )
        if domain != manifest.domain:
            raise KnowledgeSourceError(
                f"knowledge manifest domain mismatch: path={domain} manifest={manifest.domain} dir={case_dir}"
            )
        if topic != manifest.topic:
            raise KnowledgeSourceError(
                f"knowledge manifest topic mismatch: path={topic} manifest={manifest.topic} dir={case_dir}"
            )
        if case_id != manifest.case_id:
            raise KnowledgeSourceError(
                f"knowledge manifest case_id mismatch: path={case_id} manifest={manifest.case_id} dir={case_dir}"
            )

    @staticmethod
    def _build_content_hash(*, manifest: KnowledgeCaseManifest, body_md: str) -> str:
        digest = hashlib.sha256()
        digest.update(json.dumps(manifest.model_dump(mode="json"), sort_keys=True).encode("utf-8"))
        digest.update(b"\n---\n")
        digest.update(body_md.encode("utf-8"))
        return digest.hexdigest()
