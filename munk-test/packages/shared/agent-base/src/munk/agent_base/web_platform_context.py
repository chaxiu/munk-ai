from __future__ import annotations

import json
from collections.abc import Mapping
from typing import cast

from munk.device import CurrentAppState
from munk.perception import ObservationTree


def build_web_platform_context(
    *,
    app_info: CurrentAppState,
    observation_tree: ObservationTree | None,
) -> dict[str, object]:
    context: dict[str, object] = {
        "url": app_info.url,
        "title": app_info.title,
        "origin": app_info.raw.get("origin") or app_info.entry_identity,
        "surface_identity": app_info.surface_identity,
    }
    if observation_tree is None or observation_tree.source_type != "web_dom" or observation_tree.content_type != "json":
        return _compact_context(context)
    try:
        payload = json.loads(observation_tree.payload)
    except json.JSONDecodeError:
        return _compact_context(context)
    if not isinstance(payload, dict):
        return _compact_context(context)
    payload_dict = cast(dict[str, object], payload)
    raw_nodes = payload_dict.get("nodes")
    if not isinstance(raw_nodes, list):
        return _compact_context(context)
    raw_node_list = cast(list[object], raw_nodes)
    nodes: list[Mapping[str, object]] = []
    for raw_node in raw_node_list:
        if isinstance(raw_node, Mapping):
            nodes.append(cast(Mapping[str, object], raw_node))
    if not nodes:
        return _compact_context(context)
    context["dom_summary"] = _build_dom_summary(nodes)
    focused = _extract_focused_element(nodes)
    if focused is not None:
        context["focused_element"] = focused
    return _compact_context(context)


def format_web_page_meta(context: dict[str, object] | None) -> str:
    if not context:
        return "unavailable"
    return "\n".join(
        [
            f"title={_string_value(context.get('title'))}",
            f"url={_string_value(context.get('url'))}",
            f"origin={_string_value(context.get('origin'))}",
        ]
    )


def format_web_dom_summary(context: dict[str, object] | None) -> str:
    if not context:
        return "unavailable"
    summary = context.get("dom_summary")
    if isinstance(summary, str) and summary.strip():
        return summary
    return "unavailable"


def format_web_focused_element(context: dict[str, object] | None) -> str:
    if not context:
        return "none"
    focused = context.get("focused_element")
    if not isinstance(focused, dict):
        return "none"
    role = _string_value(focused.get("role"))
    label = _string_value(focused.get("label"))
    resource_id = _string_value(focused.get("resource_id"))
    return "\n".join(
        [
            f"role={role}",
            f"label={label}",
            f"resource_id={resource_id}",
        ]
    )


def _build_dom_summary(nodes: list[Mapping[str, object]]) -> str:
    clickable = sum(1 for node in nodes if node.get("clickable") is True)
    inputs = sum(
        1
        for node in nodes
        if _lower_text(node.get("role")) in {"textbox", "searchbox"}
        or _lower_text(node.get("tag_name")) in {"input", "textarea", "select"}
    )
    scrollable = sum(1 for node in nodes if node.get("scrollable") is True)
    labels = [_node_label(node) for node in nodes]
    unique_labels = [label for label in _dedupe_preserve_order(labels) if label][:3]
    parts = [
        f"nodes={len(nodes)}",
        f"clickable={clickable}",
        f"inputs={inputs}",
        f"scrollable={scrollable}",
    ]
    if unique_labels:
        parts.append(f"sample={', '.join(unique_labels)}")
    return "; ".join(parts)


def _extract_focused_element(nodes: list[Mapping[str, object]]) -> dict[str, str] | None:
    focused_nodes = [node for node in nodes if node.get("focused") is True]
    if not focused_nodes:
        return None
    node = max(focused_nodes, key=_focused_node_score)
    return {
        "role": _string_value(node.get("role") or node.get("tag_name")),
        "label": _node_label(node) or "unknown",
        "resource_id": _string_value(node.get("resource_id")),
    }


def _focused_node_score(node: Mapping[str, object]) -> tuple[int, int]:
    label = _node_label(node)
    return (1 if label else 0, len(label))


def _node_label(node: Mapping[str, object]) -> str:
    for key in ("text", "name", "resource_id", "tag_name"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _string_value(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _lower_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _compact_context(context: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in context.items() if value is not None}
