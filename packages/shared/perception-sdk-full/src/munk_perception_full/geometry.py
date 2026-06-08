from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float32]
IndexArray = npt.NDArray[np.int_]


def nms(
    boxes: FloatArray,
    scores: FloatArray,
    iou_threshold: float,
    nested_area_ratio: float = 3.0,
) -> list[int]:
    if len(boxes) == 0:
        return []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order: IndexArray = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        small_area = np.minimum(areas[i], areas[order[1:]])
        area_ratio = np.maximum(areas[i], areas[order[1:]]) / (small_area + 1e-6)
        contain_ratio = inter / (small_area + 1e-6)
        keep_nested = (contain_ratio >= 0.9) & (area_ratio >= nested_area_ratio)
        suppress = (iou > iou_threshold) & ~keep_nested
        keep_mask = ~suppress
        inds: IndexArray = np.where(keep_mask)[0]
        order = order[inds + 1]
    return keep


def box_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter_area + 1e-6
    return float(inter_area / union)
