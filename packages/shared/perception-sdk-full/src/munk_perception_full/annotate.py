from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import cv2
from munk.perception.image import BgrImage
from munk.perception.types import ClickableElement


@dataclass(frozen=True)
class LabelStyle:
    font_scale: float
    thickness: int
    pad: int
    border_thickness: int
    margin: int
    overlap_padding: int
    text_box_padding: int


def annotate_image(
    image_bgr: BgrImage,
    elements: list[ClickableElement],
    *,
    annotate_text: bool = True,
) -> BgrImage:
    canvas = cast(BgrImage, image_bgr.copy())
    canvas_shape: tuple[int, int] = (int(canvas.shape[0]), int(canvas.shape[1]))
    visible_items: list[tuple[int, ClickableElement, tuple[int, int, int, int]]] = []
    for idx, element in enumerate(elements, start=1):
        if not annotate_text and element.kind == "text":
            continue
        if element.kind == "text":
            style = _build_label_style(canvas_shape, element.box)
            display_box = _pad_box(element.box, canvas_shape, style.text_box_padding)
        else:
            display_box = element.box
        visible_items.append((idx, element, display_box))
    boxes = [display_box for _, _, display_box in visible_items]
    for idx, element, display_box in visible_items:
        x1, y1, x2, y2 = display_box
        style = _build_label_style(canvas_shape, display_box)
        color = (0, 200, 0) if element.kind == "icon" else (200, 0, 0)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, style.border_thickness)
        label = f"{idx}"
        label_w, label_h, _ = _measure_label(label, style)
        position = _choose_text_label_position(
            display_box,
            boxes,
            label_w,
            label_h,
            canvas_shape,
            style,
        )
        background = color if element.kind == "icon" else (60, 60, 220)
        _draw_label(
            canvas,
            label,
            position,
            background,
            (255, 255, 255),
            style,
        )
    return canvas


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
        text_box_padding=_clamp_int(round(text_px / 6), lower=2, upper=6),
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


def _pad_box(
    box: tuple[int, int, int, int],
    image_shape: tuple[int, int],
    padding: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    height, width = image_shape
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(width - 1, x2 + padding)
    y2 = min(height - 1, y2 + padding)
    return x1, y1, x2, y2


def _choose_text_label_position(
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
