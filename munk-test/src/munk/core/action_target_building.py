from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import cast

from munk.agent_base.base import ScreenState
from munk.agent_base.platform_profile import get_runner_profile
from munk.core.action_target_geometry import (
    box_area,
    box_contains,
    box_intersects_viewport,
    overlap_ratio,
    sort_targets_spatially,
)
from munk.core.action_target_models import ActionTarget, TargetParts
from munk.core.action_target_refs import (
    build_a11y_handle,
    build_dom_handle,
    build_spatial_handle,
    build_target_ref,
    is_form_control_target,
)
from munk.core.action_target_utils import (
    clip_ocr_text,
    compact_box,
    compact_node_text,
    has_text,
    normalized_text,
    state_bool,
)
from munk.core.compact_tree import build_compact_tree, compact_node_label, index_compact_tree_nodes


def build_action_targets(screen: ScreenState, *, max_elements: int) -> list[ActionTarget]:
    parts = build_target_parts(
        screen,
        vision_limit=max(max_elements, 0),
        tree_limit=max(max_elements, 0),
    )
    return [*parts.vision_targets, *parts.tree_targets]


def build_target_parts(screen: ScreenState, *, vision_limit: int, tree_limit: int) -> TargetParts:
    normalized_vision_limit = max(vision_limit, 0)
    normalized_tree_limit = max(tree_limit, 0)
    canonical_parts = build_canonical_target_parts(screen)
    return TargetParts(
        vision_targets=canonical_parts.vision_targets[:normalized_vision_limit],
        tree_targets=canonical_parts.tree_targets[:normalized_tree_limit],
        vision_total=canonical_parts.vision_total,
        tree_total=canonical_parts.tree_total,
        is_canonical_snapshot=False,
    )


def build_canonical_target_parts(screen: ScreenState) -> TargetParts:
    cached_parts = screen.action_target_parts
    if cached_parts is not None and cached_parts.is_canonical_snapshot:
        return cached_parts
    return _build_canonical_target_parts_uncached(screen)


def _build_canonical_target_parts_uncached(screen: ScreenState) -> TargetParts:
    raw_tree_nodes = screen.screen_frame.tree_nodes if screen.screen_frame is not None else []
    tree_limit = len(raw_tree_nodes)
    return _build_target_parts_uncached(
        screen,
        vision_limit=len(screen.elements),
        tree_limit=tree_limit,
        is_canonical_snapshot=True,
    )


def _build_target_parts_uncached(
    screen: ScreenState,
    *,
    vision_limit: int,
    tree_limit: int,
    is_canonical_snapshot: bool,
) -> TargetParts:
    compact_tree = build_compact_tree(
        screen.screen_frame.tree_nodes if screen.screen_frame is not None else [],
        platform=screen.platform,
    )
    compact_nodes_by_id = index_compact_tree_nodes(compact_tree)
    vision_targets_all = _build_vision_targets(
        screen=screen,
        compact_nodes_by_id=compact_nodes_by_id,
        limit=vision_limit,
    )
    tree_targets_all = _build_tree_targets(screen=screen, compact_tree=compact_tree, limit=tree_limit)
    numbered_vision_targets = [
        _assign_channel_identity(target, channel="v", index=index, transitional_target_id=index)
        for index, target in enumerate(vision_targets_all, start=1)
    ]
    tree_start_id = len(numbered_vision_targets) + 1
    numbered_tree_targets = [
        _assign_channel_identity(
            target,
            channel="t",
            index=index + 1,
            transitional_target_id=tree_start_id + index,
        )
        for index, target in enumerate(tree_targets_all)
    ]
    return TargetParts(
        vision_targets=numbered_vision_targets,
        tree_targets=numbered_tree_targets,
        vision_total=len(numbered_vision_targets),
        tree_total=len(numbered_tree_targets),
        is_canonical_snapshot=is_canonical_snapshot,
    )


def select_form_first_tree_targets(targets: list[ActionTarget], *, limit: int) -> list[ActionTarget]:
    if limit <= 0:
        return []
    form_controls = [target for target in targets if is_form_control_target(target)]
    others = [target for target in targets if not is_form_control_target(target)]
    ordered = [*form_controls, *others]
    return ordered[:limit]


def _assign_channel_identity(
    target: ActionTarget,
    *,
    channel: str,
    index: int,
    transitional_target_id: int,
) -> ActionTarget:
    ref = build_target_ref(channel=channel, index=index)  # type: ignore[arg-type]
    handle = target.handle
    if handle is None:
        if channel == "v":
            handle = build_spatial_handle(target.box)
        elif (target.platform or "").lower() == "web":
            handle = build_dom_handle(
                node_id=target.linked_tree_node_id or f"missing-{index}",
                box=target.box,
                tag=target.class_name,
                input_type=target.input_type,
                name=target.dom_name,
                value=target.dom_value,
                resource_id=target.resource_id,
                test_id=target.test_id,
                stable_key=target.stable_key,
            )
        else:
            handle = build_a11y_handle(
                node_id=target.linked_tree_node_id,
                stable_key=target.stable_key,
                resource_id=target.resource_id,
                class_name=target.class_name,
                box=target.box,
            )
    return replace(
        target,
        target_id=transitional_target_id,
        ref=ref,
        channel=channel,
        index=index,
        handle=handle,
    )


def _build_vision_targets(
    *,
    screen: ScreenState,
    compact_nodes_by_id: Mapping[str, dict[str, object]],
    limit: int,
) -> list[ActionTarget]:
    targets = [
        _build_vision_target(
            element=element,
            compact_nodes_by_id=compact_nodes_by_id,
            platform=screen.platform,
        )
        for element in screen.elements[:limit]
    ]
    targets = _filter_status_bar_like_targets(targets, screen_height=screen.screen_size[1])
    merged_targets = _merge_explicit_control_targets(targets)
    visible_targets = _filter_targets_outside_keyboard(merged_targets, screen=screen)
    return sort_targets_spatially(_attach_embedded_ocr_texts(visible_targets))


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
        box = compact_box(node.get("b"))
        if box is None:
            continue
        raw_state = node.get("state")
        state = cast(Mapping[str, object] | None, raw_state) if isinstance(raw_state, dict) else None
        node_id = cast(str | None, node.get("id"))
        class_name = cast(str | None, node.get("cls"))
        input_type = cast(str | None, node.get("input_type"))
        dom_name = cast(str | None, node.get("name"))
        dom_value = cast(str | None, node.get("value"))
        test_id = cast(str | None, node.get("test_id"))
        resource_id = cast(str | None, node.get("rid"))
        stable_key = cast(str | None, node.get("sk"))
        if (screen.platform or "").lower() == "web" and node_id:
            handle = build_dom_handle(
                node_id=node_id,
                box=box,
                tag=class_name,
                input_type=input_type,
                name=dom_name,
                value=dom_value,
                resource_id=resource_id,
                test_id=test_id,
                stable_key=stable_key,
            )
        else:
            handle = build_a11y_handle(
                node_id=node_id,
                stable_key=stable_key,
                resource_id=resource_id,
                class_name=class_name,
                box=box,
            )
        targets.append(
            ActionTarget(
                target_id=0,
                part="tree",
                source="tree",
                box=box,
                handle=handle,
                kind=cast(str | None, node.get("role")),
                text=cast(str | None, node.get("txt")),
                resource_id=resource_id,
                content_desc=cast(str | None, node.get("cd")),
                class_name=class_name,
                semantic_role=cast(str | None, node.get("role")),
                enabled=state_bool(state, "enabled"),
                checked=state_bool(state, "checked"),
                selected=state_bool(state, "selected"),
                clickable=state_bool(state, "clickable"),
                focused=state_bool(state, "focused"),
                linked_tree_node_id=node_id,
                stable_key=stable_key,
                label=_tree_target_label(node, input_type=input_type, dom_name=dom_name, dom_value=dom_value),
                reason="tree_target",
                platform=screen.platform,
                input_type=input_type,
                dom_name=dom_name,
                dom_value=dom_value,
                test_id=test_id,
            )
        )
    on_screen_targets = _filter_targets_outside_viewport(targets, screen_size=screen.screen_size)
    visible_targets = _filter_targets_outside_keyboard(on_screen_targets, screen=screen)
    return sort_targets_spatially(visible_targets)


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
    if not has_text(text) and _is_explicit_control_values(class_name=class_name, semantic_role=semantic_role):
        text = compact_node_text(linked_compact_node)
    label = _pick_target_label(
        text=text,
        content_desc=getattr(element, "content_desc", None),
        resource_id=getattr(element, "resource_id", None),
        semantic_role=semantic_role,
        class_name=class_name,
        linked_compact_node=linked_compact_node,
    )
    stable_key = linked_compact_node.get("sk") if isinstance(linked_compact_node, dict) else None
    box = cast(tuple[int, int, int, int], getattr(element, "box"))
    return ActionTarget(
        target_id=0,
        part="vision",
        source=str(getattr(element, "source", None) or "vision"),
        box=box,
        handle=build_spatial_handle(box),
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


def _tree_target_label(
    node: Mapping[str, object],
    *,
    input_type: str | None,
    dom_name: str | None,
    dom_value: str | None,
) -> str | None:
    tag = cast(str | None, node.get("cls"))
    parts: list[str] = []
    if tag:
        parts.append(tag)
    if input_type:
        parts.append(f"type={input_type}")
    if dom_name:
        parts.append(f"name={dom_name}")
    if dom_value is not None and str(dom_value).strip() != "":
        parts.append(f'value="{dom_value}"')
    elif input_type or tag in {"input", "textarea", "select"}:
        parts.append('value=""')
    if parts:
        return " ".join(parts)
    return compact_node_label(node)


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
        if has_text(value):
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


def _filter_targets_outside_viewport(
    targets: list[ActionTarget],
    *,
    screen_size: tuple[int, int],
) -> list[ActionTarget]:
    screen_width, screen_height = screen_size
    return [
        target
        for target in targets
        if box_intersects_viewport(target.box, screen_width=screen_width, screen_height=screen_height)
    ]


def _merge_control_target_label(control: ActionTarget, child_targets: list[ActionTarget]) -> ActionTarget:
    preferred_label = _preferred_child_text_label(child_targets)
    if preferred_label is None:
        return control
    return replace(
        control,
        text=control.text if has_text(control.text) else preferred_label,
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
    if not has_text(_display_label(child)):
        return False
    if child.clickable is True:
        return False
    return box_contains(control.box, child.box) or overlap_ratio(control.box, child.box) >= 0.75


def _explicit_control_kind(target: ActionTarget) -> str | None:
    return _target_profile(target).explicit_control_kind(target)


def _is_explicit_control_values(*, class_name: str | None, semantic_role: str | None) -> bool:
    normalized_role = normalized_text(semantic_role)
    normalized_class = normalized_text(class_name)
    if normalized_role in {"input", "button"}:
        return True
    return "edittext" in normalized_class or any(
        token in normalized_class for token in ("button", "imagebutton", "floatingactionbutton")
    )


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


def _target_profile(target: ActionTarget):
    return get_runner_profile(target.platform)


def _should_attach_embedded_ocr_texts(target: ActionTarget) -> bool:
    if target.part != "vision":
        return False
    return _display_kind(target) in {"icon", "container"}


def _is_ocr_text_target(target: ActionTarget) -> bool:
    if target.part != "vision":
        return False
    if normalized_text(target.kind) != "text":
        return False
    return has_text(target.text)


def _collect_embedded_ocr_texts(target: ActionTarget, ocr_targets: list[ActionTarget]) -> tuple[str, ...]:
    embedded: list[tuple[int, int, str]] = []
    for ocr_target in ocr_targets:
        if ocr_target is target:
            continue
        if not box_contains(target.box, ocr_target.box):
            continue
        text = clip_ocr_text(cast(str, ocr_target.text))
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


def _display_kind(target: ActionTarget) -> str:
    return _target_profile(target).display_kind(target)


def _display_label(target: ActionTarget) -> str | None:
    return _target_profile(target).display_label(target)
