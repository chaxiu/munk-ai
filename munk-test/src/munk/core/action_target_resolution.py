from __future__ import annotations

from typing import Any, cast

from munk.agent_base.base import ScreenState
from munk.core.action_target_building import build_action_targets, build_canonical_target_parts
from munk.core.action_target_geometry import (
    box_area,
    distance_sq_to_box_center,
    point_in_box,
    spatial_sort_key,
)
from munk.core.action_target_models import ActionTarget, ActionTargetResolution
from munk.core.action_target_refs import normalize_target_ref, parse_target_ref
from munk.core.action_target_utils import first_int, normalized_text


def resolve_action_target(
    screen: ScreenState,
    *,
    target_ref: str,
    max_elements: int,
) -> ActionTarget:
    _ = max_elements
    canonical_parts = build_canonical_target_parts(screen)
    return _resolve_by_ref(canonical_parts.vision_targets, canonical_parts.tree_targets, target_ref)


def _resolve_by_ref(
    vision_targets: list[ActionTarget],
    tree_targets: list[ActionTarget],
    target_ref: str,
) -> ActionTarget:
    channel, index = parse_target_ref(target_ref)
    channel_targets = vision_targets if channel == "v" else tree_targets
    for target in channel_targets:
        if target.index == index and target.channel == channel:
            return target
    # Fallback: refs may be missing on transitional fixtures; match by constructed ref.
    normalized = normalize_target_ref(target_ref)
    for target in channel_targets:
        if target.ref == normalized:
            return target
    if 1 <= index <= len(channel_targets):
        return channel_targets[index - 1]
    raise ValueError(f"target_ref out of range: {target_ref}")


def find_action_target_by_box(
    screen: ScreenState,
    *,
    box: tuple[int, int, int, int],
    max_elements: int,
) -> ActionTarget | None:
    matches = [target for target in build_action_targets(screen, max_elements=max_elements) if target.box == box]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda target: (
            target.stable_key is None,
            target.part != "vision",
            box_area(target.box),
            spatial_sort_key(target),
        ),
    )[0]


def find_action_targets_by_stable_key(
    screen: ScreenState,
    *,
    stable_key: str,
    max_elements: int,
) -> list[ActionTarget]:
    if not stable_key.strip():
        return []
    matches = [
        target
        for target in build_action_targets(screen, max_elements=max_elements)
        if target.stable_key == stable_key
    ]
    deduped_by_box: dict[tuple[int, int, int, int], ActionTarget] = {}
    for target in sorted(
        matches,
        key=lambda item: (
            item.part != "vision",
            box_area(item.box),
            spatial_sort_key(item),
        ),
    ):
        deduped_by_box.setdefault(target.box, target)
    return list(deduped_by_box.values())


def rank_targets_by_point(targets: list[ActionTarget], x: int, y: int) -> list[ActionTarget]:
    inside = [target for target in targets if point_in_box((x, y), target.box)]
    outside = [target for target in targets if target not in inside]
    inside_sorted = sorted(
        inside,
        key=lambda target: (
            distance_sq_to_box_center((x, y), target.box),
            box_area(target.box),
            spatial_sort_key(target),
        ),
    )
    outside_sorted = sorted(
        outside,
        key=lambda target: (
            distance_sq_to_box_center((x, y), target.box),
            box_area(target.box),
            spatial_sort_key(target),
        ),
    )
    return [*inside_sorted, *outside_sorted]


def find_focused_or_input_target(targets: list[ActionTarget]) -> ActionTarget | None:
    focused = [target for target in targets if target.focused]
    if focused:
        return sorted(focused, key=_input_target_sort_key)[0]
    inputs = [target for target in targets if _looks_like_input_target(target)]
    if inputs:
        return sorted(inputs, key=_input_target_sort_key)[0]
    return None


def resolve_recording_action_targets(
    *,
    action_kind: str,
    targets: list[ActionTarget],
    recording_event: dict[str, Any] | None,
    forwarding_event: dict[str, Any] | None,
    max_candidates: int = 3,
) -> ActionTargetResolution:
    candidates: list[ActionTarget] = []
    warnings: list[str] = []
    confidence: float | None = None
    if action_kind == "input":
        focused = find_focused_or_input_target(targets)
        if focused is None:
            warnings.append("no focused or input-like target was found before the input event")
        else:
            candidates = [focused, *[target for target in targets if target is not focused][: max_candidates - 1]]
            confidence = 0.98 if focused.focused else 0.8
    elif action_kind in {"click", "swipe"}:
        point = _event_point_for_action(
            action_kind=action_kind,
            recording_event=recording_event,
            forwarding_event=forwarding_event,
        )
        if point is None:
            warnings.append(f"{action_kind} event did not include usable coordinates")
        else:
            ranked = rank_targets_by_point(targets, point[0], point[1])
            if action_kind == "swipe":
                ranked = _prioritize_swipe_targets(ranked)
            candidates = ranked[:max_candidates]
            if candidates:
                confidence = 0.96 if point_in_box(point, candidates[0].box) else 0.62
    else:
        warnings.append(f"no target resolution strategy for action kind '{action_kind}'")
    resolved_target = candidates[0] if candidates else None
    if resolved_target is None:
        warnings.append("resolved_target is unavailable")
    return ActionTargetResolution(
        resolved_target=resolved_target,
        candidates=candidates,
        confidence=confidence,
        warnings=warnings,
    )


def build_recording_action_summary(
    *,
    action_kind: str,
    recording_event: dict[str, Any] | None,
    forwarding_event: dict[str, Any] | None,
) -> str:
    payload = cast(dict[str, Any], recording_event.get("payload") or {}) if isinstance(recording_event, dict) else {}
    forwarding_payload = (
        cast(dict[str, Any], forwarding_event.get("payload") or {}) if isinstance(forwarding_event, dict) else {}
    )
    if action_kind == "click":
        point = _event_point_for_action(
            action_kind=action_kind,
            recording_event=recording_event,
            forwarding_event=forwarding_event,
        )
        if point is None:
            return "click"
        width = forwarding_payload.get("width") or payload.get("width")
        height = forwarding_payload.get("height") or payload.get("height")
        return f"click at ({point[0]}, {point[1]}) on {width or 'unknown'}x{height or 'unknown'} screen"
    if action_kind == "swipe":
        start = _event_point_for_action(
            action_kind=action_kind,
            recording_event=recording_event,
            forwarding_event=forwarding_event,
        )
        end_x = first_int({**forwarding_payload, **payload}, ("end_x",))
        end_y = first_int({**forwarding_payload, **payload}, ("end_y",))
        duration_ms = forwarding_payload.get("duration_ms") or payload.get("duration_ms")
        if start is None or end_x is None or end_y is None:
            return "swipe"
        return f"swipe from ({start[0]}, {start[1]}) to ({end_x}, {end_y}) duration_ms={duration_ms or 'unknown'}"
    if action_kind == "input":
        text = payload.get("text")
        submit = payload.get("submit")
        return f"input text={text!r} submit={bool(submit)}"
    return action_kind


def summarize_action_target(target: ActionTarget | None) -> dict[str, object] | None:
    if target is None:
        return None
    state = {
        key: value
        for key, value in (
            ("enabled", target.enabled),
            ("checked", target.checked),
            ("selected", target.selected),
            ("clickable", target.clickable),
            ("focused", target.focused),
        )
        if value is not None
    }
    return {
        "target_id": target.target_id,
        "ref": target.ref,
        "channel": target.channel,
        "index": target.index,
        "part": target.part,
        "source": target.source,
        "label": target.label,
        "kind": target.kind,
        "text": target.text,
        "resource_id": target.resource_id,
        "content_desc": target.content_desc,
        "class_name": target.class_name,
        "semantic_role": target.semantic_role,
        "linked_tree_node_id": target.linked_tree_node_id,
        "stable_key": target.stable_key,
        "bounds": list(target.box),
        "state": state,
        "ocr_texts": list(target.ocr_texts),
        "reason": target.reason,
        "platform": target.platform,
        "input_type": target.input_type,
        "dom_name": target.dom_name,
        "dom_value": target.dom_value,
        "test_id": target.test_id,
    }


def degrade_target_confidence(confidence: float | None, *, index: int) -> float | None:
    if confidence is None:
        return None
    return round(max(0.1, confidence - ((index - 1) * 0.18)), 2)


def _event_point_for_action(
    *,
    action_kind: str,
    recording_event: dict[str, Any] | None,
    forwarding_event: dict[str, Any] | None,
) -> tuple[int, int] | None:
    payloads = [
        cast(dict[str, Any], forwarding_event.get("payload") or {}) if isinstance(forwarding_event, dict) else {},
        cast(dict[str, Any], recording_event.get("payload") or {}) if isinstance(recording_event, dict) else {},
    ]
    x_keys = ("x", "start_x") if action_kind == "swipe" else ("x",)
    y_keys = ("y", "start_y") if action_kind == "swipe" else ("y",)
    for payload in payloads:
        x = first_int(payload, x_keys)
        y = first_int(payload, y_keys)
        if x is not None and y is not None:
            return (x, y)
    return None


def _prioritize_swipe_targets(targets: list[ActionTarget]) -> list[ActionTarget]:
    return sorted(targets, key=_swipe_target_sort_key)


def _swipe_target_sort_key(target: ActionTarget) -> tuple[int, tuple[int, int, int, int, int]]:
    if _looks_scrollable(target):
        bucket = 0
    elif target.clickable:
        bucket = 1
    else:
        bucket = 2
    return (bucket, spatial_sort_key(target))


def _looks_scrollable(target: ActionTarget) -> bool:
    class_name = str(target.class_name or "").lower()
    kind = str(target.kind or "").lower()
    role = str(target.semantic_role or "").lower()
    return any(token in class_name for token in ("scroll", "recycler", "listview", "viewpager")) or kind in {
        "container",
        "scroll",
    } or role in {"container", "list", "scroll"}


def _looks_like_input_target(target: ActionTarget) -> bool:
    normalized_kind = normalized_text(target.kind)
    normalized_role = normalized_text(target.semantic_role)
    normalized_class = normalized_text(target.class_name)
    if normalized_kind == "input" or normalized_role == "input":
        return True
    return "edittext" in normalized_class or "textfield" in normalized_class or "input" in normalized_class


def _input_target_sort_key(target: ActionTarget) -> tuple[int, int, int, int, int, int, int]:
    return (
        0 if target.focused else 1,
        0 if _looks_like_input_target(target) else 1,
        *spatial_sort_key(target),
    )
