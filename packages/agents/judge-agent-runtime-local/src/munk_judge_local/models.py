from __future__ import annotations

from munk.judging.models import JudgeEvidence, JudgeExecutionSummary
from munk.testing import AiGuidance
from pydantic import BaseModel, Field


def empty_strings() -> list[str]:
    return []


def empty_evidence() -> list[JudgeEvidence]:
    return []


def empty_screenshots() -> list["JudgeScreenshotRef"]:
    return []


def empty_summary_items() -> list[dict[str, object]]:
    return []


class JudgeScreenshotRef(BaseModel):
    screenshot_id: str
    step_index: int
    kind: str
    path: str
    package: str | None = None
    action_summary: str | None = None
    observation_summary: str | None = None
    tree_evidence_id: str | None = None
    diff_evidence_id: str | None = None


class JudgeEvidencePack(BaseModel):
    plan_id: str
    case_id: str
    case_title: str
    intent: str
    preconditions: list[str] = Field(default_factory=empty_strings)
    expected: list[str] = Field(default_factory=empty_strings)
    runner_goal: str
    ai_guidance: AiGuidance | None = None
    execution: JudgeExecutionSummary
    primary_evidence: list[JudgeEvidence] = Field(default_factory=empty_evidence)
    supporting_evidence: list[JudgeEvidence] = Field(default_factory=empty_evidence)
    evidence: list[JudgeEvidence] = Field(default_factory=empty_evidence)
    runner_memory_summary: list[dict[str, object]] = Field(default_factory=empty_summary_items)
    recent_raw_screenshots: list[JudgeScreenshotRef] = Field(default_factory=empty_screenshots)
    recent_annotated_screenshots: list[JudgeScreenshotRef] = Field(default_factory=empty_screenshots)
    artifacts: dict[str, str] = Field(default_factory=dict)
