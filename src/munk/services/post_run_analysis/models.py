from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from munk.execution.models import CaseExecutionResult
from munk.judging import JudgeResult
from munk.post_run_analysis import (
    ATTEMPT_CANONICAL_ARTIFACT_IDS,
    TOP_LEVEL_CANONICAL_ARTIFACT_IDS,
    PostRunAnalysisAgentInput,
)

__all__ = [
    "ATTEMPT_CANONICAL_ARTIFACT_IDS",
    "TOP_LEVEL_CANONICAL_ARTIFACT_IDS",
    "CaseRunEvidence",
    "PostRunAnalysisAgentInput",
]


@dataclass(frozen=True)
class CaseRunEvidence:
    case_result: CaseExecutionResult
    source_attempt_index: int | None
    judge_result_path: Path | None
    judge_result: JudgeResult | None
    artifacts: dict[str, str]
    canonical_artifacts: dict[str, Path]
