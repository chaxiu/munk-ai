from __future__ import annotations

from dataclasses import replace

from munk.agent_base.action import Action, ActionType
from munk.agent_base.action.structure_handle import is_structure_element_handle
from munk.core.action_target_fingerprint import handle_fingerprint
from munk.core.action_target_models import TargetHandle
from munk.core.action_target_refs import normalize_target_ref

from .models import InteractiveObservation, InteractiveTargetSummary
from .target_catalog import interactive_targets_for_resolution

_GUARDED_ACTION_TYPES = frozenset(
    {
        ActionType.CLICK,
        ActionType.LONG_PRESS,
        ActionType.EDIT_TEXT,
        ActionType.SET_VALUE,
    }
)

_REOBSERVE_HINT = "re-run session_observe before acting again"
# Align with Runner pre_execute_target_matcher spatial rebind threshold.
MAX_REBIND_CENTER_DISTANCE_RATIO = 0.1


def guard_structure_handle_before_execution(
    *,
    action: Action,
    decision_observation: InteractiveObservation | None,
    before_observation: InteractiveObservation,
) -> Action:
    """Validate/rebind structure handles against the fresh before frame.

    Thin Runner subset: fingerprint match, with decision-box spatial disambiguation
    when multiple candidates share a fingerprint. No visual/IoU fallback.
    """
    if action.type not in _GUARDED_ACTION_TYPES:
        return action
    if not is_structure_element_handle(action.handle):
        return action
    fingerprint = handle_fingerprint(action.handle)
    if fingerprint is None:
        return action
    if decision_observation is None:
        raise ValueError(
            "stale structure handle: interactive action requires a prior session_observe; "
            f"{_REOBSERVE_HINT}"
        )
    _reject_identity_drift(
        decision_observation=decision_observation,
        before_observation=before_observation,
        fingerprint=fingerprint,
    )
    matches = [
        target
        for target in interactive_targets_for_resolution(before_observation)
        if handle_fingerprint(target.handle) == fingerprint
    ]
    if len(matches) == 0:
        raise ValueError(
            "stale structure handle: fingerprint "
            f"{_format_fingerprint(fingerprint)} not found on the current screen; "
            f"{_REOBSERVE_HINT}"
        )
    if len(matches) == 1:
        return _rebind_action_to_target(action, matches[0])

    anchor_box = _decision_anchor_box(action, decision_observation)
    if anchor_box is None:
        raise ValueError(
            "stale structure handle: fingerprint "
            f"{_format_fingerprint(fingerprint)} matched {len(matches)} targets "
            f"and no decision box is available to disambiguate; {_REOBSERVE_HINT}"
        )
    nearest = _resolve_spatially_nearest_candidate(
        matches,
        original_box=anchor_box,
        screen_size=before_observation.screen.screen_size,
    )
    if nearest is None:
        raise ValueError(
            "stale structure handle: fingerprint "
            f"{_format_fingerprint(fingerprint)} matched {len(matches)} targets "
            f"with no nearby candidate; {_REOBSERVE_HINT}"
        )
    return _rebind_action_to_target(action, nearest)


def _decision_anchor_box(
    action: Action,
    decision_observation: InteractiveObservation,
) -> tuple[int, int, int, int] | None:
    if action.target_ref is not None:
        try:
            normalized_ref = normalize_target_ref(action.target_ref)
        except ValueError:
            normalized_ref = None
        if normalized_ref is not None:
            for target in interactive_targets_for_resolution(decision_observation):
                if target.target_ref == normalized_ref:
                    return target.box
    if action.box is not None:
        return action.box
    return None


def _resolve_spatially_nearest_candidate(
    candidates: list[InteractiveTargetSummary],
    *,
    original_box: tuple[int, int, int, int],
    screen_size: tuple[int, int],
) -> InteractiveTargetSummary | None:
    if len(candidates) == 1:
        return candidates[0]
    near_candidates = sorted(
        (
            candidate
            for candidate in candidates
            if _normalized_center_distance(candidate.box, original_box, screen_size=screen_size)
            <= MAX_REBIND_CENTER_DISTANCE_RATIO
        ),
        key=lambda candidate: _normalized_center_distance(
            candidate.box,
            original_box,
            screen_size=screen_size,
        ),
    )
    if not near_candidates:
        return None
    return near_candidates[0]


def _normalized_center_distance(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
    *,
    screen_size: tuple[int, int],
) -> float:
    first_center = ((first[0] + first[2]) / 2.0, (first[1] + first[3]) / 2.0)
    second_center = ((second[0] + second[2]) / 2.0, (second[1] + second[3]) / 2.0)
    width, height = screen_size
    diagonal = max((width**2 + height**2) ** 0.5, 1.0)
    distance = ((first_center[0] - second_center[0]) ** 2 + (first_center[1] - second_center[1]) ** 2) ** 0.5
    return distance / diagonal


def _reject_identity_drift(
    *,
    decision_observation: InteractiveObservation,
    before_observation: InteractiveObservation,
    fingerprint: tuple[str, ...],
) -> None:
    decision_screen = decision_observation.screen
    before_screen = before_observation.screen
    if decision_screen.entry_identity != before_screen.entry_identity:
        raise ValueError(
            "stale structure handle: entry_identity changed before execution "
            f"(fingerprint={_format_fingerprint(fingerprint)}); {_REOBSERVE_HINT}"
        )
    if decision_screen.surface_identity != before_screen.surface_identity:
        raise ValueError(
            "stale structure handle: surface_identity changed before execution "
            f"(fingerprint={_format_fingerprint(fingerprint)}); {_REOBSERVE_HINT}"
        )


def _rebind_action_to_target(action: Action, target: InteractiveTargetSummary) -> Action:
    handle = target.handle
    box = target.box
    if action.type == ActionType.CLICK:
        return Action.click(
            box,
            summary=action.summary,
            handle=handle,
            target_ref=action.target_ref or target.target_ref,
        )
    if action.type == ActionType.LONG_PRESS:
        return Action.long_press(
            box,
            duration=action.duration,
            summary=action.summary,
            handle=handle,
            target_ref=action.target_ref or target.target_ref,
        )
    if action.type == ActionType.EDIT_TEXT:
        return Action.edit_text(
            text=action.text or "",
            mode=action.text_mode or "append",
            target_box=box,
            dismiss_keyboard=action.dismiss_keyboard,
            summary=action.summary,
            handle=handle,
            target_ref=action.target_ref or target.target_ref,
        )
    if action.type == ActionType.SET_VALUE:
        if not isinstance(handle, TargetHandle):
            raise ValueError(
                "stale structure handle: matched target is missing a structure handle; "
                f"{_REOBSERVE_HINT}"
            )
        updated_handle = handle if handle.box == box else replace(handle, box=box)
        return Action.set_value(
            value=action.text or "",
            handle=updated_handle,
            target_ref=action.target_ref or target.target_ref,
            summary=action.summary,
        )
    return action


def _format_fingerprint(fingerprint: tuple[str, ...]) -> str:
    return ":".join(fingerprint)
