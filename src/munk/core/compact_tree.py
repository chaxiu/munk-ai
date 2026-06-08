from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from munk.agent_base.platform_profile import get_runner_profile
from munk.core.screen_graph import TreeNodeSnapshot


def build_compact_tree(
    raw_nodes: object,
    *,
    tree_parent_map: Mapping[str, str | None] | None = None,
    platform: str | None = None,
) -> dict[str, object]:
    if not isinstance(raw_nodes, Sequence) or isinstance(raw_nodes, (str, bytes, bytearray)):
        return {"node_count": 0, "nodes": []}
    nodes: list[dict[str, object]] = []
    for raw_item in raw_nodes:
        compact = compact_tree_node(raw_item, tree_parent_map=tree_parent_map, platform=platform)
        if compact is not None:
            nodes.append(compact)
    return {
        "node_count": len(nodes),
        "nodes": nodes,
    }


def compact_tree_node(
    raw_item: object,
    *,
    tree_parent_map: Mapping[str, str | None] | None = None,
    platform: str | None = None,
) -> dict[str, object] | None:
    node = _normalize_tree_node(raw_item)
    if node is None:
        return None
    node_id = str(node.get("node_id") or "")
    payload: dict[str, object] = {
        "id": node_id,
        "sk": node.get("stable_key"),
        "pid": (tree_parent_map or {}).get(node_id),
        "cls": node.get("class_name"),
        "rid": node.get("resource_id"),
        "txt": node.get("text"),
        "cd": node.get("content_desc"),
        "b": node.get("bounds"),
    }
    state = sparse_state_fields(node, platform=platform)
    if state:
        payload["state"] = state
    role = node.get("semantic_role")
    if role:
        payload["role"] = role
    matched_visual_ids = node.get("matched_visual_ids")
    if isinstance(matched_visual_ids, list) and matched_visual_ids:
        payload["visual_ids"] = list(matched_visual_ids)
    return payload


def sparse_state_fields(raw_item: object, *, platform: str | None = None) -> dict[str, object]:
    node = _normalize_tree_node(raw_item)
    if node is None:
        return {}
    return get_runner_profile(platform).compact_state(node)


def compact_node_label(node: Mapping[str, object]) -> str | None:
    for key in ("txt", "cd", "rid", "role", "cls", "id"):
        value = node.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def index_compact_tree_nodes(compact_tree: Mapping[str, object]) -> dict[str, dict[str, object]]:
    raw_nodes = compact_tree.get("nodes")
    if not isinstance(raw_nodes, list):
        return {}
    indexed: dict[str, dict[str, object]] = {}
    for raw_item in raw_nodes:
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, object], raw_item)
        node_id = item.get("id")
        if node_id is None:
            continue
        indexed[str(node_id)] = item
    return indexed


def _normalize_tree_node(raw_item: object) -> dict[str, object] | None:
    if isinstance(raw_item, TreeNodeSnapshot):
        return {
            "node_id": raw_item.node_id,
            "stable_key": raw_item.stable_key,
            "bounds": list(raw_item.bounds),
            "package_name": raw_item.package_name,
            "text": raw_item.text,
            "content_desc": raw_item.content_desc,
            "resource_id": raw_item.resource_id,
            "class_name": raw_item.class_name,
            "clickable": raw_item.clickable,
            "checkable": raw_item.checkable,
            "checked": raw_item.checked,
            "enabled": raw_item.enabled,
            "focused": raw_item.focused,
            "selected": raw_item.selected,
            "scrollable": raw_item.scrollable,
            "semantic_role": raw_item.semantic_role,
            "matched_visual_ids": list(raw_item.matched_visual_ids),
        }
    if isinstance(raw_item, dict):
        return cast(dict[str, object], raw_item)
    return None
