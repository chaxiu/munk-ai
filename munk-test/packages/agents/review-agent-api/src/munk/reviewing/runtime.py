from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from munk.agent_runtime.control import CancelController
from munk.agent_runtime.events import AgentEventSink

from .errors import ReviewRuntimeConflictError, ReviewRuntimeUnavailableError
from .health import ReviewRuntimeHealth
from .models import (
    ReviewFinding,
    ReviewKnowledgeHit,
    ReviewRequest,
    SuggestedFollowUpCase,
)
from .orchestration_models import ReviewOrchestrationContract

ENTRY_POINT_GROUP = "munk.review.runtimes"


def empty_strings() -> list[str]:
    return []


def empty_prompt_hits() -> list[ReviewKnowledgeHit]:
    return []


def empty_findings() -> list[ReviewFinding]:
    return []


def empty_follow_up_cases() -> list[SuggestedFollowUpCase]:
    return []


def empty_knowledge_hits() -> list[ReviewKnowledgeHit]:
    return []


class ReviewRuntimeResultData(BaseModel):
    app_id: str | None = None
    risk_summary: str
    likely_regression_surface: list[str] = Field(default_factory=empty_strings)
    missing_verification: list[str] = Field(default_factory=empty_strings)
    suggested_follow_up_cases: list[SuggestedFollowUpCase] = Field(default_factory=empty_follow_up_cases)
    findings: list[ReviewFinding] = Field(default_factory=empty_findings)
    knowledge_hits: list[ReviewKnowledgeHit] = Field(default_factory=empty_knowledge_hits)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def high_risk_count(self) -> int:
        return sum(1 for item in self.findings if item.severity in {"high", "critical"})


class ReviewRuntimeOutput(BaseModel):
    result_data: ReviewRuntimeResultData
    review_orchestration: ReviewOrchestrationContract
    started_at: str
    duration_ms: int
    warning_summary: list[str] = Field(default_factory=empty_strings)
    prompt_hits: list[ReviewKnowledgeHit] = Field(default_factory=empty_prompt_hits)
    retrieval_debug_payload: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ReviewManagedPaths:
    root_dir: Path
    review_request_path: Path
    retrieval_path: Path
    llm_transcript_path: Path | None


@dataclass(frozen=True)
class ReviewRuntimeContext:
    operation_id: str | None
    managed_paths: ReviewManagedPaths
    progress: AgentEventSink | None = None


class ReviewRuntime(Protocol):
    def review(
        self,
        request: ReviewRequest,
        *,
        context: ReviewRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> ReviewRuntimeOutput: ...


class ReviewRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self, *, resolved_config: Any) -> ReviewRuntime: ...

    def diagnose(self) -> ReviewRuntimeHealth: ...


def list_review_runtime_factories() -> dict[str, ReviewRuntimeFactory]:
    factories: dict[str, ReviewRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_review_runtime_factory(runtime_name: str | None = None) -> ReviewRuntimeFactory:
    factories = list_review_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise ReviewRuntimeUnavailableError(
                f"review runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise ReviewRuntimeUnavailableError(
            "no review local runtime installed; install the review local runtime package first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise ReviewRuntimeConflictError(
            "multiple review runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_review_runtime(
    *,
    resolved_config: Any,
    runtime_name: str | None = None,
) -> ReviewRuntime:
    factory = resolve_review_runtime_factory(runtime_name)
    return factory.create_runtime(resolved_config=resolved_config)


def diagnose_review_runtime(runtime_name: str | None = None) -> ReviewRuntimeHealth:
    factory = resolve_review_runtime_factory(runtime_name)
    return factory.diagnose()
