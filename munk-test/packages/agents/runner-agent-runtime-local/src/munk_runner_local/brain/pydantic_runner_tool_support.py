from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Literal, cast

from munk.agent_base.action.executor import (
    GESTURE_HORIZONTAL_EDGE_MARGIN_RATIO,
    GESTURE_VERTICAL_EDGE_MARGIN_RATIO,
)
from munk.agent_base.base import ScreenState

from munk_runner_local.brain.pydantic_runner_models import RunnerStepDeps
from munk_runner_local.brain.runner_view import (
    build_target_detail_text,
    build_targets_list_text,
    build_targets_text,
    resolve_action_target,
)

TERMINAL_TOOL_NAMES = (
    "click",
    "long_press",
    "edit_text",
    "set_value",
    "reveal_more",
    "swipe",
    "drag",
    "pull_to_refresh",
    "dismiss_soft_keyboard",
    "wait_for_text",
    "scroll_until_text",
    "back",
    "home",
    "restart_app",
    "wait",
    "redetect",
    "stop",
)
DEFAULT_TARGET_PART_LIMIT = 40
MAX_TARGET_PART_LIMIT = 200
DEFAULT_REVEAL_MORE_DISTANCE_RATIO = 0.35
DEFAULT_SWIPE_DISTANCE_RATIO = 0.35


@dataclass(frozen=True)
class ResolvedGestureAnchor:
    start_x_ratio: float
    start_y_ratio: float
    distance_ratio: float
    anchor_target: object | None = None


def build_screen_summary_text(screen: ScreenState) -> str:
    tree_summary = screen.screen_frame.tree_summary if screen.screen_frame is not None else "none"
    return "\n".join(
        [
            f"target_identity={screen.entry_identity or 'unknown'}",
            f"surface_identity={screen.surface_identity or 'unknown'}",
            f"screen_size={screen.screen_size[0]}x{screen.screen_size[1]}",
            f"elements={len(screen.elements)}",
            f"tree={tree_summary}",
        ]
    )


def build_clickable_elements_text(
    screen: ScreenState,
    limit: int,
    *,
    source: str = "all",
    offset: int = 0,
) -> str:
    return build_targets_list_text(screen, offset=offset, limit=limit, source=cast(Any, source))


def build_targets_seed_text(
    screen: ScreenState,
    max_elements: int,
    prompt_max_elements: int,
) -> str:
    return build_targets_text(
        screen,
        max_elements=max_elements,
        prompt_max_elements=prompt_max_elements,
    )


def build_target_detail_payload(
    deps: RunnerStepDeps,
    *,
    target_ref: str,
) -> str:
    return build_target_detail_text(
        deps.screen,
        target_ref=target_ref,
        max_elements=_canonical_target_part_limit(deps),
    )


def resolve_target_part_limit(limit: int | None = None) -> int:
    if limit is None:
        return DEFAULT_TARGET_PART_LIMIT
    return _validate_target_part_limit(limit)


def resolve_target(deps: RunnerStepDeps, target_ref: str) -> Any:
    return resolve_action_target(
        deps.screen,
        target_ref=target_ref,
        max_elements=_canonical_target_part_limit(deps),
    )


def resolve_reveal_more_gesture(
    deps: RunnerStepDeps,
    *,
    anchor_target_ref: str | None,
    direction: Literal["up", "down"],
    distance: float | None,
    start_y_ratio: float | None,
) -> ResolvedGestureAnchor:
    distance_ratio = distance if distance is not None else DEFAULT_REVEAL_MORE_DISTANCE_RATIO
    anchor_target = resolve_target(deps, anchor_target_ref) if anchor_target_ref is not None else None
    width, height = deps.screen.screen_size
    if width <= 0 or height <= 0:
        raise ValueError("screen_size must be positive for gesture actions")

    if anchor_target is None:
        resolved_start_y_ratio = start_y_ratio if start_y_ratio is not None else (0.75 if direction == "down" else 0.25)
        return ResolvedGestureAnchor(
            start_x_ratio=0.5,
            start_y_ratio=resolved_start_y_ratio,
            distance_ratio=distance_ratio,
        )

    x1, y1, x2, y2 = getattr(anchor_target, "box")
    center_x = (x1 + x2) / 2.0
    center_y = (y1 + y2) / 2.0
    x_ratio = _project_to_usable_ratio(center_x, width, GESTURE_HORIZONTAL_EDGE_MARGIN_RATIO)
    y_ratio = _project_to_usable_ratio(center_y, height, GESTURE_VERTICAL_EDGE_MARGIN_RATIO)
    resolved_start_y_ratio = start_y_ratio
    if resolved_start_y_ratio is None:
        if direction == "down":
            resolved_start_y_ratio = min(max(y_ratio, 0.45), 0.85)
        else:
            resolved_start_y_ratio = min(max(y_ratio, 0.15), 0.55)
    return ResolvedGestureAnchor(
        start_x_ratio=x_ratio,
        start_y_ratio=resolved_start_y_ratio,
        distance_ratio=distance_ratio,
        anchor_target=anchor_target,
    )


def resolve_swipe_gesture(
    deps: RunnerStepDeps,
    *,
    direction: Literal["left", "right"],
    distance: float | None,
    start_x_ratio: float | None,
) -> ResolvedGestureAnchor:
    width, height = deps.screen.screen_size
    if width <= 0 or height <= 0:
        raise ValueError("screen_size must be positive for gesture actions")
    return ResolvedGestureAnchor(
        start_x_ratio=start_x_ratio if start_x_ratio is not None else (0.75 if direction == "left" else 0.25),
        start_y_ratio=0.5,
        distance_ratio=distance if distance is not None else DEFAULT_SWIPE_DISTANCE_RATIO,
    )


def memory_payload_matches(
    existing_value: object,
    new_value: object,
    existing_summary: str,
    new_summary: str,
) -> bool:
    """Return True when a memory update would not change the stored payload."""
    if existing_summary.strip() != new_summary.strip():
        return False
    try:
        existing_canonical = json_dumps_canonical(existing_value)
        new_canonical = json_dumps_canonical(new_value)
    except (TypeError, ValueError):
        return existing_value == new_value
    return existing_canonical == new_canonical


def text_match_arguments(match: object, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"match": getattr(match, "model_dump")()}
    payload.update(extra)
    return payload


def target_arguments(arguments: dict[str, object], target: object) -> dict[str, object]:
    payload = dict(arguments)
    payload["target_ref"] = getattr(target, "ref", None) or payload.get("target_ref")
    payload["target_channel"] = getattr(target, "channel", None)
    payload["target_part"] = getattr(target, "part", None)
    payload["target_source"] = getattr(target, "source", None)
    payload["target_box"] = getattr(target, "box", None)
    if getattr(target, "linked_tree_node_id", None):
        payload["linked_tree_node_id"] = getattr(target, "linked_tree_node_id")
    if getattr(target, "stable_key", None):
        payload["target_stable_key"] = getattr(target, "stable_key")
    if getattr(target, "resource_id", None):
        payload["target_resource_id"] = getattr(target, "resource_id")
    if getattr(target, "reason", None):
        payload["target_reason"] = getattr(target, "reason")
    return payload


def json_dumps_canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _validate_target_part_limit(value: int) -> int:
    if value <= 0:
        raise ValueError("max must be positive")
    return min(value, MAX_TARGET_PART_LIMIT)


def _canonical_target_part_limit(deps: RunnerStepDeps) -> int:
    cached_parts = deps.screen.action_target_parts
    if cached_parts is None:
        return deps.max_elements
    return max(len(cached_parts.vision_targets), len(cached_parts.tree_targets), deps.max_elements)


def _project_to_usable_ratio(center_px: float, size_px: int, margin_ratio: float) -> float:
    if not math.isfinite(center_px):
        raise ValueError("gesture anchor center must be finite")
    min_px = size_px * margin_ratio
    max_px = size_px * (1.0 - margin_ratio)
    usable_px = max(max_px - min_px, 1.0)
    return min(max((center_px - min_px) / usable_px, 0.0), 1.0)
