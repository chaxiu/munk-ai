from __future__ import annotations

import json
from typing import cast

from munk.agent_base.action import Action, ActionType
from munk.agent_base.base import ActionFeedback, ActionFeedbackValue


def build_runner_action_feedback(action: Action) -> ActionFeedback | None:
    fields: list[tuple[str, ActionFeedbackValue]] = []
    if action.type in {ActionType.SCROLL, ActionType.SWIPE}:
        if action.direction is not None:
            fields.append(("normalized_direction", action.direction))
        if action.start is not None:
            fields.append(("start", action.start))
        if action.end is not None:
            fields.append(("end", action.end))
        return ActionFeedback(action_type=action.type.value, status="executed", fields=tuple(fields))
    if action.type == ActionType.DRAG:
        if action.start is not None:
            fields.append(("start", action.start))
        if action.end is not None:
            fields.append(("end", action.end))
        return ActionFeedback(action_type=action.type.value, status="executed", fields=tuple(fields))
    if action.type in {ActionType.CLICK, ActionType.LONG_PRESS}:
        resolved_point = _resolve_point(action)
        if resolved_point is not None:
            fields.append(("resolved_point", resolved_point))
        return ActionFeedback(action_type=action.type.value, status="executed", fields=tuple(fields))
    if action.type in {ActionType.INPUT, ActionType.EDIT_TEXT}:
        if action.text is not None:
            fields.append(("text_applied", action.text))
        if action.type == ActionType.EDIT_TEXT and action.text_mode is not None:
            fields.append(("text_mode", action.text_mode))
        input_target = action.box if action.box is not None else action.point
        if action.type == ActionType.EDIT_TEXT and input_target is not None:
            fields.append(("input_target", input_target))
        return ActionFeedback(action_type=action.type.value, status="executed", fields=tuple(fields))
    if action.type == ActionType.SET_VALUE:
        if action.text is not None:
            fields.append(("value_applied", action.text))
        if action.target_ref is not None:
            fields.append(("target_ref", action.target_ref))
        if action.handle is not None and action.handle.fill_mode is not None:
            fields.append(("fill_mode", action.handle.fill_mode))
        return ActionFeedback(action_type=action.type.value, status="executed", fields=tuple(fields))
    if action.type in {ActionType.BACK, ActionType.HOME, ActionType.RESTART_APP, ActionType.WAIT}:
        return ActionFeedback(action_type=action.type.value, status="executed")
    return None


def augment_runner_action_feedback(
    action: Action,
    *,
    feedback: ActionFeedback | None,
    duration_ms: int | None = None,
    changes: tuple[str, ...] = (),
    extra_fields: tuple[tuple[str, ActionFeedbackValue], ...] = (),
) -> ActionFeedback | None:
    effective = feedback
    if effective is None and (duration_ms is not None or changes or extra_fields):
        effective = ActionFeedback(action_type=action.type.value, status="executed")
    if effective is None:
        return None
    fields = list(effective.fields)
    if duration_ms is not None:
        fields.append(("duration_ms", duration_ms))
    if changes:
        fields.append(("changes", list(changes)))
    fields.extend(extra_fields)
    return ActionFeedback(
        action_type=effective.action_type,
        status=effective.status,
        fields=tuple(fields),
    )


def _resolve_point(action: Action) -> tuple[int, int] | None:
    if action.point is not None:
        return action.point
    if action.box is None:
        return None
    left, top, right, bottom = action.box
    return (int(round((left + right) / 2.0)), int(round((top + bottom) / 2.0)))


def build_failed_runner_action_feedback(
    *,
    action_type: str,
    arguments: dict[str, object],
    error_type: str,
    error_message: str,
) -> ActionFeedback:
    fields: list[tuple[str, ActionFeedbackValue]] = []
    for key, value in arguments.items():
        if key == "action_type" or value is None:
            continue
        fields.append((key, _coerce_feedback_value(value)))
    fields.append(("error_type", error_type))
    fields.append(("error_message", error_message))
    return ActionFeedback(action_type=action_type, status="failed", fields=tuple(fields))


def format_runner_action_feedback(feedback: ActionFeedback | None) -> str:
    if feedback is None:
        return "none"
    lines = [f"status={feedback.status}", f"action={feedback.action_type}"]
    lines.extend(f"{key}={_format_feedback_value(value)}" for key, value in feedback.fields)
    return "\n".join(lines)


def _format_feedback_value(value: ActionFeedbackValue) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _coerce_feedback_value(value: object) -> ActionFeedbackValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        tuple_value = cast(tuple[object, ...], value)
        if len(tuple_value) in {2, 4} and all(isinstance(item, int) for item in tuple_value):
            return cast(tuple[int, int] | tuple[int, int, int, int], tuple_value)
    if isinstance(value, list):
        return cast(list[object], value)
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return str(value)
