from __future__ import annotations

from pathlib import Path

from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionRequest, ExecutionOutcome
from munk.judging.models import JudgeResult
from munk.judging.runtime import JudgeRuntime
from munk.services.events import RunEvent
from munk.services.judge_runtime import resolve_judge_runtime

from .materializer import JudgeArtifactMaterializer, MaterializedJudgeArtifacts
from .runtime_host import (
    JudgeTrackerLike,
    build_judge_cancel_controller,
    build_judge_request,
    build_judge_runtime_context,
)


def execute_case_judging(
    *,
    request: CaseExecutionRequest,
    execution: ExecutionOutcome,
    events: list[RunEvent],
    artifacts: dict[str, str],
    resolved_config: ResolvedConfig,
    tracker: JudgeTrackerLike | None,
    judge_runtime: JudgeRuntime | None = None,
    raise_on_runtime_error: bool = True,
) -> MaterializedJudgeArtifacts:
    runtime = judge_runtime or resolve_judge_runtime(resolved_config=resolved_config)
    runtime_id = getattr(runtime, "runtime_id", None) or getattr(type(runtime), "runtime_id", None)
    judge_request = build_judge_request(
        request=request,
        execution=execution,
        events=events,
        artifacts=artifacts,
    )
    built_context = build_judge_runtime_context(
        run_dir=artifacts_root(artifacts),
        tracker=tracker,
    )
    materializer = JudgeArtifactMaterializer(resolved_config=resolved_config)
    try:
        runtime_output = runtime.judge(
            judge_request,
            context=built_context.runtime_context,
            cancel_controller=build_judge_cancel_controller(tracker=tracker),
        )
    except Exception as exc:
        materialized = materializer.materialize_failure(
            request=judge_request,
            context=built_context.runtime_context,
            host_paths=built_context.host_paths,
            execution=judge_request.execution,
            exc=exc,
            runtime_id=str(runtime_id) if runtime_id else None,
        )
        if raise_on_runtime_error:
            raise
        return materialized
    return materializer.materialize_success(
        runtime_output=runtime_output,
        request=judge_request,
        context=built_context.runtime_context,
        host_paths=built_context.host_paths,
        runtime_id=str(runtime_id) if runtime_id else None,
    )


def build_case_judge_result(materialized: MaterializedJudgeArtifacts) -> JudgeResult:
    return materialized.result


def artifacts_root(artifacts: dict[str, str]) -> Path:
    result_path = artifacts.get("result")
    if result_path:
        return Path(result_path).parent
    case_path = artifacts.get("case")
    if case_path:
        return Path(case_path).parent
    raise ValueError("judge orchestration requires a run_dir in artifacts")
