from __future__ import annotations

import logging
import time

from munk.services.models import RunnerKernelResult

from .context import RunContext, prepare_runner_context

logger = logging.getLogger(__name__)


def build_run_result(
    *,
    step_index: int,
    stop_reason: str,
    status: str,
    last_action_summary: str | None,
    last_target_identity: str | None,
    last_surface_identity: str | None,
) -> RunnerKernelResult:
    return RunnerKernelResult(
        steps_completed=step_index,
        stop_reason=stop_reason,
        status=status,
        last_action_summary=last_action_summary,
        last_target_identity=last_target_identity,
        last_surface_identity=last_surface_identity,
    )


def ensure_context_prep_ready(context: RunContext) -> None:
    if context.context_prep_output is None:
        future = context.context_prep_future
        if future is not None:
            wait_started = time.monotonic()
            logger.info("context_prep_wait_start future_done=%s", future.done())
            try:
                context.context_prep_output = future.result()
                logger.info(
                    "context_prep_wait_done waited_ms=%s source=future",
                    int(round((time.monotonic() - wait_started) * 1000.0)),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("context_prep_future_failed error=%s", exc)
                logger.info(
                    "context_prep_wait_done waited_ms=%s source=future_fallback",
                    int(round((time.monotonic() - wait_started) * 1000.0)),
                )
                context.context_prep_output = prepare_runner_context(context)
        else:
            logger.info("context_prep_wait_start future_done=false source=direct")
            wait_started = time.monotonic()
            context.context_prep_output = prepare_runner_context(context)
            logger.info(
                "context_prep_wait_done waited_ms=%s source=direct",
                int(round((time.monotonic() - wait_started) * 1000.0)),
            )
    apply_context_prep = getattr(context.brain, "apply_context_prep_output", None)
    if callable(apply_context_prep) and context.context_prep_output is not None:
        apply_context_prep(
            context.context_prep_output,
            knowledge_bundle=context.prepared_knowledge_bundle,
        )
