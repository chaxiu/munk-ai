from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, cast

from munk.agent_base.base import ScreenState
from munk.agent_base.platform_profile import get_runner_profile
from munk.core.compact_tree import build_compact_tree, compact_node_label, index_compact_tree_nodes

VISION_PART_MAX = 40
TREE_PART_MAX = 40


@dataclass(frozen=True)
class ActionTarget:
    target_id: int
    part: str
    source: str
    box: tuple[int, int, int, int]
    kind: str | None = None
    text: str | None = None
    resource_id: str | None = None
    content_desc: str | None = None
    class_name: str | None = None
    semantic_role: str | None = None
    enabled: bool | None = None
    checked: bool | None = None
    selected: bool | None = None
    clickable: bool | None = None
    focused: bool | None = None
    linked_tree_node_id: str | None = None
    stable_key: str | None = None
    label: str | None = None
    reason: str | None = None
    ocr_texts: tuple[str, ...] = ()
    platform: str | None = None


@dataclass(frozen=True)
class TargetParts:
    vision_targets: list[ActionTarget]
    tree_targets: list[ActionTarget]
    vision_total: int
    tree_total: int


@dataclass(frozen=True)
class ActionTargetResolution:
    resolved_target: ActionTarget | None
    candidates: list[ActionTarget]
    confidence: float | None
    warnings: list[str]


def build_action_targets(screen: ScreenState, *, max_elements: int) -> list[ActionTarget]:
    parts = build_target_parts(
        screen,
        vision_limit=max(max_elements, 0),
        tree_limit=max(max_elements, 0),
    )
    return [*parts.vision_targets, *parts.tree_targets]


def build_target_parts(screen: ScreenState, *, vision_limit: int, tree_limit: int) -> TargetParts:
    compact_tree = build_compact_tree(
        screen.screen_frame.tree_nodes if screen.screen_frame is not None else [],
        platform=screen.platform,
    )
    compact_nodes_by_id = index_compact_tree_nodes(compact_tree)
    vision_targets_all = _build_vision_targets(
        screen=screen,
        compact_nodes_by_id=compact_nodes_by_id,
        limit=max(vision_limit, 0),
    )
    tree_targets_all = _build_tree_targets(screen=screen, compact_tree=compact_tree, limit=max(tree_limit, 0))
    numbered_vision_targets = [
        replace(target, target_id=index)
        for index, target in enumerate(vision_targets_all, start=1)
    ]
    tree_start_id = len(numbered_vision_targets) + 1
    numbered_tree_targets = [
        replace(target, target_id=tree_start_id + index)
        for index, target in enumerate(tree_targets_all)
    ]
    return TargetParts(
        vision_targets=numbered_vision_targets,
        tree_targets=numbered_tree_targets,
        vision_total=len(screen.elements),
        tree_total=_compact_tree_node_count(compact_tree, uncapped=True),
    )


def resolve_action_target(screen: ScreenState, *, target_id: int, max_elements: int) -> ActionTarget:
    targets = build_action_targets(screen, max_elements=max_elements)
    index = target_id - 1 if target_id > 0 else target_id
    if not 0 <= index < len(targets):
        raise ValueError(f"target_id out of range: {target_id}")
    return targets[index]


def rank_targets_by_point(targets: list[ActionTarget], x: int, y: int) -> list[ActionTarget]:
    inside = [target for target in targets if _point_in_box((x, y), target.box)]
    outside = [target for target in targets if target not in inside]
    inside_sorted = sorted(
        inside,
        key=lambda target: (
            _distance_sq_to_box_center((x, y), target.box),
            _box_area(target.box),
            _spatial_sort_key(target),
        ),
    )
    outside_sorted = sorted(
        outside,
        key=lambda target: (
            _distance_sq_to_box_center((x, y), target.box),
            _box_area(target.box),
            _spatial_sort_key(target),
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
                confidence = 0.96 if _point_in_box(point, candidates[0].box) else 0.62
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
        end_x = _first_int({**forwarding_payload, **payload}, ("end_x",))
        end_y = _first_int({**forwarding_payload, **payload}, ("end_y",))
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
    }


def degrade_target_confidence(confidence: float | None, *, index: int) -> float | None:
    if confidence is None:
        return None
    return round(max(0.1, confidence - ((index - 1) * 0.18)), 2)


def _build_vision_targets(
    *,
    screen: ScreenState,
    compact_nodes_by_id: Mapping[str, dict[str, object]],
    limit: int,
) -> list[ActionTarget]:
    targets: list[ActionTarget] = []
    for element in screen.elements[:limit]:
        targets.append(
            _build_vision_target(
                element=element,
                compact_nodes_by_id=compact_nodes_by_id,
                platform=screen.platform,
            )
        )
    targets = _filter_status_bar_like_targets(targets, screen_height=screen.screen_size[1])
    merged_targets = _merge_explicit_control_targets(targets)
    visible_targets = _filter_targets_outside_keyboard(merged_targets, screen=screen)
    return _sort_targets_spatially(_attach_embedded_ocr_texts(visible_targets))


def _build_tree_targets(
    *,
    screen: ScreenState,
    compact_tree: Mapping[str, object],
    limit: int,
) -> list[ActionTarget]:
    raw_nodes = compact_tree.get("nodes")
    if not isinstance(raw_nodes, list):
        return []
    targets: list[ActionTarget] = []
    for raw_node in raw_nodes[:limit]:
        if not isinstance(raw_node, dict):
            continue
        node = cast(dict[str, object], raw_node)
        box = _compact_box(node.get("b"))
        if box is None:
            continue
        state = node.get("state") if isinstance(node.get("state"), dict) else {}
        targets.append(
            ActionTarget(
                target_id=0,
                part="tree",
                source="tree",
                box=box,
                kind=cast(str | None, node.get("role")),
                text=cast(str | None, node.get("txt")),
                resource_id=cast(str | None, node.get("rid")),
                content_desc=cast(str | None, node.get("cd")),
                class_name=cast(str | None, node.get("cls")),
                semantic_role=cast(str | None, node.get("role")),
                enabled=_state_bool(state, "enabled"),
                checked=_state_bool(state, "checked"),
                selected=_state_bool(state, "selected"),
                clickable=_state_bool(state, "clickable"),
                focused=_state_bool(state, "focused"),
                linked_tree_node_id=cast(str | None, node.get("id")),
                stable_key=cast(str | None, node.get("sk")),
                label=compact_node_label(node),
                reason="tree_target",
                platform=screen.platform,
            )
        )
    return _sort_targets_spatially(targets)


def _build_vision_target(
    *,
    element: object,
    compact_nodes_by_id: Mapping[str, dict[str, object]],
    platform: str | None,
) -> ActionTarget:
    linked_node_id = getattr(element, "linked_tree_node_id", None)
    linked_compact_node = compact_nodes_by_id.get(str(linked_node_id)) if linked_node_id else None
    class_name = cast(str | None, getattr(element, "class_name", None))
    semantic_role = cast(str | None, getattr(element, "semantic_role", None))
    text = cast(str | None, getattr(element, "text", None))
    if not _has_text(text) and _is_explicit_control_values(class_name=class_name, semantic_role=semantic_role):
        text = _compact_node_text(linked_compact_node)
    label = _pick_target_label(
        text=text,
        content_desc=getattr(element, "content_desc", None),
        resource_id=getattr(element, "resource_id", None),
        semantic_role=semantic_role,
        class_name=class_name,
        linked_compact_node=linked_compact_node,
    )
    stable_key = linked_compact_node.get("sk") if isinstance(linked_compact_node, dict) else None
    return ActionTarget(
        target_id=0,
        part="vision",
        source=str(getattr(element, "source", None) or "vision"),
        box=cast(tuple[int, int, int, int], getattr(element, "box")),
        kind=cast(str | None, getattr(element, "kind", None)),
        text=text,
        resource_id=cast(str | None, getattr(element, "resource_id", None)),
        content_desc=cast(str | None, getattr(element, "content_desc", None)),
        class_name=class_name,
        semantic_role=semantic_role,
        enabled=cast(bool | None, getattr(element, "enabled", None)),
        checked=cast(bool | None, getattr(element, "checked", None)),
        selected=cast(bool | None, getattr(element, "selected", None)),
        clickable=cast(bool | None, getattr(element, "clickable", None)),
        focused=cast(bool | None, getattr(element, "focused", None)),
        linked_tree_node_id=cast(str | None, linked_node_id),
        stable_key=str(stable_key) if stable_key else None,
        label=label,
        reason="vision_target",
        platform=platform,
    )


def _pick_target_label(
    *,
    text: object,
    content_desc: object,
    resource_id: object,
    semantic_role: object,
    class_name: object,
    linked_compact_node: Mapping[str, object] | None,
) -> str | None:
    for value in (text, content_desc, resource_id, semantic_role, class_name):
        if _has_text(value):
            return str(value).strip()
    if linked_compact_node is None:
        return None
    return compact_node_label(linked_compact_node)


def _merge_explicit_control_targets(targets: list[ActionTarget]) -> list[ActionTarget]:
    merged_targets = list(targets)
    suppressed_indexes: set[int] = set()
    for index, target in enumerate(merged_targets):
        if target.part != "vision" or _explicit_control_kind(target) not in {"button", "input"}:
            continue
        child_candidates: list[tuple[int, ActionTarget]] = []
        for child_index, child in enumerate(merged_targets):
            if child_index == index or child_index in suppressed_indexes:
                continue
            if child.part != "vision":
                continue
            if not _is_mergeable_child_text_target(control=target, child=child):
                continue
            child_candidates.append((child_index, child))
        if not child_candidates:
            continue
        merged_targets[index] = _merge_control_target_label(target, [child for _, child in child_candidates])
        suppressed_indexes.update(child_index for child_index, _ in child_candidates)
    return [target for index, target in enumerate(merged_targets) if index not in suppressed_indexes]


def _filter_targets_outside_keyboard(targets: list[ActionTarget], *, screen: ScreenState) -> list[ActionTarget]:
    keyboard_bounds = _keyboard_bounds_from_platform_context(screen.platform_context)
    if keyboard_bounds is None:
        return targets
    return [target for target in targets if not _target_inside_keyboard(target, keyboard_bounds)]


def _keyboard_bounds_from_platform_context(
    platform_context: Mapping[str, object] | None,
) -> tuple[int, int, int, int] | None:
    if not isinstance(platform_context, Mapping):
        return None
    raw_bounds = platform_context.get("keyboard_bounds")
    if not isinstance(raw_bounds, list) or len(raw_bounds) != 4:
        return None
    try:
        left = int(raw_bounds[0])
        top = int(raw_bounds[1])
        right = int(raw_bounds[2])
        bottom = int(raw_bounds[3])
    except (TypeError, ValueError):
        return None
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def _target_inside_keyboard(target: ActionTarget, keyboard_bounds: tuple[int, int, int, int]) -> bool:
    center_x = (target.box[0] + target.box[2]) / 2
    center_y = (target.box[1] + target.box[3]) / 2
    return (
        keyboard_bounds[0] <= center_x <= keyboard_bounds[2]
        and keyboard_bounds[1] <= center_y <= keyboard_bounds[3]
    )


def _merge_control_target_label(control: ActionTarget, child_targets: list[ActionTarget]) -> ActionTarget:
    preferred_label = _preferred_child_text_label(child_targets)
    if preferred_label is None:
        return control
    return replace(
        control,
        text=control.text if _has_text(control.text) else preferred_label,
        label=preferred_label,
    )


def _preferred_child_text_label(child_targets: list[ActionTarget]) -> str | None:
    labels = [label for label in (_display_label(target) for target in child_targets) if label is not None]
    if not labels:
        return None
    return max(labels, key=len)


def _is_mergeable_child_text_target(*, control: ActionTarget, child: ActionTarget) -> bool:
    if _display_kind(child) != "text":
        return False
    if not _has_text(_display_label(child)):
        return False
    if child.clickable is True:
        return False
    return _box_contains(control.box, child.box) or _overlap_ratio(control.box, child.box) >= 0.75


def _explicit_control_kind(target: ActionTarget) -> str | None:
    return _target_profile(target).explicit_control_kind(target)


def _compact_node_text(linked_compact_node: Mapping[str, object] | None) -> str | None:
    if linked_compact_node is None:
        return None
    value = linked_compact_node.get("txt")
    if _has_text(value):
        return str(value).strip()
    return None


def _compact_tree_node_count(compact_tree: Mapping[str, object], *, uncapped: bool = False) -> int:
    raw_nodes = compact_tree.get("nodes")
    if not isinstance(raw_nodes, list):
        return 0
    if uncapped:
        return len(raw_nodes)
    return min(len(raw_nodes), TREE_PART_MAX)


def _compact_box(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        return (int(value[0]), int(value[1]), int(value[2]), int(value[3]))
    except (TypeError, ValueError):
        return None


def _state_bool(state: object, key: str) -> bool | None:
    if not isinstance(state, dict):
        return None
    value = state.get(key)
    return value if isinstance(value, bool) else None


def _box_contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _overlap_ratio(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return 0.0
    intersection_area = (right - left) * (bottom - top)
    second_area = _box_area(second)
    if second_area <= 0:
        return 0.0
    return intersection_area / second_area


def _is_explicit_control_values(*, class_name: str | None, semantic_role: str | None) -> bool:
    normalized_role = _normalized_text(semantic_role)
    normalized_class = _normalized_text(class_name)
    if normalized_role in {"input", "button"}:
        return True
    return "edittext" in normalized_class or any(
        token in normalized_class for token in ("button", "imagebutton", "floatingactionbutton")
    )


def _box_area(box: tuple[int, int, int, int]) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized_text(value: object) -> str:
    return str(value or "").strip().lower()


def _target_has_primary_label(target: ActionTarget) -> bool:
    return any(_has_text(value) for value in (target.text, target.content_desc, target.resource_id, target.label))


def _display_kind(target: ActionTarget) -> str:
    return _target_profile(target).display_kind(target)


def _display_label(target: ActionTarget) -> str | None:
    return _target_profile(target).display_label(target)


def _resource_id_label(value: str | None) -> str | None:
    if not _has_text(value):
        return None
    text = str(value).strip()
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    if ":" in text:
        text = text.rsplit(":", 1)[-1]
    return text or None


def _attach_embedded_ocr_texts(targets: list[ActionTarget]) -> list[ActionTarget]:
    updated_targets = list(targets)
    ocr_targets = [target for target in updated_targets if _is_ocr_text_target(target)]
    for index, target in enumerate(updated_targets):
        if not _should_attach_embedded_ocr_texts(target):
            continue
        embedded_texts = _collect_embedded_ocr_texts(target, ocr_targets)
        if not embedded_texts:
            continue
        updated_targets[index] = replace(target, ocr_texts=embedded_texts)
    return updated_targets


def _filter_status_bar_like_targets(targets: list[ActionTarget], *, screen_height: int) -> list[ActionTarget]:
    return [target for target in targets if not _is_status_bar_like_target(target, screen_height=screen_height)]


def _is_status_bar_like_target(target: ActionTarget, *, screen_height: int) -> bool:
    return _target_profile(target).is_status_bar_like_target(target, screen_height=screen_height)


def _looks_like_status_bar_text(value: str | None) -> bool:
    if not _has_text(value):
        return False
    text = str(value).strip()
    compact = text.replace(" ", "").upper()
    if ":" in compact and any(ch.isdigit() for ch in compact):
        if all(ch.isdigit() or ch in {":", "A", "P", "M"} for ch in compact):
            return True
    if compact.endswith("%") and compact[:-1].isdigit():
        return True
    return False


def _target_profile(target: ActionTarget):
    return get_runner_profile(target.platform)


def _should_attach_embedded_ocr_texts(target: ActionTarget) -> bool:
    if target.part != "vision":
        return False
    return _display_kind(target) in {"icon", "container"}


def _is_ocr_text_target(target: ActionTarget) -> bool:
    if target.part != "vision":
        return False
    if _normalized_text(target.kind) != "text":
        return False
    return _has_text(target.text)


def _collect_embedded_ocr_texts(target: ActionTarget, ocr_targets: list[ActionTarget]) -> tuple[str, ...]:
    embedded: list[tuple[int, int, str]] = []
    for ocr_target in ocr_targets:
        if ocr_target is target:
            continue
        if not _box_contains(target.box, ocr_target.box):
            continue
        text = _clip_ocr_text(cast(str, ocr_target.text))
        if not text:
            continue
        embedded.append((ocr_target.box[1], ocr_target.box[0], text))
    embedded.sort()
    unique_texts: list[str] = []
    for _, _, text in embedded:
        if text in unique_texts:
            continue
        unique_texts.append(text)
        if len(unique_texts) >= 3:
            break
    return tuple(unique_texts)


def _clip_ocr_text(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if len(text) <= 48:
        return text
    return f"{text[:45]}..."


def _sort_targets_spatially(targets: list[ActionTarget]) -> list[ActionTarget]:
    return sorted(targets, key=_spatial_sort_key)


def _spatial_sort_key(target: ActionTarget) -> tuple[int, int, int, int, int]:
    left, top, right, bottom = target.box
    center_y = (top + bottom) // 2
    center_x = (left + right) // 2
    area = _box_area(target.box)
    return (center_y, center_x, top, left, area)


def _point_in_box(point: tuple[int, int], box: tuple[int, int, int, int]) -> bool:
    x, y = point
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def _distance_sq_to_box_center(point: tuple[int, int], box: tuple[int, int, int, int]) -> int:
    center_x = (box[0] + box[2]) // 2
    center_y = (box[1] + box[3]) // 2
    return (point[0] - center_x) ** 2 + (point[1] - center_y) ** 2


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
        x = _first_int(payload, x_keys)
        y = _first_int(payload, y_keys)
        if x is not None and y is not None:
            return (x, y)
    return None


def _first_int(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
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
    return (bucket, _spatial_sort_key(target))


def _looks_scrollable(target: ActionTarget) -> bool:
    class_name = str(target.class_name or "").lower()
    kind = str(target.kind or "").lower()
    role = str(target.semantic_role or "").lower()
    return any(token in class_name for token in ("scroll", "recycler", "listview", "viewpager")) or kind in {
        "container",
        "scroll",
    } or role in {"container", "list", "scroll"}


def _looks_like_input_target(target: ActionTarget) -> bool:
    normalized_kind = _normalized_text(target.kind)
    normalized_role = _normalized_text(target.semantic_role)
    normalized_class = _normalized_text(target.class_name)
    if normalized_kind == "input" or normalized_role == "input":
        return True
    return "edittext" in normalized_class or "textfield" in normalized_class or "input" in normalized_class


def _input_target_sort_key(target: ActionTarget) -> tuple[int, int, int, int, int, int, int]:
    return (
        0 if target.focused else 1,
        0 if _looks_like_input_target(target) else 1,
        *_spatial_sort_key(target),
    )
