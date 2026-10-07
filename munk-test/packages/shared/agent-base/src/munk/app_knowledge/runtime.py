from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Protocol

from pydantic import BaseModel, Field, model_validator

from munk.agent_runtime.control import CancelController
from munk.knowledge import (
    KnowledgeManagedPaths,
    KnowledgeRuntimeConflictError,
    KnowledgeRuntimeContext,
    KnowledgeRuntimeHealth,
    KnowledgeRuntimeUnavailableError,
)

from .models import (
    KnowledgeCandidateQuery,
    KnowledgeCandidateRecord,
    KnowledgeCandidateSubmission,
    KnowledgeCard,
    KnowledgeCardType,
    KnowledgeReviewDecision,
)

APP_KNOWLEDGE_ENTRY_POINT_GROUP = "munk.app_knowledge.runtimes"


def empty_strings() -> list[str]:
    return []


def empty_cards() -> list[KnowledgeCard]:
    return []


def empty_candidate_records() -> list[KnowledgeCandidateRecord]:
    return []


class KnowledgeSearchRequest(BaseModel):
    app_id: str
    query: str
    card_types: list[KnowledgeCardType] = Field(default_factory=empty_strings)
    limit: int = Field(default=8, ge=1, le=100)

    @model_validator(mode="after")
    def validate_request(self) -> "KnowledgeSearchRequest":
        self.app_id = self.app_id.strip()
        self.query = self.query.strip()
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.query:
            raise ValueError("query must not be empty")
        return self


class KnowledgeSearchOutput(BaseModel):
    items: list[KnowledgeCard] = Field(default_factory=empty_cards)
    total_count: int = 0
    warning_summary: list[str] = Field(default_factory=empty_strings)


class KnowledgeGetRequest(BaseModel):
    app_id: str | None = None
    card_id: str

    @model_validator(mode="after")
    def validate_request(self) -> "KnowledgeGetRequest":
        if self.app_id is not None:
            self.app_id = self.app_id.strip() or None
        self.card_id = self.card_id.strip()
        if not self.card_id:
            raise ValueError("card_id must not be empty")
        return self


class KnowledgeGetOutput(BaseModel):
    card: KnowledgeCard | None = None
    warning_summary: list[str] = Field(default_factory=empty_strings)


class KnowledgeListRequest(BaseModel):
    app_id: str
    card_type: KnowledgeCardType | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_request(self) -> "KnowledgeListRequest":
        self.app_id = self.app_id.strip()
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        return self


class KnowledgeListOutput(BaseModel):
    items: list[KnowledgeCard] = Field(default_factory=empty_cards)
    total_count: int = 0
    warning_summary: list[str] = Field(default_factory=empty_strings)


class KnowledgeSubmitCandidateRequest(BaseModel):
    submission: KnowledgeCandidateSubmission


class KnowledgeSubmitCandidateOutput(BaseModel):
    candidate: KnowledgeCandidateRecord | None = None
    warning_summary: list[str] = Field(default_factory=empty_strings)


class KnowledgeCandidateListRequest(BaseModel):
    app_id: str
    query: KnowledgeCandidateQuery = Field(default_factory=KnowledgeCandidateQuery)

    @model_validator(mode="after")
    def validate_request(self) -> "KnowledgeCandidateListRequest":
        self.app_id = self.app_id.strip()
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        return self


class KnowledgeCandidateListOutput(BaseModel):
    items: list[KnowledgeCandidateRecord] = Field(default_factory=empty_candidate_records)
    total_count: int = 0
    warning_summary: list[str] = Field(default_factory=empty_strings)


class KnowledgeCandidateApproveRequest(BaseModel):
    app_id: str
    candidate_id: str
    decision: KnowledgeReviewDecision = Field(default_factory=KnowledgeReviewDecision)

    @model_validator(mode="after")
    def validate_request(self) -> "KnowledgeCandidateApproveRequest":
        self.app_id = self.app_id.strip()
        self.candidate_id = self.candidate_id.strip()
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty")
        return self


class KnowledgeCandidateApproveOutput(BaseModel):
    candidate: KnowledgeCandidateRecord | None = None
    resolved_card_id: str | None = None
    warning_summary: list[str] = Field(default_factory=empty_strings)


class KnowledgeCandidateRejectRequest(BaseModel):
    app_id: str
    candidate_id: str
    decision: KnowledgeReviewDecision = Field(default_factory=KnowledgeReviewDecision)

    @model_validator(mode="after")
    def validate_request(self) -> "KnowledgeCandidateRejectRequest":
        self.app_id = self.app_id.strip()
        self.candidate_id = self.candidate_id.strip()
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty")
        return self


class KnowledgeCandidateRejectOutput(BaseModel):
    candidate: KnowledgeCandidateRecord | None = None
    warning_summary: list[str] = Field(default_factory=empty_strings)


class AppKnowledgeRuntime(Protocol):
    def search(
        self,
        request: KnowledgeSearchRequest,
        *,
        context: KnowledgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeSearchOutput: ...

    def get(
        self,
        request: KnowledgeGetRequest,
        *,
        context: KnowledgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeGetOutput: ...

    def list(
        self,
        request: KnowledgeListRequest,
        *,
        context: KnowledgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeListOutput: ...

    def submit_candidate(
        self,
        request: KnowledgeSubmitCandidateRequest,
        *,
        context: KnowledgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeSubmitCandidateOutput: ...

    def list_candidates(
        self,
        request: KnowledgeCandidateListRequest,
        *,
        context: KnowledgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeCandidateListOutput: ...

    def approve_candidate(
        self,
        request: KnowledgeCandidateApproveRequest,
        *,
        context: KnowledgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeCandidateApproveOutput: ...

    def reject_candidate(
        self,
        request: KnowledgeCandidateRejectRequest,
        *,
        context: KnowledgeRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> KnowledgeCandidateRejectOutput: ...


class AppKnowledgeRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self, *, resolved_config: Any) -> AppKnowledgeRuntime: ...

    def diagnose(self) -> KnowledgeRuntimeHealth: ...


def list_knowledge_runtime_factories() -> dict[str, AppKnowledgeRuntimeFactory]:
    factories: dict[str, AppKnowledgeRuntimeFactory] = {}
    for entry_point in entry_points(group=APP_KNOWLEDGE_ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    if not factories:
        from .local_runtime import build_knowledge_runtime_factory

        factories["local"] = build_knowledge_runtime_factory()
    return factories


def resolve_knowledge_runtime_factory(runtime_name: str | None = None) -> AppKnowledgeRuntimeFactory:
    factories = list_knowledge_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise KnowledgeRuntimeUnavailableError(
                f"app knowledge runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise KnowledgeRuntimeUnavailableError(
            "no app knowledge runtime installed; install the app knowledge local runtime provider first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise KnowledgeRuntimeConflictError(
            "multiple app knowledge runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_knowledge_runtime(*, resolved_config: Any, runtime_name: str | None = None) -> AppKnowledgeRuntime:
    factory = resolve_knowledge_runtime_factory(runtime_name)
    return factory.create_runtime(resolved_config=resolved_config)


def diagnose_knowledge_runtime(runtime_name: str | None = None) -> KnowledgeRuntimeHealth:
    factory = resolve_knowledge_runtime_factory(runtime_name)
    return factory.diagnose()


__all__ = [
    "APP_KNOWLEDGE_ENTRY_POINT_GROUP",
    "AppKnowledgeRuntime",
    "AppKnowledgeRuntimeFactory",
    "KnowledgeCandidateApproveOutput",
    "KnowledgeCandidateApproveRequest",
    "KnowledgeCandidateListOutput",
    "KnowledgeCandidateListRequest",
    "KnowledgeCandidateRejectOutput",
    "KnowledgeCandidateRejectRequest",
    "KnowledgeGetOutput",
    "KnowledgeGetRequest",
    "KnowledgeListOutput",
    "KnowledgeListRequest",
    "KnowledgeManagedPaths",
    "KnowledgeRuntimeContext",
    "KnowledgeSearchOutput",
    "KnowledgeSearchRequest",
    "KnowledgeReviewDecision",
    "KnowledgeSubmitCandidateOutput",
    "KnowledgeSubmitCandidateRequest",
    "create_knowledge_runtime",
    "diagnose_knowledge_runtime",
    "list_knowledge_runtime_factories",
    "resolve_knowledge_runtime_factory",
]
