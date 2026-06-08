from __future__ import annotations

from typing import Literal

from munk.agent_base.base import ScreenState
from munk.agent_base.platform_profile import get_runner_profile

from munk.core.action_targets import (
    VISION_PART_MAX,
    ActionTarget,
    build_action_targets,
    build_target_parts,
    resolve_action_target,
)

__all__ = [
    "build_action_targets",
    "build_target_detail_text",
    "build_targets_list_text",
    "build_targets_text",
    "count_targets_in_text",
    "resolve_action_target",
]


def build_targets_text(
    screen: ScreenState,
    max_elements: int,
    prompt_max_elements: int,
) -> str:
    _ = max_elements
    parts = build_target_parts(
        screen,
        vision_limit=min(max(prompt_max_elements, 0), VISION_PART_MAX),
        tree_limit=0,
    )
    if not parts.vision_targets:
        return "none"
    summary_lines = [
        "Use the integer after # as target_id for the seeded visible targets below.",
        f"vision_window={len(parts.vision_targets)}/{parts.vision_total} limit={min(max(prompt_max_elements, 0), VISION_PART_MAX)}",
    ]
    vision_truncated = max(parts.vision_total - len(parts.vision_targets), 0)
    if vision_truncated > 0:
        summary_lines.append(f"vision_truncated={vision_truncated}")
    vision_lines = [_format_target_line(target) for target in parts.vision_targets] or ["none"]
    return "\n".join(
        [
            *summary_lines,
            "",
            "[VISION_TARGETS]",
            *vision_lines,
            "",
            "tree_seed=omitted; use list_clickable_elements(source=tree) when structure-backed targets are needed",
        ]
    )


def build_targets_list_text(
    screen: ScreenState,
    *,
    max_elements: int,
    source: Literal["all", "vision", "tree"] = "all",
) -> str:
    parts = build_target_parts(
        screen,
        vision_limit=max(max_elements, 0),
        tree_limit=max(max_elements, 0),
    )
    include_vision = source in {"all", "vision"}
    include_tree = source in {"all", "tree"}
    visible_targets = [
        *(parts.vision_targets if include_vision else []),
        *(parts.tree_targets if include_tree else []),
    ]
    if not visible_targets:
        return "none"
    summary_lines: list[str] = []
    if source != "all":
        summary_lines.append(f"source={source}")
    if include_vision:
        summary_lines.append(f"vision_window={len(parts.vision_targets)}/{parts.vision_total} limit={max(max_elements, 0)}")
    vision_truncated = max(parts.vision_total - len(parts.vision_targets), 0)
    if include_vision and vision_truncated > 0:
        summary_lines.append(f"vision_truncated={vision_truncated}")
    if include_tree:
        summary_lines.append(f"tree_window={len(parts.tree_targets)}/{parts.tree_total} limit={max(max_elements, 0)}")
    tree_truncated = max(parts.tree_total - len(parts.tree_targets), 0)
    if include_tree and tree_truncated > 0:
        summary_lines.append(f"tree_truncated={tree_truncated}")
    sections: list[str] = [*summary_lines]
    if include_vision:
        vision_lines = [_format_target_line(target) for target in parts.vision_targets] or ["none"]
        sections.extend(["", "[VISION_TARGETS]", *vision_lines])
    if include_tree:
        tree_lines = [_format_target_line(target) for target in parts.tree_targets] or ["none"]
        sections.extend(["", "[TREE_TARGETS]", *tree_lines])
    return "\n".join(sections)


def build_target_detail_text(screen: ScreenState, *, target_id: int, max_elements: int) -> str:
    target = resolve_action_target(screen, target_id=target_id, max_elements=max_elements)
    return "\n".join([_format_target_line(target), *_format_target_detail_lines(target)])


def count_targets_in_text(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("#"))


def _format_target_line(target: ActionTarget) -> str:
    parts = [f"#{target.target_id}", _display_kind(target)]
    label = _display_label(target)
    if label is not None:
        parts.append(f'"{label}"')
    parts.extend(_format_inline_state_parts(target))
    parts.append(_format_box(target.box))
    return " ".join(parts)


def _format_target_detail_lines(target: ActionTarget) -> list[str]:
    details: list[str] = [f"part={target.part}"]
    for key, value in (
        ("source", target.source),
        ("reason", target.reason),
        ("linked_node_id", target.linked_tree_node_id),
        ("stable_key", target.stable_key),
        ("resource_id", target.resource_id),
        ("content_desc", target.content_desc),
        ("class_name", target.class_name),
        ("semantic_role", target.semantic_role),
    ):
        if _has_text(value):
            details.append(f"{key}={value}")
    if target.ocr_texts:
        details.append(f"ocr={_format_ocr_list(target.ocr_texts)}")
    return details


def _display_kind(target: ActionTarget) -> str:
    return _target_profile(target).display_kind(target)


def _display_label(target: ActionTarget) -> str | None:
    return _target_profile(target).display_label(target)
def _format_inline_state_parts(target: ActionTarget) -> list[str]:
    parts: list[str] = []
    display_kind = _display_kind(target)
    if display_kind == "input" and _has_text(target.text):
        parts.append(f'value="{str(target.text).strip()}"')
    if target.focused:
        parts.append("focused")
    if target.checked:
        parts.append("checked")
    if target.selected:
        parts.append("selected")
    if target.enabled is False:
        parts.append("disabled")
    if target.clickable is True and display_kind in {"text", "icon", "container", "visual", "label", "node"}:
        parts.append("clickable")
    if target.ocr_texts:
        parts.append(f"ocr={_format_ocr_list(target.ocr_texts)}")
    return parts


def _format_box(box: tuple[int, int, int, int]) -> str:
    return f"@{box[0]},{box[1]},{box[2]},{box[3]}"


def _target_profile(target: ActionTarget):
    return get_runner_profile(target.platform)


def _format_ocr_list(values: tuple[str, ...]) -> str:
    quoted = ", ".join(f'"{value}"' for value in values)
    return f"[{quoted}]"


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
