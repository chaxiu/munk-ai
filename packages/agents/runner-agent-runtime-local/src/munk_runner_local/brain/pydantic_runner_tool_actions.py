from __future__ import annotations

from munk.agent_base.action import Action

from munk_runner_local.brain.pydantic_runner_models import RunnerStepDeps
from munk_runner_local.brain.pydantic_runner_output_models import (
    ClickActionSubmission,
    DragActionSubmission,
    EditTextActionSubmission,
    LongPressActionSubmission,
    PullToRefreshActionSubmission,
    RevealMoreActionSubmission,
    RunnerActionOutput,
    ScrollUntilTextActionSubmission,
    SimpleActionSubmission,
    SwipeActionSubmission,
    WaitActionSubmission,
    WaitForTextActionSubmission,
)
from munk_runner_local.brain.pydantic_runner_tool_runtime import record_materialized_action
from munk_runner_local.brain.pydantic_runner_tool_support import (
    resolve_reveal_more_gesture,
    resolve_swipe_gesture,
    resolve_target,
    target_arguments,
    text_match_arguments,
)


def materialize_runner_action(
    deps: RunnerStepDeps,
    submission: RunnerActionOutput,
) -> Action:
    if isinstance(submission, ClickActionSubmission):
        target = resolve_target(deps, submission.target_id)
        action = Action.click(target.box, summary=submission.summary)
        arguments = target_arguments(
            {
                "target_id": submission.target_id,
                "summary": submission.summary,
            },
            target,
        )
        return record_materialized_action(deps, "click", arguments, action)

    if isinstance(submission, LongPressActionSubmission):
        target = resolve_target(deps, submission.target_id)
        action = Action.long_press(
            target.box,
            duration=submission.duration_sec,
            summary=submission.summary,
        )
        arguments = target_arguments(
            {
                "target_id": submission.target_id,
                "summary": submission.summary,
                "duration_sec": submission.duration_sec,
            },
            target,
        )
        return record_materialized_action(deps, "long_press", arguments, action)

    if isinstance(submission, EditTextActionSubmission):
        dismiss_keyboard = submission.dismiss_keyboard
        if dismiss_keyboard is None:
            raise ValueError("edit_text submission is missing dismiss_keyboard")
        target = resolve_target(deps, submission.target_id) if submission.target_id is not None else None
        action = Action.edit_text(
            text=submission.text,
            mode=submission.mode,
            target_box=target.box if target is not None else None,
            dismiss_keyboard=dismiss_keyboard,
            summary=submission.summary,
        )
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        if target is not None:
            arguments = target_arguments(arguments, target)
        return record_materialized_action(deps, "edit_text", arguments, action)

    if isinstance(submission, RevealMoreActionSubmission):
        gesture = resolve_reveal_more_gesture(
            deps,
            anchor_target_id=submission.anchor_target_id,
            direction=submission.direction,
            distance=submission.distance,
            start_y_ratio=submission.start_y_ratio,
        )
        action = Action.scroll(
            direction=submission.direction,
            start_x_ratio=gesture.start_x_ratio,
            start_y_ratio=gesture.start_y_ratio,
            distance_ratio=gesture.distance_ratio,
            summary=submission.summary,
        )
        arguments: dict[str, object] = {
            "direction": submission.direction,
            "distance": submission.distance,
            "start_y_ratio": submission.start_y_ratio,
            "resolved_start_x_ratio": round(gesture.start_x_ratio, 4),
            "resolved_start_y_ratio": round(gesture.start_y_ratio, 4),
            "resolved_distance_ratio": round(gesture.distance_ratio, 4),
            "summary": submission.summary,
        }
        if submission.anchor_target_id is not None:
            arguments["anchor_target_id"] = submission.anchor_target_id
            arguments = target_arguments(arguments, gesture.anchor_target)
        return record_materialized_action(deps, "reveal_more", arguments, action)

    if isinstance(submission, SwipeActionSubmission):
        gesture = resolve_swipe_gesture(
            deps,
            direction=submission.direction,
            distance=submission.distance,
            start_x_ratio=submission.start_x_ratio,
        )
        action = Action.swipe(
            direction=submission.direction,
            start_x_ratio=gesture.start_x_ratio,
            start_y_ratio=gesture.start_y_ratio,
            distance_ratio=gesture.distance_ratio,
            summary=submission.summary,
        )
        arguments = {
            "direction": submission.direction,
            "distance": submission.distance,
            "start_x_ratio": submission.start_x_ratio,
            "resolved_start_x_ratio": round(gesture.start_x_ratio, 4),
            "resolved_start_y_ratio": round(gesture.start_y_ratio, 4),
            "resolved_distance_ratio": round(gesture.distance_ratio, 4),
            "summary": submission.summary,
        }
        return record_materialized_action(deps, "swipe", arguments, action)

    if isinstance(submission, DragActionSubmission):
        action = Action.drag(
            start=(submission.start_x, submission.start_y),
            end=(submission.end_x, submission.end_y),
            duration=submission.duration_sec,
            summary=submission.summary,
        )
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        return record_materialized_action(deps, "drag", arguments, action)

    if isinstance(submission, PullToRefreshActionSubmission):
        action = Action.pull_to_refresh(
            start_x_ratio=submission.start_x_ratio,
            start_y_ratio=submission.start_y_ratio,
            distance_ratio=submission.distance_ratio,
            summary=submission.summary,
        )
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        return record_materialized_action(deps, "pull_to_refresh", arguments, action)

    if isinstance(submission, SimpleActionSubmission):
        return _materialize_simple_action(deps, submission)

    if isinstance(submission, WaitForTextActionSubmission):
        match = submission.to_text_match_args()
        arguments = text_match_arguments(
            match,
            timeout_sec=submission.timeout_sec,
            summary=submission.summary,
        )
        action = Action.wait_for_text(
            match_type=match.match_type,
            texts=match.texts,
            timeout_sec=submission.timeout_sec,
            summary=submission.summary,
        )
        return record_materialized_action(deps, "wait_for_text", arguments, action)

    if isinstance(submission, ScrollUntilTextActionSubmission):
        match = submission.to_text_match_args()
        action = Action.scroll_until_text(
            match_type=match.match_type,
            texts=match.texts,
            direction=submission.direction,
            max_attempts=submission.max_attempts,
            summary=submission.summary,
        )
        arguments = text_match_arguments(
            match,
            direction=submission.direction,
            max_attempts=submission.max_attempts,
            summary=submission.summary,
        )
        return record_materialized_action(deps, "scroll_until_text", arguments, action)

    if isinstance(submission, WaitActionSubmission):
        action = Action.wait(submission.duration, summary=submission.summary)
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        return record_materialized_action(deps, "wait", arguments, action)

    raise ValueError(f"unsupported runner action output: {type(submission).__name__}")


def _materialize_simple_action(deps: RunnerStepDeps, submission: SimpleActionSubmission) -> Action:
    arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
    action_type = submission.action_type
    if action_type == "dismiss_soft_keyboard":
        action = Action.dismiss_soft_keyboard(summary=submission.summary)
        return record_materialized_action(deps, "dismiss_soft_keyboard", arguments, action)
    if action_type == "back":
        action = Action.back(summary=submission.summary)
        return record_materialized_action(deps, "back", arguments, action)
    if action_type == "home":
        action = Action.home(summary=submission.summary)
        return record_materialized_action(deps, "home", arguments, action)
    if action_type == "restart_app":
        action = Action.restart_app(summary=submission.summary)
        return record_materialized_action(deps, "restart_app", arguments, action)
    if action_type == "redetect":
        action = Action.redetect(summary=submission.summary)
        return record_materialized_action(deps, "redetect", arguments, action)
    if action_type == "stop":
        action = Action.stop(summary=submission.summary)
        return record_materialized_action(deps, "stop", arguments, action)
    raise ValueError(f"unsupported simple runner action output: {action_type}")
