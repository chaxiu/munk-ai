from __future__ import annotations

from ..base import ScreenState
from .high_level_common import (
    KEYBOARD_INPUT_CLASS_TOKENS,
    TEXT_RECENTER_EPSILON_RATIO,
    TEXT_RECENTER_MAX_DISTANCE_RATIO,
    TEXT_RECENTER_TARGET_RATIO,
)


def normalize_text_for_match(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def screen_contains_text(screen: ScreenState, text: str) -> bool:
    needle = normalize_text_for_match(text)
    if not needle:
        return False
    for element in screen.elements:
        if needle in normalize_text_for_match(element.text):
            return True
    frame = screen.screen_frame
    if frame is None:
        return False
    for node in frame.tree_nodes:
        if needle in normalize_text_for_match(node.text):
            return True
    return False


def screen_likely_has_visible_keyboard(screen: ScreenState, *, recent_input: bool = False) -> bool:
    _ = recent_input
    frame = screen.screen_frame
    if frame is None:
        return False
    for node in frame.tree_nodes:
        semantic = (node.semantic_role or "").lower()
        class_name = (node.class_name or "").lower()
        is_input = semantic == "input" or any(token in class_name for token in KEYBOARD_INPUT_CLASS_TOKENS)
        if is_input and node.focused:
            return True
    return False


def input_target_has_text(
    screen: ScreenState,
    target_box: tuple[int, int, int, int] | None,
) -> bool:
    frame = screen.screen_frame
    if frame is not None:
        for node in frame.tree_nodes:
            semantic = (node.semantic_role or "").lower()
            class_name = (node.class_name or "").lower()
            is_input = semantic == "input" or any(
                token in class_name for token in KEYBOARD_INPUT_CLASS_TOKENS
            )
            if not is_input:
                continue
            if target_box is not None and not boxes_overlap(node.bounds, target_box):
                continue
            if (node.text or "").strip():
                return True
    for element in screen.elements:
        if target_box is not None and not boxes_overlap(element.box, target_box):
            continue
        if (element.text or "").strip():
            return True
    return False


def boxes_overlap(
    left: tuple[int, int, int, int],
    right: tuple[int, int, int, int],
) -> bool:
    return not (
        left[2] <= right[0]
        or right[2] <= left[0]
        or left[3] <= right[1]
        or right[3] <= left[1]
    )


def map_box_to_screen_space(
    target_box: tuple[int, int, int, int] | None,
    *,
    device_size: tuple[int, int],
    screen_size: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    if target_box is None:
        return None
    device_w, device_h = device_size
    screen_w, screen_h = screen_size
    if device_w <= 0 or device_h <= 0 or screen_w <= 0 or screen_h <= 0:
        return target_box
    if device_w == screen_w and device_h == screen_h:
        return target_box
    scale_x = screen_w / float(device_w)
    scale_y = screen_h / float(device_h)
    left = int(round(target_box[0] * scale_x))
    top = int(round(target_box[1] * scale_y))
    right = int(round(target_box[2] * scale_x))
    bottom = int(round(target_box[3] * scale_y))
    left = max(0, min(screen_w - 1, left))
    top = max(0, min(screen_h - 1, top))
    right = max(0, min(screen_w - 1, right))
    bottom = max(0, min(screen_h - 1, bottom))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def screen_matches_text_condition(
    screen: ScreenState,
    *,
    match_type: str,
    texts: tuple[str, ...],
) -> bool:
    visible_texts = build_screen_text_snapshot(screen)
    visible_blob = " ".join(visible_texts)

    def contains(text: str) -> bool:
        needle = normalize_text_for_match(text)
        if not needle:
            return False
        return needle in visible_blob or any(needle in candidate for candidate in visible_texts)

    if match_type == "any_of_texts":
        return any(contains(text) for text in texts)
    if match_type == "all_texts":
        return all(contains(text) for text in texts)
    if match_type == "none_of_texts":
        return not any(contains(text) for text in texts)
    return False


def build_text_match_summary(*, match_type: str, texts: tuple[str, ...]) -> str:
    joined = ", ".join(repr(text) for text in texts)
    return f"{match_type}: [{joined}]"


def build_screen_text_snapshot(screen: ScreenState) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for element in screen.elements:
        normalized = normalize_text_for_match(element.text)
        if normalized and normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    frame = screen.screen_frame
    if frame is None:
        return values
    for node in frame.tree_nodes:
        normalized = normalize_text_for_match(node.text)
        if normalized and normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    return values


def locate_matched_text_box(
    screen: ScreenState,
    *,
    match_type: str,
    texts: tuple[str, ...],
) -> tuple[int, int, int, int] | None:
    if match_type not in {"any_of_texts", "all_texts"}:
        return None
    needles = tuple(normalize_text_for_match(text) for text in texts if normalize_text_for_match(text))
    if not needles:
        return None
    matched_boxes: list[tuple[int, int, int, int]] = []
    matched_needles: set[str] = set()
    seen_boxes: set[tuple[int, int, int, int]] = set()

    def collect_match(text_value: str | None, box: tuple[int, int, int, int]) -> None:
        normalized = normalize_text_for_match(text_value)
        if not normalized:
            return
        matching_needles = [needle for needle in needles if needle in normalized]
        if not matching_needles:
            return
        matched_needles.update(matching_needles)
        if box in seen_boxes:
            return
        seen_boxes.add(box)
        matched_boxes.append(box)

    for element in screen.elements:
        collect_match(element.text, element.box)
    frame = screen.screen_frame
    if frame is not None:
        for node in frame.tree_nodes:
            collect_match(node.text, node.bounds)
    if not matched_boxes:
        return None
    if match_type == "all_texts" and not all(needle in matched_needles for needle in needles):
        return None
    return merge_boxes(matched_boxes)


def merge_boxes(boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = max(box[2] for box in boxes)
    bottom = max(box[3] for box in boxes)
    return (left, top, right, bottom)


def box_center_y_ratio(
    box: tuple[int, int, int, int],
    *,
    screen_size: tuple[int, int],
) -> float:
    screen_height = screen_size[1]
    if screen_height <= 0:
        return TEXT_RECENTER_TARGET_RATIO
    return ((box[1] + box[3]) / 2.0) / float(screen_height)


def resolve_text_recenter_adjustment(
    box: tuple[int, int, int, int],
    *,
    screen_size: tuple[int, int],
) -> tuple[str | None, float]:
    center_ratio = box_center_y_ratio(box, screen_size=screen_size)
    diff_ratio = TEXT_RECENTER_TARGET_RATIO - center_ratio
    if abs(diff_ratio) <= TEXT_RECENTER_EPSILON_RATIO:
        return None, 0.0
    distance_ratio = min(abs(diff_ratio), TEXT_RECENTER_MAX_DISTANCE_RATIO)
    direction = "up" if diff_ratio > 0 else "down"
    return direction, distance_ratio
