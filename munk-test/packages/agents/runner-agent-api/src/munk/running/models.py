from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from munk.agent_runtime.events import AgentEventSink
from munk.app import AppTarget
from munk.device import DeviceDriver
from munk.perception import PerceptionProvider
from munk.testing import TestCase
from munk.token_usage import TokenUsage

if TYPE_CHECKING:
    from munk.services.models import RunPaths

RuntimeOverrideValue = str | int | float | bool
RunnerExecutionStatus = Literal["completed", "failed", "incomplete"]


def empty_runtime_overrides() -> dict[str, RuntimeOverrideValue]:
    return {}


def empty_warning_summary() -> list[str]:
    return []


class RunnerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    plan_id: str
    case_id: str
    case: TestCase
    app_target: AppTarget
    device_ref: str | None = None
    assets_root: Path | None = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=empty_runtime_overrides)

    @model_validator(mode="after")
    def validate_request(self) -> "RunnerRequest":
        self.app_id = self.app_id.strip()
        self.plan_id = self.plan_id.strip()
        self.case_id = self.case_id.strip()
        if not self.app_id:
            raise ValueError("app_id must not be empty")
        if not self.plan_id:
            raise ValueError("plan_id must not be empty")
        if not self.case_id:
            raise ValueError("case_id must not be empty")
        if self.case.case_id.strip() != self.case_id:
            raise ValueError("case_id must match case.case_id")
        return self


class RunnerRuntimeResultData(BaseModel):
    status: RunnerExecutionStatus
    stop_reason: str | None = None
    steps_completed: int = 0
    last_action_summary: str | None = None
    last_target_identity: str | None = None
    last_surface_identity: str | None = None


def build_runner_runtime_result_data(
    *,
    status: RunnerExecutionStatus,
    stop_reason: str | None,
    steps_completed: int,
    last_action_summary: str | None = None,
    last_target_identity: str | None = None,
    last_surface_identity: str | None = None,
) -> "RunnerRuntimeResultData":
    return RunnerRuntimeResultData(
        status=status,
        stop_reason=stop_reason,
        steps_completed=steps_completed,
        last_action_summary=last_action_summary,
        last_target_identity=last_target_identity,
        last_surface_identity=last_surface_identity,
    )


class RunnerRuntimeOutput(BaseModel):
    result_data: RunnerRuntimeResultData
    started_at: str
    duration_ms: int
    warning_summary: list[str] = Field(default_factory=empty_warning_summary)
    token_usage: TokenUsage | None = None


@dataclass(frozen=True)
class RunnerManagedPaths:
    root_dir: Path
    request_dump_path: Path
    raw_dir: Path
    annotated_dir: Path
    runtime_logs_dir: Path | None
    observation_frames_dir: Path | None
    observation_diffs_dir: Path | None
    observation_tree_dir: Path | None
    decision_trace_path: Path | None
    runner_history_path: Path | None
    runner_memory_path: Path | None
    llm_transcript_path: Path | None
    context_prep_path: Path | None
    runner_issues_path: Path | None = None

    @classmethod
    def from_run_paths(cls, paths: "RunPaths") -> "RunnerManagedPaths":
        return cls(
            root_dir=paths.run_dir,
            request_dump_path=paths.case_path or (paths.run_dir / "runner_request.json"),
            raw_dir=paths.raw_dir,
            annotated_dir=paths.annotated_dir,
            runtime_logs_dir=paths.runtime_logs_dir,
            observation_frames_dir=paths.observation_frames_dir,
            observation_diffs_dir=paths.observation_diffs_dir,
            observation_tree_dir=paths.observation_tree_dir,
            decision_trace_path=paths.decision_trace_path,
            runner_history_path=paths.runner_history_path,
            runner_memory_path=paths.runner_memory_path,
            llm_transcript_path=paths.llm_transcript_path,
            context_prep_path=paths.context_prep_path,
            runner_issues_path=paths.runner_issues_path,
        )

    def to_run_paths(self) -> "RunPaths":
        from munk.services.models import RunPaths

        return RunPaths(
            run_dir=self.root_dir,
            log_path=self.root_dir / "run.log",
            raw_dir=self.raw_dir,
            annotated_dir=self.annotated_dir,
            runtime_logs_dir=self.runtime_logs_dir,
            observation_frames_dir=self.observation_frames_dir,
            observation_diffs_dir=self.observation_diffs_dir,
            observation_tree_dir=self.observation_tree_dir,
            case_path=self.request_dump_path,
            result_path=self.root_dir / "result.json",
            decision_trace_path=self.decision_trace_path,
            runner_history_path=self.runner_history_path,
            runner_memory_path=self.runner_memory_path,
            runner_issues_path=self.runner_issues_path,
            llm_transcript_path=self.llm_transcript_path,
            context_prep_path=self.context_prep_path,
        )


@dataclass(frozen=True)
class RunnerRuntimeContext:
    operation_id: str | None
    managed_paths: RunnerManagedPaths
    device: DeviceDriver
    perception: PerceptionProvider
    attempt_index: int = 0
    progress: AgentEventSink | None = None
