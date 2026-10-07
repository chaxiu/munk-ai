from __future__ import annotations

from munk.core.action_target_models import ActionTarget


def box_area(box: tuple[int, int, int, int]) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def box_contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def overlap_ratio(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return 0.0
    intersection_area = (right - left) * (bottom - top)
    second_area = box_area(second)
    if second_area <= 0:
        return 0.0
    return intersection_area / second_area


def box_intersects_viewport(
    box: tuple[int, int, int, int],
    *,
    screen_width: int,
    screen_height: int,
) -> bool:
    x1, y1, x2, y2 = box
    return not (x2 <= 0 or y2 <= 0 or x1 >= screen_width or y1 >= screen_height)


def spatial_sort_key(target: ActionTarget) -> tuple[int, int, int, int, int]:
    left, top, right, bottom = target.box
    center_y = (top + bottom) // 2
    center_x = (left + right) // 2
    area = box_area(target.box)
    return (center_y, center_x, top, left, area)


def sort_targets_spatially(targets: list[ActionTarget]) -> list[ActionTarget]:
    return sorted(targets, key=spatial_sort_key)


def point_in_box(point: tuple[int, int], box: tuple[int, int, int, int]) -> bool:
    x, y = point
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def distance_sq_to_box_center(point: tuple[int, int], box: tuple[int, int, int, int]) -> int:
    center_x = (box[0] + box[2]) // 2
    center_y = (box[1] + box[3]) // 2
    return (point[0] - center_x) ** 2 + (point[1] - center_y) ** 2
