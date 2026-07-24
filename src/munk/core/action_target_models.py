from __future__ import annotations

from dataclasses import dataclass

VISION_PART_MAX = 40
TREE_PART_MAX = 40


@dataclass(frozen=True)
class ActionTarget:
    target_id: int
    part: str
    source: str
    box: tuple[int, int, int, int]
    kind: str | None = None
    text: str | None = None
    resource_id: str | None = None
    content_desc: str | None = None
    class_name: str | None = None
    semantic_role: str | None = None
    enabled: bool | None = None
    checked: bool | None = None
    selected: bool | None = None
    clickable: bool | None = None
    focused: bool | None = None
    linked_tree_node_id: str | None = None
    stable_key: str | None = None
    label: str | None = None
    reason: str | None = None
    ocr_texts: tuple[str, ...] = ()
    platform: str | None = None


@dataclass(frozen=True)
class TargetParts:
    vision_targets: list[ActionTarget]
    tree_targets: list[ActionTarget]
    vision_total: int
    tree_total: int
    is_canonical_snapshot: bool = False


@dataclass(frozen=True)
class ActionTargetResolution:
    resolved_target: ActionTarget | None
    candidates: list[ActionTarget]
    confidence: float | None
    warnings: list[str]
