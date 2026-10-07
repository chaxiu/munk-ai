from __future__ import annotations

from collections.abc import Callable

from munk.services.events import RunEventSink
from munk.services.models import RunnerKernelResult

from .context import RunContext
from .loop_engine import execute_run_loop as _execute_run_loop
from .loop_observation import (
    capture_screen_state,
    capture_settle_snapshot,
    settle_after_action,
    wait_until_initial_screen_ready,
)
from .loop_support import publish_step_started, publish_stop


def execute_run_loop(
    context: RunContext,
    event_sink: RunEventSink | None,
    should_stop: Callable[[], bool],
) -> RunnerKernelResult:
    return _execute_run_loop(
        context=context,
        event_sink=event_sink,
        should_stop=should_stop,
        wait_until_initial_screen_ready=wait_until_initial_screen_ready,
        capture_screen_state=capture_screen_state,
        capture_settle_snapshot=capture_settle_snapshot,
        settle_after_action=settle_after_action,
        publish_step_started=publish_step_started,
        publish_stop=publish_stop,
    )
