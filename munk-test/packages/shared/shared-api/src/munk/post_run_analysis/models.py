from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


def empty_object_dict() -> dict[str, object]:
    return {}


def empty_string_dict() -> dict[str, str]:
    return {}

TOP_LEVEL_CANONICAL_ARTIFACT_IDS = frozenset(
    {
        "attempts",
        "history",
        "retry_handoffs",
        "orchestration_result",
        "artifact_manifest",
        "result",
    }
)

ATTEMPT_CANONICAL_ARTIFACT_IDS = frozenset(
    {
        "judge_result",
        "decision_trace",
        "runner_history",
        "runner_memory",
        "context_prep",
        "log",
        "raw_screenshots",
        "annotated_screenshots",
        "observation_frames",
        "observation_diffs",
        "observation_tree",
        "llm_transcript",
    }
)


class PostRunAnalysisAgentInput(BaseModel):
    """Neutral host contract shared by post-run analysis agents such as optimize and knowledge."""

    app_id: str
    plan_id: str
    case_id: str
    case_title: str | None = None
    run_dir: Path
    execution_summary: dict[str, object] = Field(default_factory=empty_object_dict)
    judge_summary: dict[str, object] = Field(default_factory=empty_object_dict)
    artifacts: dict[str, str] = Field(default_factory=empty_string_dict)
    structured_evidence: dict[str, object] = Field(default_factory=empty_object_dict)
    source_attempt_index: int | None = None
    requirements: dict[str, object] = Field(default_factory=empty_object_dict)
