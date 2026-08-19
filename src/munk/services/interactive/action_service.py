from __future__ import annotations

from munk.agent_base.action import ActionType

from .action_execution import execute_interactive_action
from .helpers import capture_interactive_observation, summarize_action_execution
from .models import InteractiveActionRequest, InteractiveActionResult
from .session_service import InteractiveSessionService
from .settle import capture_interactive_settle_snapshot, settle_interactive_after_action
from .structure_handle_guard import guard_structure_handle_before_execution
from .target_resolution import resolve_action_request_from_observation

ALLOWED_ACTION_TYPES = {
    ActionType.CLICK,
    ActionType.LONG_PRESS,
    ActionType.EDIT_TEXT,
    ActionType.SET_VALUE,
    ActionType.SCROLL,
    ActionType.SWIPE,
    ActionType.PULL_TO_REFRESH,
    ActionType.WAIT,
    ActionType.BACK,
    ActionType.HOME,
}


class InteractiveActionService:
    def __init__(self, session_service: InteractiveSessionService) -> None:
        self._session_service = session_service

    def act(
        self,
        session_id: str,
        action_request: InteractiveActionRequest,
        settle_timeout_sec: float | None = None,
    ) -> InteractiveActionResult:
        action = action_request.action
        if action.type not in ALLOWED_ACTION_TYPES:
            raise ValueError(f"interactive action is not supported: {action.type.value}")
        entry = self._session_service.begin_action(session_id)
        try:
            decision_observation = entry.session.last_observation
            resolved_request = resolve_action_request_from_observation(
                action_request,
                observation=decision_observation,
            )
            action = resolved_request.action

            before = capture_interactive_observation(session_id=session_id, context=entry.context)
            action = guard_structure_handle_before_execution(
                action=action,
                decision_observation=decision_observation,
                before_observation=before,
            )
            settle_before = capture_interactive_settle_snapshot(context=entry.context)
            execution = execute_interactive_action(
                context=entry.context,
                action=action,
                before=before,
            )
            settle_status = "skipped"
            settle_timed_out = False
            settle_elapsed_ms = 0
            settle_summary: str | None = None
            if execution.executed and not execution.timed_out:
                settle_result = settle_interactive_after_action(
                    context=entry.context,
                    before=settle_before,
                    settle_timeout_sec=settle_timeout_sec,
                )
                settle_status = settle_result.status
                settle_timed_out = settle_result.timed_out
                settle_elapsed_ms = settle_result.elapsed_ms
                settle_summary = settle_result.summary
            after = capture_interactive_observation(session_id=session_id, context=entry.context)
            effect_summary = summarize_action_execution(
                execution=execution,
                before=before,
                after=after,
            )
            result = InteractiveActionResult(
                session_id=session_id,
                action=action_request.action,
                normalized_action=execution.normalized_action,
                before=before,
                after=after,
                executed=execution.executed,
                timed_out=execution.timed_out,
                duration_ms=execution.duration_ms,
                effect_summary=effect_summary,
                error_type=execution.error_type,
                error_message=execution.error_message,
                settle_status=settle_status,
                settle_timed_out=settle_timed_out,
                settle_elapsed_ms=settle_elapsed_ms,
                settle_summary=settle_summary,
            )
            return self._session_service.record_action_step(session_id, result)
        except Exception:
            self._session_service.fail_action(session_id)
            raise
