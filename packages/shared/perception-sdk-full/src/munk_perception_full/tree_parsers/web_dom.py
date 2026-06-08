from __future__ import annotations

import json

from ..tree_models import ParsedTreeNode


def parse_web_dom_snapshot(payload: str) -> list[ParsedTreeNode]:
    raw = json.loads(payload)
    if not isinstance(raw, dict):
        return []
    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list):
        return []
    nodes: list[ParsedTreeNode] = []
    for index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, dict):
            continue
        bounds = _parse_bounds(raw_node.get("bounds"))
        if bounds is None:
            continue
        text = _clean_text(raw_node.get("text"))
        name = _clean_text(raw_node.get("name"))
        tag_name = _clean_text(raw_node.get("tag_name"))
        role = _clean_text(raw_node.get("role"))
        semantic_role = _infer_semantic_role(role=role, tag_name=tag_name, clickable=bool(raw_node.get("clickable")))
        nodes.append(
            ParsedTreeNode(
                node_id=_clean_text(raw_node.get("node_id")) or f"node-{index}",
                bounds=bounds,
                class_name=tag_name,
                text=text,
                content_desc=name,
                resource_id=_clean_text(raw_node.get("resource_id")),
                clickable=bool(raw_node.get("clickable")),
                checkable=bool(raw_node.get("checkable")),
                checked=bool(raw_node.get("checked")),
                enabled=_coerce_bool(raw_node.get("enabled"), default=True),
                focused=bool(raw_node.get("focused")),
                selected=bool(raw_node.get("selected")),
                scrollable=bool(raw_node.get("scrollable")),
                semantic_role=semantic_role,
            )
        )
    return nodes


def filter_web_dom_nodes(
    nodes: list[ParsedTreeNode],
    screen_size: tuple[int, int],
) -> list[ParsedTreeNode]:
    screen_width, screen_height = screen_size
    kept: list[ParsedTreeNode] = []
    for node in nodes:
        if _box_area(node.bounds) <= 4:
            continue
        x1, y1, x2, y2 = node.bounds
        if x2 <= 0 or y2 <= 0 or x1 >= screen_width or y1 >= screen_height:
            continue
        if not (
            node.semantic_role
            or node.text
            or node.content_desc
            or node.resource_id
            or node.clickable
            or node.checkable
            or node.scrollable
        ):
            continue
        kept.append(node)
    return kept


def _parse_bounds(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    numbers = [_to_int(item) for item in value]
    if any(item is None for item in numbers):
        return None
    x1, y1, x2, y2 = numbers
    assert x1 is not None and y1 is not None and x2 is not None and y2 is not None
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2, y2)


def _to_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _coerce_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _infer_semantic_role(*, role: str | None, tag_name: str | None, clickable: bool) -> str | None:
    normalized_role = (role or "").strip().lower()
    if normalized_role in {"button", "checkbox", "switch", "tab", "textbox", "link"}:
        return {
            "textbox": "input",
            "link": "button" if clickable else "label",
        }.get(normalized_role, normalized_role)
    normalized_tag = (tag_name or "").strip().lower()
    if normalized_tag in {"button", "summary"}:
        return "button"
    if normalized_tag in {"input", "textarea", "select"}:
        return "input"
    if normalized_tag == "a":
        return "button" if clickable else "label"
    if clickable:
        return "button"
    return "label" if normalized_role or normalized_tag else None


def _box_area(box: tuple[int, int, int, int]) -> int:
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)
