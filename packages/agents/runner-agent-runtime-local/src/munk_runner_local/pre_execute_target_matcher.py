from __future__ import annotations

from dataclasses import dataclass

from munk.agent_base.action import ActionType
from munk.core.action_targets import ActionTarget, is_text_input_target, set_value_control_family

from munk_runner_local.target_handle_fingerprint import handle_fingerprint

MAX_REBIND_CENTER_DISTANCE_RATIO = 0.1


@dataclass(frozen=True)
class TargetMatchResult:
    resolved_target: ActionTarget | None
    match_strategy: str | None = None
    stale_reason: str | None = None


def match_pre_execute_target(
    *,
    original_target: ActionTarget,
    current_targets: list[ActionTarget],
    action_type: ActionType,
    screen_size: tuple[int, int],
) -> TargetMatchResult:
    if not _has_rebind_signature(original_target):
        return TargetMatchResult(resolved_target=original_target)
    compatible_targets = _dedupe_targets(
        [
            target
            for target in current_targets
            if _is_candidate_compatible(
                target,
                action_type=action_type,
                original_target=original_target,
            )
        ]
    )
    for layer_name, matches in _collect_layer_matches(original_target, compatible_targets):
        if not matches:
            continue
        if len(matches) == 1:
            return TargetMatchResult(resolved_target=matches[0], match_strategy=layer_name)
        resolved_target = _resolve_spatially_nearest_candidate(
            matches,
            original_box=original_target.box,
            screen_size=screen_size,
        )
        if resolved_target is not None:
            return TargetMatchResult(resolved_target=resolved_target, match_strategy=layer_name)
        return TargetMatchResult(
            resolved_target=None,
            stale_reason=f"target_{layer_name}_ambiguous_before_execution",
        )
    return TargetMatchResult(
        resolved_target=None,
        stale_reason="target_no_compatible_rebind_match_before_execution",
    )


def _has_rebind_signature(target: ActionTarget) -> bool:
    # Frame-local refs (vN/tN) are never a stable rebind identity.
    if handle_fingerprint(target.handle) is not None:
        return True
    return _has_text(target.stable_key) or _has_text(target.resource_id) or has_reliable_target_label(target)


def _collect_layer_matches(
    original_target: ActionTarget,
    compatible_targets: list[ActionTarget],
) -> tuple[tuple[str, list[ActionTarget]], ...]:
    layers: list[tuple[str, list[ActionTarget]]] = []
    original_fingerprint = handle_fingerprint(original_target.handle)
    if original_fingerprint is not None:
        layers.append(
            (
                "handle",
                [
                    target
                    for target in compatible_targets
                    if handle_fingerprint(target.handle) == original_fingerprint
                ],
            )
        )
    if _has_text(original_target.stable_key):
        stable_key = str(original_target.stable_key).strip()
        layers.append(
            (
                "stable_key",
                [target for target in compatible_targets if target.stable_key == stable_key],
            )
        )
    if _has_text(original_target.resource_id):
        resource_id = str(original_target.resource_id).strip()
        layers.append(
            (
                "resource_id",
                [target for target in compatible_targets if target.resource_id == resource_id],
            )
        )
    normalized_label = _normalize_label(original_target.label) if has_reliable_target_label(original_target) else None
    if normalized_label is not None:
        layers.append(
            (
                "label",
                [
                    target
                    for target in compatible_targets
                    if has_reliable_target_label(target) and _normalize_label(target.label) == normalized_label
                ],
            )
        )
    return tuple(layers)


def _resolve_spatially_nearest_candidate(
    candidates: list[ActionTarget],
    *,
    original_box: tuple[int, int, int, int],
    screen_size: tuple[int, int],
) -> ActionTarget | None:
    if len(candidates) == 1:
        return candidates[0]
    near_candidates = sorted(
        (
            candidate
            for candidate in candidates
            if _normalized_center_distance(candidate.box, original_box, screen_size=screen_size)
            <= MAX_REBIND_CENTER_DISTANCE_RATIO
        ),
        key=lambda candidate: (
            _normalized_center_distance(candidate.box, original_box, screen_size=screen_size),
            _target_preference_sort_key(candidate),
        ),
    )
    if not near_candidates:
        return None
    return near_candidates[0]


def _dedupe_targets(targets: list[ActionTarget]) -> list[ActionTarget]:
    deduped_by_box: dict[tuple[int, int, int, int], ActionTarget] = {}
    for target in sorted(targets, key=_target_preference_sort_key):
        deduped_by_box.setdefault(target.box, target)
    return list(deduped_by_box.values())


def _target_preference_sort_key(target: ActionTarget) -> tuple[int, int, int, tuple[int, int, int, int]]:
    return (
        target.part != "vision",
        target.stable_key is None,
        _box_area(target.box),
        target.box,
    )


def _is_candidate_compatible(
    target: ActionTarget,
    *,
    action_type: ActionType,
    original_target: ActionTarget | None = None,
) -> bool:
    if target.enabled is False:
        return False
    if action_type in {ActionType.CLICK, ActionType.LONG_PRESS}:
        return target.clickable is not False
    if action_type == ActionType.EDIT_TEXT:
        return is_text_input_target(target)
    if action_type == ActionType.SET_VALUE:
        if target.handle is None or target.handle.kind not in {"dom", "a11y"}:
            return False
        if original_target is None:
            return set_value_control_family(target) is not None
        original_family = set_value_control_family(original_target)
        candidate_family = set_value_control_family(target)
        if original_family is None or candidate_family is None:
            return False
        return original_family == candidate_family
    return True


def _normalize_label(value: object) -> str | None:
    if not _has_text(value):
        return None
    return " ".join(str(value).split()).lower()


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def has_reliable_target_label(target: ActionTarget) -> bool:
    if _has_text(target.text) or _has_text(target.content_desc):
        return True
    if any(_has_text(text) for text in target.ocr_texts):
        return True
    normalized_label = _normalize_label(target.label)
    if normalized_label is None:
        return False
    derived_values = (
        _normalize_label(target.resource_id),
        _normalize_label(target.semantic_role),
        _normalize_label(target.class_name),
    )
    return all(derived is None or derived != normalized_label for derived in derived_values)


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


def _box_area(box: tuple[int, int, int, int]) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])
