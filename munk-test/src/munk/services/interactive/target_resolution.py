from __future__ import annotations

from dataclasses import replace

from munk.agent_base.action import Action, ActionType
from munk.agent_base.action.structure_handle import is_structure_element_handle
from munk.core.action_target_models import ActionTarget
from munk.core.action_target_refs import (
    is_text_input_target,
    normalize_target_ref,
    requires_set_value_action,
)

from .models import InteractiveActionRequest, InteractiveObservation, InteractiveTargetSummary
from .target_catalog import interactive_targets_for_resolution

TARGET_REQUIRED_ACTION_TYPES = {
    ActionType.CLICK,
    ActionType.LONG_PRESS,
    ActionType.SET_VALUE,
}
TARGET_OPTIONAL_ACTION_TYPES = {
    ActionType.EDIT_TEXT,
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

    target = _resolve_target(action_request, interactive_targets_for_resolution(observation))
    resolved_action = _resolve_action(action, target)
    return replace(action_request, action=resolved_action)


def _needs_target_resolution(action_request: InteractiveActionRequest) -> bool:
    return any(
        value is not None
        for value in (
            action_request.target_ref,
            action_request.resource_id,
            action_request.label,
        )
    )


def _resolve_target(
    action_request: InteractiveActionRequest,
    targets: list[InteractiveTargetSummary],
) -> InteractiveTargetSummary:  # noqa: C901
    if action_request.target_ref is not None:
        try:
            normalized_ref = normalize_target_ref(action_request.target_ref)
        except ValueError as err:
            raise ValueError(f"interactive target_ref is invalid: {action_request.target_ref!r}") from err
        for target in targets:
            if target.target_ref == normalized_ref:
                return target
        raise ValueError(f"interactive target not found: target_ref={normalized_ref}")

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

    raise ValueError("interactive action requires target_ref, resource_id, label, box, or point")


def _resolve_action(action: Action, target: InteractiveTargetSummary) -> Action:
    handle = target.handle
    if action.type == ActionType.CLICK:
        return replace(action, box=target.box, handle=handle)
    if action.type == ActionType.LONG_PRESS:
        return replace(action, box=target.box, handle=handle)
    if action.type == ActionType.SET_VALUE:
        if target.channel != "t":
            raise ValueError("set_value requires a tree target_ref (tN)")
        if not is_structure_element_handle(handle):
            raise ValueError("set_value requires a structure (#t*) target with dom/a11y handle")
        assert handle is not None
        return Action.set_value(
            value=action.text or "",
            handle=handle if handle.box == target.box else replace(handle, box=target.box),
            target_ref=target.target_ref,
            summary=action.summary,
        )
    if action.type == ActionType.EDIT_TEXT:
        _reject_edit_text_for_target(target)
        return replace(action, box=target.box, handle=handle)
    if action.type in TARGET_REQUIRED_ACTION_TYPES | TARGET_OPTIONAL_ACTION_TYPES:
        raise ValueError(f"interactive action target resolution is not supported: {action.type.value}")
    return action


def _action_target_from_summary(target: InteractiveTargetSummary) -> ActionTarget:
    handle = target.handle
    return ActionTarget(
        target_id=target.index,
        ref=target.target_ref,
        channel="t" if target.channel == "t" else "v",
        index=target.index,
        part="tree" if target.channel == "t" else "vision",
        source=target.source,
        box=target.box,
        kind=target.kind,
        resource_id=target.resource_id,
        text=target.text,
        class_name=(handle.class_name or handle.tag) if handle is not None else None,
        input_type=handle.input_type if handle is not None else None,
        semantic_role=target.kind,
        handle=handle,
    )


def _reject_edit_text_for_target(target: InteractiveTargetSummary) -> None:
    action_target = _action_target_from_summary(target)
    if is_structure_element_handle(target.handle):
        if requires_set_value_action(action_target):
            raise ValueError(
                "edit_text cannot target structured controls "
                "(date/select/checkbox/switch/radio); use set_value with #t*"
            )
        if not is_text_input_target(action_target):
            raise ValueError(
                "edit_text requires a real text input target; "
                "use set_value for structured controls or pick a text field"
            )
        return
    if requires_set_value_action(action_target):
        raise ValueError(
            "native form controls (date/select/checkbox/radio) require set_value with #t*"
        )
