from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IconDetection:
    box: tuple[int, int, int, int]
    score: float


@dataclass(frozen=True)
class TextDetection:
    box: tuple[int, int, int, int]
    text: str
    score: float


@dataclass(frozen=True)
class ClickableElement:
    box: tuple[int, int, int, int]
    kind: str
    text: str
    score: float
    source: str = "vision"
    linked_tree_node_id: str | None = None
    class_name: str | None = None
    resource_id: str | None = None
    content_desc: str | None = None
    enabled: bool | None = None
    checked: bool | None = None
    selected: bool | None = None
    clickable: bool | None = None
    semantic_role: str | None = None
