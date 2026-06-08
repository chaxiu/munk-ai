from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from munk.agent_runtime import AgentRuntimeEvent, CancelController
from munk.config import ResolvedConfig
from munk.device import resolve_device_runtime_factory
from munk.execution.models import CaseExecutionRequest, RuntimeOverrideValue
from munk.paths import export_adb_env
from munk.running import RunnerRequest, RunnerRuntimeContext
from munk.services.events import RunEventSink
from munk.services.models import RunPaths, RunStartParams
from munk.services.operations.service import OperationTracker
from munk.services.perception_runtime import build_perception_provider_for_runtime
from munk.services.running.start_state import prepare_case_start_state

from .runtime_bridge import (
    build_runner_request_from_case_execution_request,
    build_runner_runtime_context,
)


class TrackerRunnerProgressSink:
    def __init__(self, tracker: OperationTracker) -> None:
        self._tracker = tracker

    def emit(self, event: AgentRuntimeEvent) -> None:
        data = dict(event.data)
        data["lifecycle_state"] = event.lifecycle_state
        data["agent_role"] = event.agent_role
        data["timestamp"] = event.timestamp
        self._tracker.append_event(event_type=event.event_type, message=event.message, data=data)
        progress: dict[str, object] = {
            "lifecycle_state": event.lifecycle_state,
            "agent_role": event.agent_role,
            "event_timestamp": event.timestamp,
            "runner_event_type": event.event_type,
        }
        for key in ("app_id", "plan_id", "case_id", "step", "action", "summary", "stop_reason"):
            if key in data and data[key] is not None:
                progress[key] = data[key]
        self._tracker.update_progress(**progress)


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
) -> BuiltRunnerHostBundle:
    host_paths = build_runner_host_paths(paths)
    params = build_run_start_params(request=request, resolved_config=resolved_config)
    export_adb_env()
    factory = resolve_device_runtime_factory(platform=request.app_target.platform)
    device = factory.create_device(device_ref=params.device_ref, app_target=request.app_target)
    prepare_case_start_state(
        device=device,
        case=request.case,
        app_target=request.app_target,
    )
    perception = build_perception_provider_for_runtime(
        resolved_config.config,
        max_side=params.max_side,
        icon_conf=params.icon_conf,
    )
    progress = TrackerRunnerProgressSink(tracker) if tracker is not None else None
    return BuiltRunnerHostBundle(
        runner_request=build_runner_request_from_case_execution_request(request),
        runtime_context=build_runner_runtime_context(
            operation_id=tracker.operation_id if tracker is not None else None,
            paths=paths,
            device=device,
            perception=perception,
            progress=progress,
        ),
        host_paths=host_paths,
        params=params,
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
    for key, value in request.runtime_overrides.items():
        params = apply_runtime_override(params, key, value)
    return params


def apply_runtime_override(
    params: RunStartParams,
    key: str,
    value: RuntimeOverrideValue,
) -> RunStartParams:
    if key in {"device_ref", "goal", "app_id", "plan_id", "case_id"}:
        raise ValueError(f"{key} is managed by case context and cannot be overridden")
    if key == "max_steps":
        return replace(params, max_steps=require_int_override(key, value))
    if key in {"max_seconds", "interval", "settle_timeout", "initial_ready_timeout_sec", "icon_conf", "temperature"}:
        return replace(params, **{key: require_float_override(key, value)})
    if key in {"max_side", "max_tokens", "vl_max_side", "runner_max_elements"}:
        return replace(params, **{key: require_int_override(key, value)})
    raise ValueError(f"unsupported runtime override: {key}")


def require_int_override(key: str, value: RuntimeOverrideValue) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"runtime override '{key}' must be an integer")
    return value


def require_float_override(key: str, value: RuntimeOverrideValue) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"runtime override '{key}' must be a number")
    return float(value)
