from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from munk.agent_runtime.events import AgentEventSink
from munk.app_knowledge import KnowledgeCandidateSubmission
from munk.judging import JudgeResult
from pydantic import BaseModel, ConfigDict, Field, model_validator


def empty_strings() -> list[str]:
    return []


def empty_artifacts() -> list["KnowledgeArtifactRef"]:
    return []


def empty_submissions() -> list[KnowledgeCandidateSubmission]:
    return []


def empty_payload() -> dict[str, Any]:
    return {}


class KnowledgeArtifactRef(BaseModel):
    artifact_id: str
    path: Path

    @model_validator(mode="after")
    def validate_ref(self) -> "KnowledgeArtifactRef":
        self.artifact_id = self.artifact_id.strip()
        if not self.artifact_id:
            raise ValueError("artifact_id must not be empty")
        return self


class KnowledgeAgentEvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    judge_result: JudgeResult
    judge_result_path: Path | None = None
    artifacts: list[KnowledgeArtifactRef] = Field(default_factory=empty_artifacts)


class KnowledgeAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    plan_id: str
    case_id: str
    case_title: str | None = None
    run_dir: Path
    evidence_bundle: KnowledgeAgentEvidenceBundle

    @model_validator(mode="after")
    def validate_request(self) -> "KnowledgeAgentRequest":
        self.app_id = self.app_id.strip()
        self.plan_id = self.plan_id.strip()
        self.case_id = self.case_id.strip()
        if self.case_title is not None:
            self.case_title = self.case_title.strip() or None
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.plan_id:
            raise ValueError("plan_id must not be empty")
        if not self.case_id:
            raise ValueError("case_id must not be empty")
        if self.evidence_bundle.judge_result.app_id != self.app_id:
            raise ValueError("judge_result.app_id must match app_id")
        if self.evidence_bundle.judge_result.plan_id != self.plan_id:
            raise ValueError("judge_result.plan_id must match plan_id")
        if self.evidence_bundle.judge_result.case_id != self.case_id:
            raise ValueError("judge_result.case_id must match case_id")
        return self


class KnowledgeAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    candidate_submissions: list[KnowledgeCandidateSubmission] = Field(default_factory=empty_submissions)
    skip_reason: str | None = None
    warning_summary: list[str] = Field(default_factory=empty_strings)
    tool_calls: list[str] = Field(default_factory=empty_strings)
    artifacts: dict[str, str] = Field(default_factory=empty_payload)


@dataclass(frozen=True)
class KnowledgeAgentManagedPaths:
    root_dir: Path
    prompt_path: Path
    tool_calls_path: Path
    llm_transcript_path: Path | None = None


@dataclass(frozen=True)
class KnowledgeAgentRuntimeContext:
    operation_id: str | None
    managed_paths: KnowledgeAgentManagedPaths
    progress: AgentEventSink | None = None
