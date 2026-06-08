from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

KnowledgeCardType = Literal[
    "screen",
    "flow",
    "assertion",
    "issue",
    "data",
    "policy",
    "domain_term",
]
KnowledgeCardStatus = Literal["active", "deprecated", "archived"]
KnowledgeSourceKind = Literal["import", "review", "knowledge_agent", "manual"]
KnowledgeCandidateStatus = Literal["pending_review", "approved", "rejected"]
KNOWLEDGE_IMPORT_SCHEMA_VERSION = "knowledge.import.v1"


def empty_strings() -> list[str]:
    return []


def _clean_text(value: str) -> str:
    return value.strip()


def _clean_text_list(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        value = _clean_text(item)
        if value:
            cleaned.append(value)
    return cleaned


class KnowledgeSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: KnowledgeSourceKind
    ref: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "KnowledgeSource":
        if self.ref is not None:
            self.ref = _clean_text(self.ref) or None
        if self.note is not None:
            self.note = _clean_text(self.note) or None
        return self


class ScreenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enter: str | None = None
    recognize: str | None = None
    key_elements: list[str] = Field(default_factory=empty_strings)
    exit_signals: list[str] = Field(default_factory=empty_strings)

    @model_validator(mode="after")
    def validate_payload(self) -> "ScreenPayload":
        if self.enter is not None:
            self.enter = _clean_text(self.enter) or None
        if self.recognize is not None:
            self.recognize = _clean_text(self.recognize) or None
        self.key_elements = _clean_text_list(self.key_elements)
        self.exit_signals = _clean_text_list(self.exit_signals)
        return self


class FlowPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    preconditions: list[str] = Field(default_factory=empty_strings)
    typical_steps: list[str] = Field(default_factory=empty_strings)
    completion_signals: list[str] = Field(default_factory=empty_strings)

    @model_validator(mode="after")
    def validate_payload(self) -> "FlowPayload":
        self.goal = _clean_text(self.goal)
        self.preconditions = _clean_text_list(self.preconditions)
        self.typical_steps = _clean_text_list(self.typical_steps)
        self.completion_signals = _clean_text_list(self.completion_signals)
        if not self.goal:
            raise ValueError("goal must not be empty")
        return self


class AssertionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    when: str
    success_signals: list[str] = Field(default_factory=empty_strings)
    failure_signals: list[str] = Field(default_factory=empty_strings)
    verdict_hint: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "AssertionPayload":
        self.when = _clean_text(self.when)
        self.success_signals = _clean_text_list(self.success_signals)
        self.failure_signals = _clean_text_list(self.failure_signals)
        if self.verdict_hint is not None:
            self.verdict_hint = _clean_text(self.verdict_hint) or None
        if not self.when:
            raise ValueError("when must not be empty")
        return self


class IssuePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symptoms: list[str] = Field(default_factory=empty_strings)
    trigger_conditions: list[str] = Field(default_factory=empty_strings)
    workaround: str | None = None
    severity: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "IssuePayload":
        self.symptoms = _clean_text_list(self.symptoms)
        self.trigger_conditions = _clean_text_list(self.trigger_conditions)
        if self.workaround is not None:
            self.workaround = _clean_text(self.workaround) or None
        if self.severity is not None:
            self.severity = _clean_text(self.severity) or None
        return self


class DataPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixtures: list[str] = Field(default_factory=empty_strings)
    accounts: list[str] = Field(default_factory=empty_strings)
    preloaded_state: list[str] = Field(default_factory=empty_strings)
    cleanup_requirements: list[str] = Field(default_factory=empty_strings)

    @model_validator(mode="after")
    def validate_payload(self) -> "DataPayload":
        self.fixtures = _clean_text_list(self.fixtures)
        self.accounts = _clean_text_list(self.accounts)
        self.preloaded_state = _clean_text_list(self.preloaded_state)
        self.cleanup_requirements = _clean_text_list(self.cleanup_requirements)
        return self


class PolicyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform_constraints: list[str] = Field(default_factory=empty_strings)
    environment_rules: list[str] = Field(default_factory=empty_strings)
    permission_rules: list[str] = Field(default_factory=empty_strings)
    risk_controls: list[str] = Field(default_factory=empty_strings)

    @model_validator(mode="after")
    def validate_payload(self) -> "PolicyPayload":
        self.platform_constraints = _clean_text_list(self.platform_constraints)
        self.environment_rules = _clean_text_list(self.environment_rules)
        self.permission_rules = _clean_text_list(self.permission_rules)
        self.risk_controls = _clean_text_list(self.risk_controls)
        return self


class DomainTermPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str
    aliases: list[str] = Field(default_factory=empty_strings)
    meaning: str
    related_terms: list[str] = Field(default_factory=empty_strings)
    business_scope: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "DomainTermPayload":
        self.term = _clean_text(self.term)
        self.aliases = _clean_text_list(self.aliases)
        self.meaning = _clean_text(self.meaning)
        self.related_terms = _clean_text_list(self.related_terms)
        if self.business_scope is not None:
            self.business_scope = _clean_text(self.business_scope) or None
        if not self.term:
            raise ValueError("term must not be empty")
        if not self.meaning:
            raise ValueError("meaning must not be empty")
        return self


class KnowledgeCardBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    app_id: str
    title: str
    status: KnowledgeCardStatus
    confidence: float = Field(ge=0.0, le=1.0)
    updated_at: str
    source: KnowledgeSource

    @model_validator(mode="after")
    def validate_card(self) -> "KnowledgeCardBase":
        self.card_id = _clean_text(self.card_id)
        self.app_id = _clean_text(self.app_id)
        self.title = _clean_text(self.title)
        self.updated_at = _clean_text(self.updated_at)
        if not self.card_id:
            raise ValueError("card_id must not be empty")
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.title:
            raise ValueError("title must not be empty")
        if not self.updated_at:
            raise ValueError("updated_at must not be empty")
        return self


class ScreenKnowledgeCard(KnowledgeCardBase):
    card_type: Literal["screen"]
    payload: ScreenPayload


class FlowKnowledgeCard(KnowledgeCardBase):
    card_type: Literal["flow"]
    payload: FlowPayload


class AssertionKnowledgeCard(KnowledgeCardBase):
    card_type: Literal["assertion"]
    payload: AssertionPayload


class IssueKnowledgeCard(KnowledgeCardBase):
    card_type: Literal["issue"]
    payload: IssuePayload


class DataKnowledgeCard(KnowledgeCardBase):
    card_type: Literal["data"]
    payload: DataPayload


class PolicyKnowledgeCard(KnowledgeCardBase):
    card_type: Literal["policy"]
    payload: PolicyPayload


class DomainTermKnowledgeCard(KnowledgeCardBase):
    card_type: Literal["domain_term"]
    payload: DomainTermPayload


KnowledgeCard = Annotated[
    ScreenKnowledgeCard
    | FlowKnowledgeCard
    | AssertionKnowledgeCard
    | IssueKnowledgeCard
    | DataKnowledgeCard
    | PolicyKnowledgeCard
    | DomainTermKnowledgeCard,
    Field(discriminator="card_type"),
]


class KnowledgeCardInputBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str | None = None
    app_id: str
    title: str
    status: KnowledgeCardStatus = "active"
    confidence: float = Field(ge=0.0, le=1.0)
    source: KnowledgeSource

    @model_validator(mode="after")
    def validate_card_input(self) -> "KnowledgeCardInputBase":
        if self.card_id is not None:
            self.card_id = _clean_text(self.card_id) or None
        self.app_id = _clean_text(self.app_id)
        self.title = _clean_text(self.title)
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.title:
            raise ValueError("title must not be empty")
        return self


class ScreenKnowledgeCardInput(KnowledgeCardInputBase):
    card_type: Literal["screen"]
    payload: ScreenPayload


class FlowKnowledgeCardInput(KnowledgeCardInputBase):
    card_type: Literal["flow"]
    payload: FlowPayload


class AssertionKnowledgeCardInput(KnowledgeCardInputBase):
    card_type: Literal["assertion"]
    payload: AssertionPayload


class IssueKnowledgeCardInput(KnowledgeCardInputBase):
    card_type: Literal["issue"]
    payload: IssuePayload


class DataKnowledgeCardInput(KnowledgeCardInputBase):
    card_type: Literal["data"]
    payload: DataPayload


class PolicyKnowledgeCardInput(KnowledgeCardInputBase):
    card_type: Literal["policy"]
    payload: PolicyPayload


class DomainTermKnowledgeCardInput(KnowledgeCardInputBase):
    card_type: Literal["domain_term"]
    payload: DomainTermPayload


KnowledgeCardInput = Annotated[
    ScreenKnowledgeCardInput
    | FlowKnowledgeCardInput
    | AssertionKnowledgeCardInput
    | IssueKnowledgeCardInput
    | DataKnowledgeCardInput
    | PolicyKnowledgeCardInput
    | DomainTermKnowledgeCardInput,
    Field(discriminator="card_type"),
]


class KnowledgeCandidateDraftBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str | None = None
    app_id: str
    title: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: KnowledgeSource

    @model_validator(mode="after")
    def validate_candidate(self) -> "KnowledgeCandidateDraftBase":
        if self.card_id is not None:
            self.card_id = _clean_text(self.card_id) or None
        self.app_id = _clean_text(self.app_id)
        self.title = _clean_text(self.title)
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.title:
            raise ValueError("title must not be empty")
        return self


class ScreenKnowledgeCandidateDraft(KnowledgeCandidateDraftBase):
    card_type: Literal["screen"]
    payload: ScreenPayload


class FlowKnowledgeCandidateDraft(KnowledgeCandidateDraftBase):
    card_type: Literal["flow"]
    payload: FlowPayload


class AssertionKnowledgeCandidateDraft(KnowledgeCandidateDraftBase):
    card_type: Literal["assertion"]
    payload: AssertionPayload


class IssueKnowledgeCandidateDraft(KnowledgeCandidateDraftBase):
    card_type: Literal["issue"]
    payload: IssuePayload


class DataKnowledgeCandidateDraft(KnowledgeCandidateDraftBase):
    card_type: Literal["data"]
    payload: DataPayload


class PolicyKnowledgeCandidateDraft(KnowledgeCandidateDraftBase):
    card_type: Literal["policy"]
    payload: PolicyPayload


class DomainTermKnowledgeCandidateDraft(KnowledgeCandidateDraftBase):
    card_type: Literal["domain_term"]
    payload: DomainTermPayload


KnowledgeCandidateDraft = Annotated[
    ScreenKnowledgeCandidateDraft
    | FlowKnowledgeCandidateDraft
    | AssertionKnowledgeCandidateDraft
    | IssueKnowledgeCandidateDraft
    | DataKnowledgeCandidateDraft
    | PolicyKnowledgeCandidateDraft
    | DomainTermKnowledgeCandidateDraft,
    Field(discriminator="card_type"),
]


class AppKnowledgeImportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = KNOWLEDGE_IMPORT_SCHEMA_VERSION
    app_id: str
    cards: list[KnowledgeCard] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_document(self) -> "AppKnowledgeImportDocument":
        self.app_id = _clean_text(self.app_id)
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if self.schema_version != KNOWLEDGE_IMPORT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {KNOWLEDGE_IMPORT_SCHEMA_VERSION}")
        return self


class KnowledgeCandidateSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    candidate: KnowledgeCandidateDraft
    evidence_refs: list[str] = Field(default_factory=empty_strings)

    @model_validator(mode="after")
    def validate_submission(self) -> "KnowledgeCandidateSubmission":
        self.app_id = _clean_text(self.app_id)
        self.evidence_refs = _clean_text_list(self.evidence_refs)
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if self.candidate.app_id != self.app_id:
            raise ValueError("candidate.app_id must match app_id")
        return self


class KnowledgeCandidateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    app_id: str
    status: KnowledgeCandidateStatus
    submitted_at: str
    candidate: KnowledgeCandidateDraft
    evidence_refs: list[str] = Field(default_factory=empty_strings)
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    review_note: str | None = None
    resolved_card_id: str | None = None

    @model_validator(mode="after")
    def validate_record(self) -> "KnowledgeCandidateRecord":
        self.candidate_id = _clean_text(self.candidate_id)
        self.app_id = _clean_text(self.app_id)
        self.submitted_at = _clean_text(self.submitted_at)
        self.evidence_refs = _clean_text_list(self.evidence_refs)
        if self.reviewed_at is not None:
            self.reviewed_at = _clean_text(self.reviewed_at) or None
        if self.reviewed_by is not None:
            self.reviewed_by = _clean_text(self.reviewed_by) or None
        if self.review_note is not None:
            self.review_note = _clean_text(self.review_note) or None
        if self.resolved_card_id is not None:
            self.resolved_card_id = _clean_text(self.resolved_card_id) or None
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty")
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if self.candidate.app_id != self.app_id:
            raise ValueError("candidate.app_id must match app_id")
        return self


class KnowledgeCandidateQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str | None = None
    status: KnowledgeCandidateStatus | None = None
    limit: int = Field(default=20, ge=1, le=200)

    @model_validator(mode="after")
    def validate_query(self) -> "KnowledgeCandidateQuery":
        if self.candidate_id is not None:
            self.candidate_id = _clean_text(self.candidate_id) or None
        return self


class KnowledgeReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_by: str | None = None
    review_note: str | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> "KnowledgeReviewDecision":
        if self.reviewed_by is not None:
            self.reviewed_by = _clean_text(self.reviewed_by) or None
        if self.review_note is not None:
            self.review_note = _clean_text(self.review_note) or None
        return self
