from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from munk.agent_runtime import AgentRuntimeEvent, AgentRuntimeEventEmitter, CancelController
from munk.config import ResolvedConfig
from munk.device import resolve_device_runtime_factory
from munk.execution.models import CaseExecutionRequest
from munk.paths import export_adb_env
from munk.running import RunnerRequest, RunnerRuntimeContext, apply_runtime_overrides
from munk.services.events import RunEventSink
from munk.services.ios import IOSDeviceBridgeDiagnosticsContext
from munk.services.models import RunPaths, RunStartParams
from munk.services.operations.runtime_event_sinks import TrackerAgentRuntimeTimelineSink
from munk.services.operations.service import OperationTracker
from munk.services.perception_runtime import build_perception_provider_for_runtime
from munk.services.running.start_state import prepare_case_start_state

from .runtime_bridge import (
    build_runner_request_from_case_execution_request,
    build_runner_runtime_context,
)


class TrackerCancelController(CancelController):
    def __init__(self, tracker: OperationTracker) -> None:
        self._tracker = tracker

    def is_cancel_requested(self) -> bool:
        return self._tracker.should_cancel()


@dataclass(frozen=True)
class RunnerHostManagedPaths:
    root_dir: Path
    result_path: Path
    diagnostics_path: Path
    artifact_manifest_path: Path


@dataclass(frozen=True)
class BuiltRunnerHostBundle:
    runner_request: RunnerRequest
    runtime_context: RunnerRuntimeContext
    host_paths: RunnerHostManagedPaths
    params: RunStartParams


def build_runner_host_paths(paths: RunPaths) -> RunnerHostManagedPaths:
    return RunnerHostManagedPaths(
        root_dir=paths.run_dir,
        result_path=paths.result_path or (paths.run_dir / "result.json"),
        diagnostics_path=paths.run_dir / "diagnostics.json",
        artifact_manifest_path=paths.run_dir / "artifact_manifest.json",
    )


def build_runner_host_bundle(
    *,
    request: CaseExecutionRequest,
    resolved_config: ResolvedConfig,
    paths: RunPaths,
    tracker: OperationTracker | None,
    event_sink: RunEventSink | None,
    attempt_index: int,
) -> BuiltRunnerHostBundle:
    host_paths = build_runner_host_paths(paths)
    emitter = _build_context_prepare_emitter(
        request=request,
        tracker=tracker,
        attempt_index=attempt_index,
    )
    emitter.emit_started(
        event_type="context_prepare_started",
        message="context prepare started",
        timeline_phase="started",
        summary="context prepare started",
    )
    params = build_run_start_params(request=request, resolved_config=resolved_config)
    emitter.emit_progress(
        event_type="context_prepare_params_resolved",
        message="context prepare resolved runtime params",
        timeline_phase="prepared",
        summary="runtime params resolved",
        data={
            "device_ref": params.device_ref,
            "max_steps": params.runtime.max_steps,
            "max_seconds": params.runtime.max_seconds,
            "interval": params.runtime.interval,
            "initial_ready_timeout_sec": params.runtime.initial_ready_timeout_sec,
            "max_side": params.runtime.max_side,
            "settle_timeout": params.runtime.settle_timeout,
            "settle_mode": params.runtime.settle_mode,
            "settle_ocr_only": params.runtime.settle_ocr_only,
            "settle_ratio_threshold": params.runtime.settle_ratio_threshold,
            "settle_delay_sec": params.runtime.settle_delay_sec,
        },
    )
    export_adb_env()
    factory = resolve_device_runtime_factory(platform=request.app_target.platform)
    _configure_device_diagnostics(
        factory=factory,
        request=request,
        paths=paths,
        tracker=tracker,
    )
    device = factory.create_device(device_ref=params.device_ref, app_target=request.app_target)
    emitter.emit_progress(
        event_type="context_prepare_device_ready",
        message="context prepare created device runtime",
        timeline_phase="prepared",
        summary="device runtime ready",
        data={"device_ref": params.device_ref, "platform": request.app_target.platform},
    )
    prepare_case_start_state(
        device=device,
        case=request.case,
        app_target=request.app_target,
    )
    emitter.emit_progress(
        event_type="context_prepare_start_state_ready",
        message="context prepare ready state prepared",
        timeline_phase="prepared",
        summary="case start state prepared",
    )
    perception = build_perception_provider_for_runtime(
        resolved_config.config,
        max_side=params.runtime.max_side,
        icon_conf=params.runtime.icon_conf,
    )
    emitter.emit_progress(
        event_type="context_prepare_perception_ready",
        message="context prepare perception provider ready",
        timeline_phase="prepared",
        summary="perception provider ready",
        data={"max_side": params.runtime.max_side, "icon_conf": params.runtime.icon_conf},
    )
    progress = TrackerAgentRuntimeTimelineSink(
        tracker,
        progress_builder=lambda event: {"runner_event_type": event.event_type},
    ) if tracker is not None else None
    emitter.emit_ended(
        event_type="context_prepare_completed",
        message="context prepare completed",
        timeline_phase="completed",
        summary="context prepare completed",
    )
    return BuiltRunnerHostBundle(
        runner_request=build_runner_request_from_case_execution_request(request),
        runtime_context=build_runner_runtime_context(
            operation_id=tracker.operation_id if tracker is not None else None,
            attempt_index=attempt_index,
            paths=paths,
            device=device,
            perception=perception,
            progress=progress,
        ),
        host_paths=host_paths,
        params=params,
    )


def _build_context_prepare_emitter(
    *,
    request: CaseExecutionRequest,
    tracker: OperationTracker | None,
    attempt_index: int,
) -> AgentRuntimeEventEmitter:
    return AgentRuntimeEventEmitter(
        agent_role="context_prepare",
        operation_id=tracker.operation_id if tracker is not None else None,
        event_sink=TrackerAgentRuntimeTimelineSink(
            tracker,
            progress_builder=lambda event: {"runner_event_type": event.event_type},
        )
        if tracker is not None
        else None,
        timeline_scope="parent_run",
        attempt_index=attempt_index,
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=request.case.case_id,
    )


def _configure_device_diagnostics(
    *,
    factory: object,
    request: CaseExecutionRequest,
    paths: RunPaths,
    tracker: OperationTracker | None,
) -> None:
    if request.app_target.platform != "ios":
        return
    setter = getattr(factory, "set_diagnostics_context", None)
    if not callable(setter):
        return
    setter(
        IOSDeviceBridgeDiagnosticsContext(
            operation_id=tracker.operation_id if tracker is not None else None,
            run_dir=str(paths.run_dir),
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case.case_id,
        )
    )


def build_runner_cancel_controller(*, tracker: OperationTracker | None) -> CancelController | None:
    if tracker is None:
        return None
    return TrackerCancelController(tracker)


def build_run_start_params(
    *,
    request: CaseExecutionRequest,
    resolved_config: ResolvedConfig,
) -> RunStartParams:
    params = RunStartParams(
        resolved_config=resolved_config,
        app_target=request.app_target,
        device_ref=request.device_ref,
    )
    return replace(params, runtime=apply_runtime_overrides(params.runtime, request.runtime_overrides))
