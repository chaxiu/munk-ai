from __future__ import annotations

from pathlib import Path

from munk.reviewing.models import ReviewCaseType, ReviewPlatform
from pydantic import BaseModel, Field


def empty_strings() -> list[str]:
    return []


class KnowledgeCaseManifest(BaseModel):
    case_id: str
    platform: ReviewPlatform
    domain: str
    topic: str
    tags: list[str] = Field(default_factory=empty_strings)
    case_type: ReviewCaseType
    title: str
    summary: str
    recommended_checks: list[str] = Field(default_factory=empty_strings)
    code_languages: list[str] = Field(default_factory=empty_strings)


class KnowledgeCaseDocument(BaseModel):
    manifest: KnowledgeCaseManifest
    source_dir: Path
    manifest_path: Path
    body_path: Path
    body_md: str
    content_hash: str

    @property
    def case_id(self) -> str:
        return self.manifest.case_id

    @property
    def platform(self) -> ReviewPlatform:
        return self.manifest.platform

    @property
    def domain(self) -> str:
        return self.manifest.domain

    @property
    def topic(self) -> str:
        return self.manifest.topic

    @property
    def case_type(self) -> ReviewCaseType:
        return self.manifest.case_type
