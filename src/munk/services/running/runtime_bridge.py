from __future__ import annotations

from munk.agent_runtime.events import AgentEventSink
from munk.device import DeviceDriver
from munk.execution.models import CaseExecutionRequest
from munk.perception import PerceptionProvider
from munk.running import (
    RunnerManagedPaths,
    RunnerRequest,
    RunnerRuntimeContext,
    RunnerRuntimeResultData,
    build_runner_runtime_result_data,
)
from munk.services.models import RunnerKernelResult, RunPaths


def build_runner_request_from_case_execution_request(request: CaseExecutionRequest) -> RunnerRequest:
    return RunnerRequest(
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=request.case.case_id,
        case=request.case.model_copy(deep=True),
        app_target=request.app_target.model_copy(deep=True),
        device_ref=request.device_ref,
        assets_root=request.assets_root,
        runtime_overrides=dict(request.runtime_overrides),
    )


def build_runner_managed_paths(paths: RunPaths) -> RunnerManagedPaths:
    return RunnerManagedPaths(
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
    )


def build_runner_runtime_context(
    *,
    operation_id: str | None,
    paths: RunPaths,
    device: DeviceDriver,
    perception: PerceptionProvider,
    progress: AgentEventSink | None = None,
) -> RunnerRuntimeContext:
    return RunnerRuntimeContext(
        operation_id=operation_id,
        managed_paths=build_runner_managed_paths(paths),
        device=device,
        perception=perception,
        progress=progress,
    )


def build_runner_runtime_result_data_from_kernel_result(
    kernel_result: RunnerKernelResult,
) -> RunnerRuntimeResultData:
    return build_runner_runtime_result_data(
        status=kernel_result.status,
        stop_reason=kernel_result.stop_reason,
        steps_completed=kernel_result.steps_completed,
        last_action_summary=kernel_result.last_action_summary,
        last_target_identity=kernel_result.last_target_identity,
        last_surface_identity=kernel_result.last_surface_identity,
    )
