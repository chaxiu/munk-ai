from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from contextvars import copy_context
from datetime import datetime, timezone
from typing import Any, Callable

from munk.agent_base.llm import llm_transcript_scope, summarize_llm_transcript_usage
from munk.agent_runtime.events import AgentRuntimeEventEmitter
from munk.running import (
    RunnerRequest,
    RunnerRuntimeContext,
    RunnerRuntimeOutput,
    build_runner_runtime_result_data,
)

from munk.config import ResolvedConfig
from munk.services.events import RunEventSink

from .context import (
    RunContext,
    build_local_runner_context,
    prepare_runner_context,
)
from .loop import execute_run_loop


def _submit_with_current_context(
    executor: ThreadPoolExecutor,
    fn: Callable[..., Any],
    /,
    *args: Any,
    **kwargs: Any,
) -> Future[Any]:
    context = copy_context()
    return executor.submit(lambda: context.run(fn, *args, **kwargs))


class RunnerRuntimeService:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._event_sink = event_sink

    def run(
        self,
        request: RunnerRequest,
        *,
        context: RunnerRuntimeContext,
        cancel_controller=None,  # noqa: ANN001
    ) -> RunnerRuntimeOutput:
        emitter = AgentRuntimeEventEmitter(
            agent_role="runner",
            operation_id=context.operation_id,
            event_sink=context.progress,
        )
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        emitter.emit_started(
            message="runner runtime started",
            data={"app_id": request.app_id, "plan_id": request.plan_id, "case_id": request.case_id},
        )
        run_context: RunContext | None = None
        try:
            self._write_request_dump(request, context)
            run_context = build_local_runner_context(
                request=request,
                runtime_context=context,
                resolved_config=self._resolved_config,
                event_sink=self._event_sink,
            )
            prep_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="context-prep")
            run_context.context_prep_executor = prep_executor
            run_context.context_prep_future = _submit_with_current_context(
                prep_executor,
                prepare_runner_context,
                run_context,
            )
            emitter.emit_progress(
                event_type="runner_context_loaded",
                message="runner context loaded",
                data={"app_id": request.app_id, "case_id": request.case_id, "root_dir": str(context.managed_paths.root_dir)},
            )
            with llm_transcript_scope(context.managed_paths.llm_transcript_path):
                kernel_result = execute_run_loop(
                    context=run_context,
                    event_sink=self._event_sink,
                    should_stop=lambda: self._should_stop(cancel_controller),
                )
            output = RunnerRuntimeOutput(
                result_data=build_runner_runtime_result_data(
                    status=kernel_result.status,
                    stop_reason=kernel_result.stop_reason,
                    steps_completed=kernel_result.steps_completed,
                    last_action_summary=kernel_result.last_action_summary,
                    last_target_identity=kernel_result.last_target_identity,
                    last_surface_identity=kernel_result.last_surface_identity,
                ),
                started_at=started_at,
                duration_ms=int((time.monotonic() - started) * 1000),
                token_usage=summarize_llm_transcript_usage(context.managed_paths.llm_transcript_path),
            )
        except Exception as exc:
            emitter.emit_failed(
                message="runner runtime failed",
                data={
                    "app_id": request.app_id,
                    "case_id": request.case_id,
                    "error_type": exc.__class__.__name__,
                },
            )
            raise
        finally:
            if run_context is not None:
                self._finalize_runtime_logs(run_context)
                self._shutdown_context_prep(run_context)
        if self._should_stop(cancel_controller) or output.result_data.stop_reason == "stop_requested":
            emitter.emit_canceled(
                message="runner runtime canceled",
                data={"app_id": request.app_id, "plan_id": request.plan_id, "case_id": request.case_id},
            )
        else:
            emitter.emit_ended(
                message="runner runtime completed",
                data={
                    "app_id": request.app_id,
                    "plan_id": request.plan_id,
                    "case_id": request.case_id,
                    "status": output.result_data.status,
                    "stop_reason": output.result_data.stop_reason,
                    "steps_completed": output.result_data.steps_completed,
                },
            )
        return output

    @staticmethod
    def _should_stop(cancel_controller) -> bool:  # noqa: ANN001
        return bool(cancel_controller is not None and cancel_controller.is_cancel_requested())

    @staticmethod
    def _write_request_dump(request: RunnerRequest, context: RunnerRuntimeContext) -> None:
        context.managed_paths.request_dump_path.write_text(
            request.model_dump_json(indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _finalize_runtime_logs(context: RunContext) -> None:
        if context.log_collector is None:
            return
        context.log_collector.finalize()

    @staticmethod
    def _shutdown_context_prep(context: RunContext) -> None:
        executor = context.context_prep_executor
        if executor is None:
            return
        executor.shutdown(wait=False, cancel_futures=False)
