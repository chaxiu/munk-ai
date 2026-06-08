from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import cv2

from munk.core.action_targets import ActionTarget
from munk.perception.image import BgrImage

from .platform_profile import get_runner_profile

_VISION_COLOR = (0, 200, 0)
_ANNOTATED_VISION_KINDS = frozenset({"icon", "button", "input", "switch", "checkbox"})
_ANNOTATED_TREE_KINDS = frozenset({"button", "input", "switch", "checkbox"})
_DEDUP_IOU_THRESHOLD = 0.6
_DEDUP_CENTER_DISTANCE_RATIO = 0.18
_DEDUP_AREA_RATIO_MIN = 0.67
_DEDUP_AREA_RATIO_MAX = 1.5


@dataclass(frozen=True)
class LabelStyle:
    font_scale: float
    thickness: int
    pad: int
    border_thickness: int
    margin: int
    overlap_padding: int


def annotate_action_targets(
    image_bgr: BgrImage,
    targets: list[ActionTarget],
) -> BgrImage:
    targets = filter_annotated_targets(targets)
    canvas = cast(BgrImage, image_bgr.copy())
    canvas_shape: tuple[int, int] = (int(canvas.shape[0]), int(canvas.shape[1]))
    boxes = [target.box for target in targets]
    for target in targets:
        x1, y1, x2, y2 = target.box
        style = _build_label_style(canvas_shape, target.box)
        color = _target_color(target)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, style.border_thickness)
        label = str(target.target_id)
        label_w, label_h, _ = _measure_label(label, style)
        position = _choose_label_position(
            target.box,
            boxes,
            label_w,
            label_h,
            canvas_shape,
            style,
        )
        _draw_label(canvas, label, position, color, (255, 255, 255), style)
    return canvas


def filter_annotated_targets(targets: list[ActionTarget]) -> list[ActionTarget]:
    vision_targets = [target for target in targets if _should_annotate_vision_target(target)]
    tree_fallback_targets = [
        target
        for target in targets
        if _should_annotate_tree_target(target) and not _has_matching_vision_target(target, vision_targets)
    ]
    return [*vision_targets, *tree_fallback_targets]


def _should_annotate_vision_target(target: ActionTarget) -> bool:
    return target.part == "vision" and _display_kind(target) in _ANNOTATED_VISION_KINDS


def _should_annotate_tree_target(target: ActionTarget) -> bool:
    return target.part == "tree" and _display_kind(target) in _ANNOTATED_TREE_KINDS


def _has_matching_vision_target(tree_target: ActionTarget, vision_targets: list[ActionTarget]) -> bool:
    for vision_target in vision_targets:
        if _matches_same_control(tree_target, vision_target):
            return True
    return False


def _matches_same_control(tree_target: ActionTarget, vision_target: ActionTarget) -> bool:
    if _intersection_over_union(tree_target.box, vision_target.box) >= _DEDUP_IOU_THRESHOLD:
        return True
    if not _area_ratio_in_range(tree_target.box, vision_target.box):
        return False
    return _center_distance(tree_target.box, vision_target.box) <= _dedupe_center_distance_limit(
        tree_target.box,
        vision_target.box,
    )


def _target_color(_target: ActionTarget) -> tuple[int, int, int]:
    return _VISION_COLOR


def _display_kind(target: ActionTarget) -> str:
    return get_runner_profile(target.platform).display_kind(target)


def _build_label_style(
    image_shape: tuple[int, int],
    box: tuple[int, int, int, int],
) -> LabelStyle:
    image_height, image_width = image_shape
    short_side = max(1, min(image_width, image_height))
    x1, y1, x2, y2 = box
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    box_short_side = max(1, min(box_width, box_height))

    global_text_px = _clamp_int(round(short_side * 0.018), lower=14, upper=28)
    local_text_px = _clamp_int(round(box_short_side * 0.6), lower=14, upper=32)
    text_px = min(global_text_px, local_text_px)

    return LabelStyle(
        font_scale=max(0.5, text_px / 22.0),
        thickness=_clamp_int(round(text_px / 10), lower=1, upper=4),
        pad=_clamp_int(round(text_px / 4), lower=2, upper=8),
        border_thickness=_clamp_int(round(text_px / 9), lower=1, upper=4),
        margin=_clamp_int(round(text_px / 5), lower=2, upper=8),
        overlap_padding=_clamp_int(round(text_px / 5), lower=2, upper=8),
    )


def _measure_label(label: str, style: LabelStyle) -> tuple[int, int, int]:
    font = cv2.FONT_HERSHEY_SIMPLEX
    size, baseline = cv2.getTextSize(label, font, style.font_scale, style.thickness)
    width, height = size
    return width + style.pad * 2, height + style.pad * 2, baseline


def _draw_label(
    canvas: BgrImage,
    label: str,
    top_left: tuple[int, int],
    background: tuple[int, int, int],
    text_color: tuple[int, int, int],
    style: LabelStyle,
) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size, _ = cv2.getTextSize(label, font, style.font_scale, style.thickness)
    text_w, text_h = text_size
    x, y = top_left
    rect_w = text_w + style.pad * 2
    rect_h = text_h + style.pad * 2
    h = int(canvas.shape[0])
    w = int(canvas.shape[1])
    x = max(0, min(w - rect_w, x))
    y = max(0, min(h - rect_h, y))
    cv2.rectangle(canvas, (x, y), (x + rect_w, y + rect_h), background, -1)
    cv2.putText(
        canvas,
        label,
        (x + style.pad, y + style.pad + text_h),
        font,
        style.font_scale,
        text_color,
        style.thickness,
    )


def _choose_label_position(
    box: tuple[int, int, int, int],
    all_boxes: list[tuple[int, int, int, int]],
    label_w: int,
    label_h: int,
    image_shape: tuple[int, int],
    style: LabelStyle,
) -> tuple[int, int]:
    x1, y1, x2, y2 = box
    height, width = image_shape
    candidates = [
        (x1 - style.margin, y1 - style.margin - label_h),
        (x2 + style.margin - label_w, y1 - style.margin - label_h),
        (x1 - style.margin, y2 + style.margin),
        (x2 + style.margin - label_w, y2 + style.margin),
    ]
    best = candidates[0]
    best_hits = float("inf")
    for candidate in candidates:
        rect = _clamp_rect((candidate[0], candidate[1], label_w, label_h), width, height)
        hits = _count_overlaps(rect, all_boxes, box, padding=style.overlap_padding)
        if hits < best_hits:
            best_hits = hits
            best = (rect[0], rect[1])
            if hits == 0:
                break
    return best


def _clamp_rect(
    rect: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    x = max(0, min(width - w, x))
    y = max(0, min(height - h, y))
    return x, y, w, h


def _count_overlaps(
    rect: tuple[int, int, int, int],
    boxes: list[tuple[int, int, int, int]],
    current: tuple[int, int, int, int],
    padding: int,
) -> int:
    x, y, w, h = rect
    rx1, ry1, rx2, ry2 = x, y, x + w, y + h
    hits = 0
    for box in boxes:
        if box == current:
            continue
        bx1, by1, bx2, by2 = box
        bx1 -= padding
        by1 -= padding
        bx2 += padding
        by2 += padding
        if rx1 < bx2 and rx2 > bx1 and ry1 < by2 and ry2 > by1:
            hits += 1
    return hits


def _clamp_int(value: int, *, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _intersection_over_union(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return 0.0
    intersection_area = (right - left) * (bottom - top)
    union_area = _box_area(first) + _box_area(second) - intersection_area
    if union_area <= 0:
        return 0.0
    return intersection_area / union_area


def _area_ratio_in_range(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> bool:
    first_area = _box_area(first)
    second_area = _box_area(second)
    if first_area <= 0 or second_area <= 0:
        return False
    ratio = first_area / second_area
    return _DEDUP_AREA_RATIO_MIN <= ratio <= _DEDUP_AREA_RATIO_MAX


def _center_distance(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    first_center_x = (first[0] + first[2]) / 2.0
    first_center_y = (first[1] + first[3]) / 2.0
    second_center_x = (second[0] + second[2]) / 2.0
    second_center_y = (second[1] + second[3]) / 2.0
    dx = first_center_x - second_center_x
    dy = first_center_y - second_center_y
    return (dx * dx + dy * dy) ** 0.5


def _dedupe_center_distance_limit(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    return _DEDUP_CENTER_DISTANCE_RATIO * max(_box_short_side(first), _box_short_side(second))


def _box_short_side(box: tuple[int, int, int, int]) -> int:
    return max(1, min(box[2] - box[0], box[3] - box[1]))


def _box_area(box: tuple[int, int, int, int]) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])
