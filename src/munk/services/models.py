from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from munk.app import AppTarget
from munk.config import ResolvedConfig
from munk.execution.models import ExecutionStatus
from munk.perception.diagnostics import PerceptionProviderDiagnostics
from munk.runtime_defaults import (
    DEFAULT_ICON_CONF,
    DEFAULT_INITIAL_READY_TIMEOUT_SEC,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MAX_SIDE,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_RUNNER_INCLUDE_SCREENSHOT,
    DEFAULT_RUNNER_MAX_ELEMENTS,
    DEFAULT_SETTLE_DELAY_SEC,
    DEFAULT_SETTLE_MODE,
    DEFAULT_SETTLE_OCR_ONLY,
    DEFAULT_SETTLE_RATIO_THRESHOLD,
    DEFAULT_SETTLE_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_VL_FALLBACK_IMAGE_FORMAT,
    DEFAULT_VL_IMAGE_FORMAT,
    DEFAULT_VL_JPEG_QUALITY,
    DEFAULT_VL_MAX_SIDE,
    DEFAULT_VL_WEBP_QUALITY,
)
from munk.artifacts import (
    ARTIFACT_ID_CASE,
    ARTIFACT_ID_LOG,
    ARTIFACT_ID_RESULT,
    RUN_PATH_OPTIONAL_ARTIFACT_SPECS,
)

if TYPE_CHECKING:
    from munk.running import RunnerManagedPaths


def empty_missing_items() -> list[str]:
    return []


@dataclass(frozen=True)
class RunnerRuntimeParams:
    max_steps: int = DEFAULT_MAX_STEPS
    max_seconds: float = DEFAULT_MAX_SECONDS
    interval: float = DEFAULT_INTERVAL
    settle_timeout: float = DEFAULT_SETTLE_TIMEOUT
    settle_mode: str = DEFAULT_SETTLE_MODE
    settle_ocr_only: bool = DEFAULT_SETTLE_OCR_ONLY
    settle_ratio_threshold: float = DEFAULT_SETTLE_RATIO_THRESHOLD
    settle_delay_sec: float = DEFAULT_SETTLE_DELAY_SEC
    initial_ready_timeout_sec: float = DEFAULT_INITIAL_READY_TIMEOUT_SEC
    max_side: int = DEFAULT_MAX_SIDE
    icon_conf: float = DEFAULT_ICON_CONF
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    vl_max_side: int = DEFAULT_VL_MAX_SIDE
    vl_image_format: str = DEFAULT_VL_IMAGE_FORMAT
    vl_fallback_image_format: str = DEFAULT_VL_FALLBACK_IMAGE_FORMAT
    vl_webp_quality: int = DEFAULT_VL_WEBP_QUALITY
    vl_jpeg_quality: int = DEFAULT_VL_JPEG_QUALITY
    runner_max_elements: int = DEFAULT_RUNNER_MAX_ELEMENTS
    runner_include_screenshot: bool = DEFAULT_RUNNER_INCLUDE_SCREENSHOT


@dataclass(frozen=True, init=False)
class RunStartParams:
    resolved_config: ResolvedConfig
    app_target: AppTarget | None = None
    device_ref: str | None = None
    runtime: RunnerRuntimeParams = field(default_factory=RunnerRuntimeParams)

    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        app_target: AppTarget | None = None,
        device_ref: str | None = None,
        runtime: RunnerRuntimeParams | None = None,
        **runtime_values: Any,
    ) -> None:
        if runtime is not None and runtime_values:
            raise TypeError("Pass either runtime or flat runtime kwargs when constructing RunStartParams")
        object.__setattr__(self, "resolved_config", resolved_config)
        object.__setattr__(self, "app_target", app_target)
        object.__setattr__(self, "device_ref", device_ref)
        object.__setattr__(
            self,
            "runtime",
            runtime if runtime is not None else RunnerRuntimeParams(**runtime_values),
        )

    def __getattr__(self, name: str) -> Any:
        runtime = object.__getattribute__(self, "runtime")
        if hasattr(runtime, name):
            return getattr(runtime, name)
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")


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
    runner_issues_path: Path | None = None
    llm_transcript_path: Path | None = None
    context_prep_path: Path | None = None

    def to_runner_managed_paths(self) -> "RunnerManagedPaths":
        from munk.running import RunnerManagedPaths

        return RunnerManagedPaths.from_run_paths(self)

    def publishable_artifacts(self) -> dict[str, Path]:
        artifacts: dict[str, Path] = {
            ARTIFACT_ID_CASE: self.case_path or (self.run_dir / "case.json"),
            ARTIFACT_ID_RESULT: self.result_path or (self.run_dir / "result.json"),
            ARTIFACT_ID_LOG: self.log_path,
        }
        for spec in RUN_PATH_OPTIONAL_ARTIFACT_SPECS:
            path = getattr(self, spec.run_paths_attr)
            if path is None:
                continue
            if spec.require_existing_path and not path.exists():
                continue
            artifacts[spec.artifact_id] = path
        return artifacts


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
