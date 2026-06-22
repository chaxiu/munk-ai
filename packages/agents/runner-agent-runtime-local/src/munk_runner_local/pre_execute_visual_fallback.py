from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import cv2
import numpy as np

from munk.agent_base.action import ActionType
from munk.core.action_targets import ActionTarget
from munk.perception.image import BgrImage

from .pre_execute_target_matcher import has_reliable_target_label

VISUAL_FALLBACK_MATCH_STRATEGY = "visual_icon_fallback"
VISUAL_FALLBACK_SEARCH_PADDING_FACTOR = 2.0
VISUAL_FALLBACK_MIN_TEMPLATE_SIDE = 8
VISUAL_FALLBACK_MAX_TEMPLATE_SIDE_RATIO = 0.5
VISUAL_FALLBACK_MIN_TEMPLATE_STDDEV = 10.0
VISUAL_FALLBACK_MIN_SCORE = 0.92
VISUAL_FALLBACK_MIN_SECOND_BEST_GAP = 0.05
VISUAL_FALLBACK_MAX_SHIFT_RATIO = 0.25


@dataclass(frozen=True)
class VisualFallbackResult:
    matched_box: tuple[int, int, int, int] | None
    match_strategy: str | None = None
    stale_reason: str | None = None


def should_try_visual_fallback(*, original_target: ActionTarget, action_type: ActionType) -> bool:
    if action_type not in {ActionType.CLICK, ActionType.LONG_PRESS}:
        return False
    if original_target.part != "vision":
        return False
    if _has_text(original_target.stable_key) or _has_text(original_target.resource_id):
        return False
    if _has_text(original_target.linked_tree_node_id):
        return False
    if has_reliable_target_label(original_target):
        return False
    if _normalized_token(original_target.kind) == "text":
        return False
    return True


def match_visual_fallback_box(
    *,
    original_target: ActionTarget,
    previous_image: BgrImage,
    current_image: BgrImage,
) -> VisualFallbackResult:
    previous_height, previous_width = previous_image.shape[:2]
    current_height, current_width = current_image.shape[:2]
    template_box = _clip_box(original_target.box, width=previous_width, height=previous_height)
    if template_box is None:
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_template_out_of_bounds")
    template = previous_image[template_box[1] : template_box[3], template_box[0] : template_box[2]]
    template_height, template_width = template.shape[:2]
    if min(template_width, template_height) < VISUAL_FALLBACK_MIN_TEMPLATE_SIDE:
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_template_too_small")
    if (
        template_width > current_width * VISUAL_FALLBACK_MAX_TEMPLATE_SIDE_RATIO
        or template_height > current_height * VISUAL_FALLBACK_MAX_TEMPLATE_SIDE_RATIO
    ):
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_template_too_large")
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    if float(np.std(gray_template)) < VISUAL_FALLBACK_MIN_TEMPLATE_STDDEV:
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_template_low_information")
    search_box = _expand_search_box(
        template_box,
        width=current_width,
        height=current_height,
        padding=int(round(max(template_width, template_height) * VISUAL_FALLBACK_SEARCH_PADDING_FACTOR)),
    )
    search_region = current_image[search_box[1] : search_box[3], search_box[0] : search_box[2]]
    if search_region.shape[0] < template_height or search_region.shape[1] < template_width:
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_search_region_too_small")
    gray_search_region = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
    result_map = cv2.matchTemplate(gray_search_region, gray_template, cv2.TM_CCOEFF_NORMED)
    _, best_score, _, best_location = cv2.minMaxLoc(result_map)
    best_location_tuple = (int(best_location[0]), int(best_location[1]))
    second_best_score = _second_best_score(
        result_map,
        best_location_tuple,
        template_width=template_width,
        template_height=template_height,
    )
    matched_box = (
        search_box[0] + best_location_tuple[0],
        search_box[1] + best_location_tuple[1],
        search_box[0] + best_location_tuple[0] + template_width,
        search_box[1] + best_location_tuple[1] + template_height,
    )
    if float(best_score) < VISUAL_FALLBACK_MIN_SCORE:
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_score_too_low")
    if _has_multiple_strong_peaks(result_map, best_score=float(best_score)):
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_ambiguous_match")
    if float(best_score) - float(second_best_score) < VISUAL_FALLBACK_MIN_SECOND_BEST_GAP:
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_ambiguous_match")
    if _normalized_center_distance(template_box, matched_box, screen_size=(current_width, current_height)) > VISUAL_FALLBACK_MAX_SHIFT_RATIO:
        return VisualFallbackResult(matched_box=None, stale_reason="visual_fallback_match_too_far")
    return VisualFallbackResult(
        matched_box=matched_box,
        match_strategy=VISUAL_FALLBACK_MATCH_STRATEGY,
    )


def _second_best_score(
    result_map: np.ndarray,
    best_location: tuple[int, int],
    *,
    template_width: int,
    template_height: int,
) -> float:
    suppressed = cast(np.ndarray, result_map.copy())
    left = max(int(best_location[0]) - max(template_width // 2, 1), 0)
    top = max(int(best_location[1]) - max(template_height // 2, 1), 0)
    right = min(int(best_location[0]) + max(template_width // 2, 1) + 1, suppressed.shape[1])
    bottom = min(int(best_location[1]) + max(template_height // 2, 1) + 1, suppressed.shape[0])
    suppressed[top:bottom, left:right] = -1.0
    if suppressed.size == 0:
        return -1.0
    return float(np.max(suppressed))


def _has_multiple_strong_peaks(result_map: np.ndarray, *, best_score: float) -> bool:
    strong_peak_threshold = max(best_score - VISUAL_FALLBACK_MIN_SECOND_BEST_GAP, VISUAL_FALLBACK_MIN_SCORE)
    strong_peaks = (result_map >= strong_peak_threshold).astype(np.uint8)
    component_count, _ = cv2.connectedComponents(strong_peaks)
    return component_count > 2


def _expand_search_box(
    box: tuple[int, int, int, int],
    *,
    width: int,
    height: int,
    padding: int,
) -> tuple[int, int, int, int]:
    return (
        max(0, box[0] - padding),
        max(0, box[1] - padding),
        min(width, box[2] + padding),
        min(height, box[3] + padding),
    )


def _clip_box(
    box: tuple[int, int, int, int],
    *,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    left = max(0, min(width, box[0]))
    top = max(0, min(height, box[1]))
    right = max(0, min(width, box[2]))
    bottom = max(0, min(height, box[3]))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


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


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized_token(value: object) -> str:
    return str(value or "").strip().lower()
