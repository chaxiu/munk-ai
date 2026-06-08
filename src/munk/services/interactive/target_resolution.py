from __future__ import annotations

from dataclasses import replace

from munk.agent_base.action import Action, ActionType

from .models import InteractiveActionRequest, InteractiveObservation, InteractiveTargetSummary

TARGET_REQUIRED_ACTION_TYPES = {
    ActionType.CLICK,
    ActionType.LONG_PRESS,
    ActionType.CLEAR_AND_INPUT,
}
TARGET_OPTIONAL_ACTION_TYPES = {
    ActionType.INPUT,
}


def resolve_action_request_from_observation(
    action_request: InteractiveActionRequest,
    *,
    observation: InteractiveObservation | None,
) -> InteractiveActionRequest:
    action = action_request.action
    if not _needs_target_resolution(action_request):
        return action_request

    if observation is None:
        raise ValueError("interactive action target resolution requires a prior session_observe")

    target = _resolve_target(action_request, observation.targets)
    resolved_action = _resolve_action(action, target)
    return replace(action_request, action=resolved_action)


def _needs_target_resolution(action_request: InteractiveActionRequest) -> bool:
    return any(
        value is not None
        for value in (
            action_request.target_id,
            action_request.resource_id,
            action_request.label,
        )
    )


def _resolve_target(
    action_request: InteractiveActionRequest,
    targets: list[InteractiveTargetSummary],
) -> InteractiveTargetSummary:
    if action_request.target_id is not None:
        for target in targets:
            if target.target_id == action_request.target_id:
                return target
        raise ValueError(f"interactive target not found: target_id={action_request.target_id}")

    if action_request.resource_id:
        for target in targets:
            if target.resource_id == action_request.resource_id:
                return target
        raise ValueError(f"interactive target not found: resource_id={action_request.resource_id}")

    if action_request.label:
        matches = [target for target in targets if target.label == action_request.label]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"interactive target label is ambiguous: label={action_request.label}")
        raise ValueError(f"interactive target not found: label={action_request.label}")

    raise ValueError("interactive action requires target_id, resource_id, label, box, or point")


def _resolve_action(action: Action, target: InteractiveTargetSummary) -> Action:
    if action.type == ActionType.CLICK:
        return replace(action, box=target.box)
    if action.type == ActionType.LONG_PRESS:
        return replace(action, box=target.box)
    if action.type == ActionType.CLEAR_AND_INPUT:
        return replace(action, box=target.box)
    if action.type == ActionType.INPUT:
        # When an explicit target is provided, prefer targeting and resetting that field.
        return Action.clear_and_input(
            box=target.box,
            text=action.text or "",
            dismiss_keyboard=bool(action.dismiss_keyboard) if action.dismiss_keyboard is not None else True,
            summary=action.summary,
        )
    if action.type in TARGET_REQUIRED_ACTION_TYPES | TARGET_OPTIONAL_ACTION_TYPES:
        raise ValueError(f"interactive action target resolution is not supported: {action.type.value}")
    return action
