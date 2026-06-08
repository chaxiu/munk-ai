from __future__ import annotations

from munk.agent_base.action.executor import ActionExecutionResult
from munk.agent_base.action.high_level import HighLevelActionResult, uses_high_level_execution
from munk.core import map_action_to_device

from .helpers import capture_runtime_observation
from .models import InteractiveObservation
from .session_context import InteractiveSessionContext


def execute_interactive_action(
    *,
    context: InteractiveSessionContext,
    action,
    before: InteractiveObservation,
) -> HighLevelActionResult:
    image_bgr = before.screen.image_bgr
    image_size = before.screen.screen_size
    if image_bgr is not None:
        image_size = (int(image_bgr.shape[1]), int(image_bgr.shape[0]))
    mapped_action = map_action_to_device(
        action,
        image_size=image_size,
        device_size=context.device.window_size(),
    )
    if uses_high_level_execution(mapped_action):
        return context.high_level_actions.execute(
            mapped_action,
            before.screen,
            lambda source: capture_runtime_observation(
                context=context,
                source=source,
            ),
        )
    atomic = context.executor.execute(mapped_action)
    return high_level_result_from_atomic(mapped_action, atomic)


def high_level_result_from_atomic(action, result: ActionExecutionResult) -> HighLevelActionResult:  # noqa: ANN001
    return HighLevelActionResult(
        executed=result.executed,
        timed_out=result.timed_out,
        action=action,
        normalized_action=result.normalized_action,
        duration_ms=result.duration_ms,
        error_type=result.error_type,
        error_message=result.error_message,
    )
