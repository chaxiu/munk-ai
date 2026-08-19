from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from munk.agent_base.base import ScreenState
from munk.agent_base.platform_profile import get_runner_profile
from munk.core.action_target_building import (
    build_canonical_target_parts,
    build_target_parts,
    select_form_first_tree_targets,
)
from munk.core.action_target_models import TREE_PART_MAX, VISION_PART_MAX, ActionTarget
from munk.core.action_target_resolution import resolve_action_target

DEFAULT_TARGET_PART_LIMIT = 40
MAX_TARGET_PART_LIMIT = 200
MATCH_TARGET_LIMIT = 15

TargetListSource = Literal["all", "vision", "tree"]

__all__ = [
    "DEFAULT_TARGET_PART_LIMIT",
    "MATCH_TARGET_LIMIT",
    "MAX_TARGET_PART_LIMIT",
    "TargetListSource",
    "TargetMatchTextResult",
    "TargetTextWindowStats",
    "build_target_detail_text",
    "build_targets_list_text",
    "build_targets_match_text",
    "build_targets_text",
    "clamp_target_part_limit",
    "count_targets_in_text",
    "default_tree_seed_limit",
    "measure_targets_list_window",
    "measure_targets_seed_window",
]


@dataclass(frozen=True)
class TargetTextWindowStats:
    total_vision: int
    total_tree: int
    returned_vision: int
    returned_tree: int
    truncated: bool
    next_offset: int | None = None


@dataclass(frozen=True)
class TargetMatchTextResult:
    query: str
    matched_count: int
    match_text: str


def build_targets_text(
    screen: ScreenState,
    max_elements: int,
    prompt_max_elements: int,
) -> str:
    _ = max_elements
    vision_limit = min(max(prompt_max_elements, 0), VISION_PART_MAX)
    tree_limit = default_tree_seed_limit(screen)
    parts = build_target_parts(
        screen,
        vision_limit=vision_limit,
        tree_limit=0 if tree_limit == 0 else TREE_PART_MAX,
    )
    vision_targets = parts.vision_targets
    tree_targets = (
        select_form_first_tree_targets(parts.tree_targets, limit=tree_limit)
        if tree_limit > 0
        else []
    )
    if not vision_targets and not tree_targets:
        return "none"
    summary_lines = [
        "Use target_ref exactly as shown (v1, t2, …). Do not use flat integers.",
        "Prefer #t* for native inputs/selects/date/time. Use set_value for structured value setting; edit_text only for text input.",
        "Use #v* for icons/custom visuals.",
        "box=[left,top,right,bottom] in screen pixels.",
        f"vision_window={len(vision_targets)}/{parts.vision_total} limit={vision_limit}",
    ]
    vision_truncated = max(parts.vision_total - len(vision_targets), 0)
    if vision_truncated > 0:
        summary_lines.append(f"vision_truncated={vision_truncated}")
    vision_lines = [_format_seed_target_line(target) for target in vision_targets] or ["none"]
    sections: list[str] = [*summary_lines, "", "[VISION]", *vision_lines]
    if tree_limit > 0:
        tree_summary_lines = [
            "Seed [TREE] may reorder form controls first within the window; list_clickable_elements uses canonical order; tN identity is unchanged.",
            f"tree_window={len(tree_targets)}/{parts.tree_total} limit={tree_limit} form_first=true",
        ]
        tree_truncated = max(parts.tree_total - len(tree_targets), 0)
        if tree_truncated > 0:
            tree_summary_lines.append(f"tree_truncated={tree_truncated}")
        tree_lines = [_format_seed_target_line(target) for target in tree_targets] or ["none"]
        sections.extend(
            [
                "",
                *tree_summary_lines,
                "",
                "[TREE]",
                *tree_lines,
            ]
        )
    else:
        sections.extend(
            [
                "",
                "tree_seed=omitted; use list_clickable_elements(source=tree, offset=0, limit=40) for the first tree page, then advance with next_offset when structure-backed targets are needed",
            ]
        )
    return "\n".join(sections)


def build_targets_list_text(
    screen: ScreenState,
    *,
    offset: int,
    limit: int,
    source: TargetListSource = "all",
) -> str:
    parts = build_canonical_target_parts(screen)
    include_vision = source in {"all", "vision"}
    include_tree = source in {"all", "tree"}
    visible_targets = [
        *(_window_targets(parts.vision_targets, offset=offset, limit=limit) if include_vision else []),
        *(_window_targets(parts.tree_targets, offset=offset, limit=limit) if include_tree else []),
    ]
    if not visible_targets:
        return "none"
    summary_lines: list[str] = [f"source={source}", f"offset={max(offset, 0)}", f"limit={max(limit, 0)}"]
    summary_lines.append("Use target_ref values such as v1 or t2.")
    summary_lines.append("box=[left,top,right,bottom] in screen pixels.")
    if include_vision:
        summary_lines.extend(_format_window_summary("vision", parts.vision_targets, offset=offset, limit=limit))
    if include_tree:
        summary_lines.extend(_format_window_summary("tree", parts.tree_targets, offset=offset, limit=limit))
    sections: list[str] = [*summary_lines]
    if include_vision:
        vision_lines = [
            _format_full_target_line(target)
            for target in _window_targets(parts.vision_targets, offset=offset, limit=limit)
        ] or ["none"]
        sections.extend(["", "[VISION]", *vision_lines])
    if include_tree:
        tree_lines = [
            _format_full_target_line(target)
            for target in _window_targets(parts.tree_targets, offset=offset, limit=limit)
        ] or ["none"]
        sections.extend(["", "[TREE]", *tree_lines])
    return "\n".join(sections)


def build_target_detail_text(screen: ScreenState, *, target_ref: str, max_elements: int) -> str:
    target = resolve_action_target(screen, target_ref=target_ref, max_elements=max_elements)
    return "\n".join([_format_full_target_line(target), *_format_target_detail_lines(target)])


def build_targets_match_text(
    screen: ScreenState,
    query: str,
    *,
    limit: int = MATCH_TARGET_LIMIT,
) -> TargetMatchTextResult:
    normalized_query = str(query).strip()
    resolved_limit = min(max(int(limit), 0), MATCH_TARGET_LIMIT)
    if not normalized_query or resolved_limit == 0:
        return TargetMatchTextResult(query=normalized_query, matched_count=0, match_text="none")
    needle = normalized_query.casefold()
    parts = build_canonical_target_parts(screen)
    matched: list[ActionTarget] = []
    for target in [*parts.vision_targets, *parts.tree_targets]:
        if not _target_matches_query(target, needle):
            continue
        matched.append(target)
        if len(matched) >= resolved_limit:
            break
    if not matched:
        return TargetMatchTextResult(query=normalized_query, matched_count=0, match_text="none")
    match_text = "\n".join(_format_full_target_line(target) for target in matched)
    return TargetMatchTextResult(
        query=normalized_query,
        matched_count=len(matched),
        match_text=match_text,
    )


def count_targets_in_text(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("#"))


def default_tree_seed_limit(screen: ScreenState) -> int:
    profile = get_runner_profile(screen.platform)
    return min(TREE_PART_MAX, max(profile.default_tree_seed_limit, 0))


def clamp_target_part_limit(value: int | None) -> int:
    if value is None:
        return DEFAULT_TARGET_PART_LIMIT
    return min(max(int(value), 0), MAX_TARGET_PART_LIMIT)


def measure_targets_seed_window(
    screen: ScreenState,
    *,
    prompt_max_elements: int = VISION_PART_MAX,
) -> TargetTextWindowStats:
    vision_limit = min(max(prompt_max_elements, 0), VISION_PART_MAX)
    tree_limit = default_tree_seed_limit(screen)
    parts = build_target_parts(
        screen,
        vision_limit=vision_limit,
        tree_limit=0 if tree_limit == 0 else TREE_PART_MAX,
    )
    returned_vision = len(parts.vision_targets)
    returned_tree = (
        len(select_form_first_tree_targets(parts.tree_targets, limit=tree_limit))
        if tree_limit > 0
        else 0
    )
    return TargetTextWindowStats(
        total_vision=parts.vision_total,
        total_tree=parts.tree_total,
        returned_vision=returned_vision,
        returned_tree=returned_tree,
        truncated=returned_vision < parts.vision_total or returned_tree < parts.tree_total,
    )


def measure_targets_list_window(
    screen: ScreenState,
    *,
    offset: int,
    limit: int,
    source: TargetListSource = "all",
) -> TargetTextWindowStats:
    parts = build_canonical_target_parts(screen)
    include_vision = source in {"all", "vision"}
    include_tree = source in {"all", "tree"}
    vision_window = (
        _window_targets(parts.vision_targets, offset=offset, limit=limit) if include_vision else []
    )
    tree_window = _window_targets(parts.tree_targets, offset=offset, limit=limit) if include_tree else []
    total_vision = parts.vision_total if include_vision else 0
    total_tree = parts.tree_total if include_tree else 0
    returned_vision = len(vision_window)
    returned_tree = len(tree_window)
    vision_has_more = include_vision and max(offset, 0) + returned_vision < total_vision
    tree_has_more = include_tree and max(offset, 0) + returned_tree < total_tree
    truncated = vision_has_more or tree_has_more
    next_offset: int | None = None
    if truncated:
        next_candidates = [
            max(offset, 0) + returned_vision if vision_has_more else None,
            max(offset, 0) + returned_tree if tree_has_more else None,
        ]
        next_offset = min(value for value in next_candidates if value is not None)
    return TargetTextWindowStats(
        total_vision=total_vision,
        total_tree=total_tree,
        returned_vision=returned_vision,
        returned_tree=returned_tree,
        truncated=truncated,
        next_offset=next_offset,
    )


def _target_matches_query(target: ActionTarget, needle: str) -> bool:
    """Match against display-facing identity fields (not raw Android package-qualified ids)."""
    candidates: list[object] = [
        _display_label(target),
        target.text,
        target.content_desc,
        _display_resource_id(target),
        target.test_id,
        target.dom_name,
        target.kind,
        _display_kind(target),
        target.input_type,
        *target.ocr_texts,
    ]
    for value in candidates:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized:
            continue
        if needle in normalized.casefold():
            return True
    return False


def _format_seed_target_line(target: ActionTarget) -> str:
    ref = target.ref or f"{target.channel}{target.index}" or str(target.target_id)
    parts = [f"#{ref}", _display_kind(target)]
    label = _seed_display_label(target)
    resource_id = _display_resource_id(target)
    if label is not None and label != resource_id:
        parts.append(f'"{label}"')
    if resource_id is not None:
        parts.append(f"resource_id={resource_id}")
    parts.extend(_format_inline_state_parts(target, include_value=False, include_ocr=False))
    parts.append(_format_box(target.box))
    return " ".join(parts)


def _format_full_target_line(target: ActionTarget) -> str:
    ref = target.ref or f"{target.channel}{target.index}" or str(target.target_id)
    parts = [f"#{ref}", _display_kind(target)]
    label = _display_label(target)
    if label is not None:
        parts.append(f'"{label}"')
    parts.extend(_format_inline_state_parts(target, include_value=True, include_ocr=True))
    parts.append(_format_box(target.box))
    return " ".join(parts)


def _format_target_detail_lines(target: ActionTarget) -> list[str]:
    details: list[str] = [
        f"ref={target.ref or 'unknown'}",
        f"channel={target.channel}",
        f"part={target.part}",
    ]
    for key, value in (
        ("source", target.source),
        ("reason", target.reason),
        ("linked_node_id", target.linked_tree_node_id),
        ("stable_key", target.stable_key),
        ("resource_id", target.resource_id),
        ("content_desc", target.content_desc),
        ("class_name", target.class_name),
        ("semantic_role", target.semantic_role),
        ("input_type", target.input_type),
        ("dom_name", target.dom_name),
        ("dom_value", target.dom_value),
        ("test_id", target.test_id),
    ):
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        details.append(f"{key}={value}")
    if target.handle is not None:
        details.append(f"handle_kind={target.handle.kind}")
        if target.handle.fill_mode:
            details.append(f"fill_mode={target.handle.fill_mode}")
    if target.ocr_texts:
        details.append(f"ocr={_format_ocr_list(target.ocr_texts)}")
    return details


def _display_kind(target: ActionTarget) -> str:
    return _target_profile(target).display_kind(target)


def _display_label(target: ActionTarget) -> str | None:
    if target.label and target.part == "tree" and target.platform == "web":
        return target.label
    return _target_profile(target).display_label(target)


def _seed_display_label(target: ActionTarget) -> str | None:
    label = _display_label(target)
    if label is None:
        return None
    class_name = str(target.class_name or "").strip()
    if class_name and label == class_name and _is_generic_container_class(class_name):
        return None
    return label


def _display_resource_id(target: ActionTarget) -> str | None:
    resource_id = str(target.resource_id or "").strip()
    if not resource_id:
        return None
    return (
        _target_profile(target)._android_resource_id_label(resource_id)
        if target.platform == "android"
        else resource_id
    )


def _format_inline_state_parts(  # noqa: C901
    target: ActionTarget,
    *,
    include_value: bool,
    include_ocr: bool,
) -> list[str]:
    parts: list[str] = []
    display_kind = _display_kind(target)
    if include_value and display_kind == "input":
        if target.dom_value is not None:
            parts.append(f'value="{str(target.dom_value)}"')
        elif _has_text(target.text):
            parts.append(f'value="{str(target.text).strip()}"')
    if target.input_type:
        parts.append(f"type={target.input_type}")
    if target.focused:
        parts.append("focused")
    if target.checked:
        parts.append("checked")
    if target.selected:
        parts.append("selected")
    if target.enabled is False:
        parts.append("disabled")
    if target.clickable is True and display_kind in {
        "text",
        "icon",
        "container",
        "visual",
        "label",
        "node",
    }:
        parts.append("clickable")
    if include_ocr and target.ocr_texts:
        parts.append(f"ocr={_format_ocr_list(target.ocr_texts)}")
    return parts


def _window_targets(targets: list[ActionTarget], *, offset: int, limit: int) -> list[ActionTarget]:
    normalized_offset = max(offset, 0)
    normalized_limit = max(limit, 0)
    if normalized_limit == 0:
        return []
    return targets[normalized_offset : normalized_offset + normalized_limit]


def _format_window_summary(kind: str, targets: list[ActionTarget], *, offset: int, limit: int) -> list[str]:
    total = len(targets)
    window_targets = _window_targets(targets, offset=offset, limit=limit)
    has_more = max(offset, 0) + len(window_targets) < total
    window_value = _format_window_value(total=total, offset=offset, count=len(window_targets))
    lines = [f"{kind}_window={window_value}", f"{kind}_has_more={str(has_more).lower()}"]
    if has_more:
        lines.append(f"{kind}_next_offset={max(offset, 0) + len(window_targets)}")
    return lines


def _format_window_value(*, total: int, offset: int, count: int) -> str:
    if total <= 0 or count <= 0:
        return f"none/{max(total, 0)}"
    start = max(offset, 0) + 1
    end = max(offset, 0) + count
    return f"{start}-{end}/{total}"


def _format_box(box: tuple[int, int, int, int]) -> str:
    return f"box=[{box[0]},{box[1]},{box[2]},{box[3]}]"


def _target_profile(target: ActionTarget):
    return get_runner_profile(target.platform)


def _format_ocr_list(values: tuple[str, ...]) -> str:
    quoted = ", ".join(f'"{value}"' for value in values)
    return f"[{quoted}]"


def _is_generic_container_class(value: str) -> bool:
    normalized = value.strip()
    return normalized in {
        "android.widget.FrameLayout",
        "android.widget.LinearLayout",
        "android.widget.RelativeLayout",
        "android.widget.ConstraintLayout",
        "android.view.View",
        "android.view.ViewGroup",
    }


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
