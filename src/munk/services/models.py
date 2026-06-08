from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from munk.app import AppTarget
from munk.config import ResolvedConfig
from munk.config.defaults import DEFAULT_RUNNER_MAX_ELEMENTS
from munk.execution.models import ExecutionStatus
from munk.perception.diagnostics import PerceptionProviderDiagnostics
from munk.runtime_defaults import (
    DEFAULT_ICON_CONF,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MAX_SIDE,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SETTLE_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_VL_MAX_SIDE,
)


def empty_missing_items() -> list[str]:
    return []


@dataclass(frozen=True)
class RunStartParams:
    resolved_config: ResolvedConfig
    app_target: AppTarget | None = None
    device_ref: str | None = None
    max_steps: int = DEFAULT_MAX_STEPS
    max_seconds: float = DEFAULT_MAX_SECONDS
    interval: float = DEFAULT_INTERVAL
    settle_timeout: float = DEFAULT_SETTLE_TIMEOUT
    initial_ready_timeout_sec: float = DEFAULT_SETTLE_TIMEOUT
    max_side: int = DEFAULT_MAX_SIDE
    icon_conf: float = DEFAULT_ICON_CONF
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    vl_max_side: int = DEFAULT_VL_MAX_SIDE
    runner_max_elements: int = DEFAULT_RUNNER_MAX_ELEMENTS


@dataclass(frozen=True)
class RunPaths:
    run_dir: Path
    log_path: Path
    raw_dir: Path
    annotated_dir: Path
    runtime_logs_dir: Path | None = None
    observation_dir: Path | None = None
    observation_frames_dir: Path | None = None
    observation_diffs_dir: Path | None = None
    observation_tree_dir: Path | None = None
    case_path: Path | None = None
    result_path: Path | None = None
    decision_trace_path: Path | None = None
    runner_history_path: Path | None = None
    runner_memory_path: Path | None = None
    llm_transcript_path: Path | None = None
    context_prep_path: Path | None = None


@dataclass(frozen=True)
class RunSummary:
    run_dir: Path
    log_path: Path
    steps_completed: int
    stop_reason: str | None


@dataclass(frozen=True)
class RunnerKernelResult:
    steps_completed: int
    stop_reason: str | None
    status: ExecutionStatus
    last_action_summary: str | None = None
    # Last observed target/app identity.
    last_target_identity: str | None = None
    # Page/surface-level identity for the last observed screen.
    last_surface_identity: str | None = None


@dataclass(frozen=True)
class RunStatus:
    running: bool
    run_dir: Path | None = None
    steps_completed: int = 0
    last_event_type: str | None = None
    stop_requested: bool = False


@dataclass(frozen=True)
class DoctorResult:
    adb_path: Path
    perception_diagnostics: PerceptionProviderDiagnostics | None = None
    missing_items: list[str] = field(default_factory=empty_missing_items)

    @property
    def ok(self) -> bool:
        return not self.missing_items


@dataclass(frozen=True)
class AnnotateRequest:
    image_path: Path
    output_path: Path | None = None
    max_side: int = 1600
    icon_conf: float = 0.12
    resolved_config: ResolvedConfig | None = None


@dataclass(frozen=True)
class AnnotateResult:
    output_path: Path
    element_count: int
