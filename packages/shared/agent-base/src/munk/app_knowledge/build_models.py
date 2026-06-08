from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _clean_text(value: str) -> str:
    return value.strip()


class NormalizedKnowledgeCardRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    card_id: str
    card_type: str
    title: str
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    updated_at: str
    source_kind: str
    source_ref: str | None = None
    source_note: str | None = None
    payload_json: str
    flat_text: str
    fts_text: str
    embedding_text: str
    summary_text: str

    @model_validator(mode="after")
    def validate_record(self) -> "NormalizedKnowledgeCardRecord":
        self.app_id = _clean_text(self.app_id)
        self.card_id = _clean_text(self.card_id)
        self.card_type = _clean_text(self.card_type)
        self.title = _clean_text(self.title)
        self.status = _clean_text(self.status)
        self.updated_at = _clean_text(self.updated_at)
        self.source_kind = _clean_text(self.source_kind)
        self.source_ref = _clean_text(self.source_ref) or None if self.source_ref is not None else None
        self.source_note = _clean_text(self.source_note) or None if self.source_note is not None else None
        self.payload_json = self.payload_json.strip()
        self.flat_text = self.flat_text.strip()
        self.fts_text = self.fts_text.strip()
        self.embedding_text = self.embedding_text.strip()
        self.summary_text = self.summary_text.strip()
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.card_id:
            raise ValueError("card_id must not be empty")
        if not self.card_type:
            raise ValueError("card_type must not be empty")
        if not self.title:
            raise ValueError("title must not be empty")
        if not self.status:
            raise ValueError("status must not be empty")
        if not self.updated_at:
            raise ValueError("updated_at must not be empty")
        if not self.source_kind:
            raise ValueError("source_kind must not be empty")
        if not self.payload_json:
            raise ValueError("payload_json must not be empty")
        if not self.flat_text:
            raise ValueError("flat_text must not be empty")
        if not self.fts_text:
            raise ValueError("fts_text must not be empty")
        if not self.embedding_text:
            raise ValueError("embedding_text must not be empty")
        if not self.summary_text:
            raise ValueError("summary_text must not be empty")
        return self


class AppKnowledgeBuildManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    schema_version: str
    knowledge_ref: str
    source_path: str
    source_content_hash: str
    total_cards: int = Field(ge=0)
    rebuilt_cards: int = Field(ge=0)
    skipped_cards: int = Field(ge=0)
    embedding_model_id: str
    embedding_dim: int = Field(ge=1)
    db_path: str
    built_at: str

    @model_validator(mode="after")
    def validate_manifest(self) -> "AppKnowledgeBuildManifest":
        self.app_id = _clean_text(self.app_id)
        self.schema_version = _clean_text(self.schema_version)
        self.knowledge_ref = _clean_text(self.knowledge_ref)
        self.source_path = _clean_text(self.source_path)
        self.source_content_hash = _clean_text(self.source_content_hash)
        self.embedding_model_id = _clean_text(self.embedding_model_id)
        self.db_path = _clean_text(self.db_path)
        self.built_at = _clean_text(self.built_at)
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.schema_version:
            raise ValueError("schema_version must not be empty")
        if not self.knowledge_ref:
            raise ValueError("knowledge_ref must not be empty")
        if not self.source_path:
            raise ValueError("source_path must not be empty")
        if not self.source_content_hash:
            raise ValueError("source_content_hash must not be empty")
        if not self.embedding_model_id:
            raise ValueError("embedding_model_id must not be empty")
        if not self.db_path:
            raise ValueError("db_path must not be empty")
        if not self.built_at:
            raise ValueError("built_at must not be empty")
        return self


class AppKnowledgeBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    knowledge_ref: str
    db_path: str
    build_manifest_path: str
    source_content_hash: str
    total_cards: int = Field(ge=0)
    rebuilt_cards: int = Field(ge=0)
    skipped_cards: int = Field(ge=0)
    cache_hit: bool = False

    @model_validator(mode="after")
    def validate_result(self) -> "AppKnowledgeBuildResult":
        self.app_id = _clean_text(self.app_id)
        self.knowledge_ref = _clean_text(self.knowledge_ref)
        self.db_path = _clean_text(self.db_path)
        self.build_manifest_path = _clean_text(self.build_manifest_path)
        self.source_content_hash = _clean_text(self.source_content_hash)
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.knowledge_ref:
            raise ValueError("knowledge_ref must not be empty")
        if not self.db_path:
            raise ValueError("db_path must not be empty")
        if not self.build_manifest_path:
            raise ValueError("build_manifest_path must not be empty")
        if not self.source_content_hash:
            raise ValueError("source_content_hash must not be empty")
        return self
