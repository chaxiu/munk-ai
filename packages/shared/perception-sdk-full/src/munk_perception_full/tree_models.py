from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedTreeNode:
    node_id: str
    bounds: tuple[int, int, int, int]
    package_name: str | None = None
    class_name: str | None = None
    text: str | None = None
    content_desc: str | None = None
    resource_id: str | None = None
    clickable: bool = False
    checkable: bool = False
    checked: bool = False
    enabled: bool = True
    focused: bool = False
    selected: bool = False
    scrollable: bool = False
    semantic_role: str | None = None


def summarize_tree_nodes(nodes: list[ParsedTreeNode]) -> str:
    if not nodes:
        return "none"
    parts: list[str] = []
    clickable_count = sum(1 for node in nodes if node.clickable)
    checkable_count = sum(1 for node in nodes if node.checkable)
    scrollable_count = sum(1 for node in nodes if node.scrollable)
    parts.append(f"nodes={len(nodes)}")
    if clickable_count:
        parts.append(f"clickable={clickable_count}")
    if checkable_count:
        parts.append(f"checkable={checkable_count}")
    if scrollable_count:
        parts.append(f"scrollable={scrollable_count}")
    labels = [_node_label(node) for node in nodes[:3]]
    labels = [label for label in labels if label]
    if labels:
        parts.append(f"sample={', '.join(labels)}")
    return "; ".join(parts)


def filter_parsed_tree_nodes(
    nodes: list[ParsedTreeNode],
    screen_size: tuple[int, int],
) -> list[ParsedTreeNode]:
    screen_width, screen_height = screen_size
    screen_area = max(1, screen_width * screen_height)
    kept: list[ParsedTreeNode] = []
    for node in nodes:
        area = _box_area(node.bounds)
        if area <= 4:
            continue
        if area >= int(screen_area * 0.98) and not _has_semantics(node):
            continue
        if not (_has_semantics(node) or _has_action_value(node) or _has_interesting_class(node.class_name)):
            continue
        kept.append(node)
    return kept


def _box_area(box: tuple[int, int, int, int]) -> int:
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def _has_semantics(node: ParsedTreeNode) -> bool:
    return any([node.text, node.content_desc, node.resource_id, node.semantic_role])


def _has_action_value(node: ParsedTreeNode) -> bool:
    return any(
        [
            node.clickable,
            node.checkable,
            node.checked,
            node.scrollable,
            node.focused,
            node.selected,
        ]
    )


def _has_interesting_class(class_name: str | None) -> bool:
    class_text = (class_name or "").lower()
    return any(
        token in class_text
        for token in (
            "button",
            "checkbox",
            "switch",
            "radio",
            "input",
            "textfield",
            "edittext",
            "tab",
            "link",
        )
    )


def _node_label(node: ParsedTreeNode) -> str:
    return (node.text or node.content_desc or node.resource_id or node.semantic_role or "").strip()
