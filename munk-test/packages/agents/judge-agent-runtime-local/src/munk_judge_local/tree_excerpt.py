from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import cast

MAX_FOCUS_HITS = 6
MAX_COMPACT_NODES = 64
MAX_PRIMARY_EXCERPT_CHARS = 6_000
FALLBACK_NODE_COUNT = 12


def select_focus_compact_nodes(
    nodes: Sequence[Mapping[str, object]],
    *,
    focus_hits: Sequence[Mapping[str, object]] | None = None,
    max_nodes: int = MAX_COMPACT_NODES,
    max_focus_hits: int = MAX_FOCUS_HITS,
) -> list[dict[str, object]]:
    indexed = _index_nodes(nodes)
    if not indexed.ordered_ids:
        return []
    selected_ids = _select_focus_ids(
        indexed,
        focus_hits=focus_hits or [],
        max_nodes=max_nodes,
        max_focus_hits=max_focus_hits,
    )
    return [indexed.nodes_by_id[node_id] for node_id in indexed.ordered_ids if node_id in selected_ids]


def build_focus_compact_tree(
    compact_tree: Mapping[str, object],
    *,
    focus_hits: Sequence[Mapping[str, object]] | None = None,
    max_nodes: int = MAX_COMPACT_NODES,
) -> dict[str, object]:
    raw_nodes = compact_tree.get("nodes")
    nodes = [cast(dict[str, object], item) for item in raw_nodes if isinstance(item, Mapping)] if isinstance(raw_nodes, list) else []
    selected = select_focus_compact_nodes(nodes, focus_hits=focus_hits, max_nodes=max_nodes)
    original_count = compact_tree.get("node_count")
    if not isinstance(original_count, int):
        original_count = len(nodes)
    payload: dict[str, object] = {
        "node_count": original_count,
        "nodes": selected,
        "truncated": len(selected) < original_count,
    }
    focus_term_count = compact_tree.get("focus_term_count")
    if isinstance(focus_term_count, int):
        payload["focus_term_count"] = focus_term_count
    return payload


def bound_json_payload(payload: object, *, max_chars: int = MAX_PRIMARY_EXCERPT_CHARS) -> object:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    if len(text) <= max_chars:
        return payload
    if not isinstance(payload, dict):
        return _preview_payload(text, max_chars=max_chars)
    bounded = dict(payload)
    bounded["truncated"] = True
    bounded["approx_chars"] = len(text)
    compact_tree = bounded.get("compact_tree")
    if isinstance(compact_tree, dict):
        reduced = _reduce_compact_tree(compact_tree, max_chars=max_chars, outer=bounded)
        if reduced is not None:
            return reduced
    candidate = json.dumps(bounded, ensure_ascii=False, sort_keys=True, default=str)
    if len(candidate) <= max_chars:
        return bounded
    return _preview_payload(text, max_chars=max_chars)


def build_prompt_size_diagnostics(prompt_text: str, *, degraded: bool = False) -> dict[str, object]:
    prompt_chars = len(prompt_text)
    return {
        "prompt_chars": prompt_chars,
        "prompt_tokens_estimate": max(0, prompt_chars // 4),
        "degraded": degraded,
    }


class _IndexedNodes:
    def __init__(
        self,
        *,
        nodes_by_id: dict[str, dict[str, object]],
        parents: dict[str, str | None],
        ordered_ids: list[str],
    ) -> None:
        self.nodes_by_id = nodes_by_id
        self.parents = parents
        self.ordered_ids = ordered_ids


def _index_nodes(nodes: Sequence[Mapping[str, object]]) -> _IndexedNodes:
    nodes_by_id: dict[str, dict[str, object]] = {}
    parents: dict[str, str | None] = {}
    ordered_ids: list[str] = []
    for raw_node in nodes:
        node = dict(raw_node)
        node_id = _node_id(node)
        if not node_id:
            continue
        nodes_by_id[node_id] = node
        ordered_ids.append(node_id)
        parent_id = node.get("pid")
        parents[node_id] = str(parent_id) if parent_id is not None else None
    return _IndexedNodes(nodes_by_id=nodes_by_id, parents=parents, ordered_ids=ordered_ids)


def _select_focus_ids(
    indexed: _IndexedNodes,
    *,
    focus_hits: Sequence[Mapping[str, object]],
    max_nodes: int,
    max_focus_hits: int,
) -> set[str]:
    selected_ids = _collect_focus_ancestor_ids(indexed, focus_hits=focus_hits, max_focus_hits=max_focus_hits)
    if not selected_ids:
        selected_ids.update(indexed.ordered_ids[: min(len(indexed.ordered_ids), FALLBACK_NODE_COUNT)])
    if len(selected_ids) >= max_nodes:
        return _limit_selected_ids(indexed.ordered_ids, selected_ids, max_nodes=max_nodes)
    _expand_selected_children(indexed, selected_ids, max_nodes=max_nodes)
    return selected_ids


def _collect_focus_ancestor_ids(
    indexed: _IndexedNodes,
    *,
    focus_hits: Sequence[Mapping[str, object]],
    max_focus_hits: int,
) -> set[str]:
    selected_ids: set[str] = set()
    for hit in list(focus_hits)[:max_focus_hits]:
        node_id = _node_id(hit) or _string_or_none(hit.get("node_id"))
        if node_id is None or node_id not in indexed.nodes_by_id:
            continue
        current_id: str | None = node_id
        while current_id is not None and current_id not in selected_ids:
            selected_ids.add(current_id)
            current_id = indexed.parents.get(current_id)
    return selected_ids


def _limit_selected_ids(ordered_ids: Sequence[str], selected_ids: set[str], *, max_nodes: int) -> set[str]:
    limited: set[str] = set()
    for node_id in ordered_ids:
        if node_id in selected_ids:
            limited.add(node_id)
        if len(limited) >= max_nodes:
            break
    return limited


def _expand_selected_children(indexed: _IndexedNodes, selected_ids: set[str], *, max_nodes: int) -> None:
    for node_id in indexed.ordered_ids:
        if len(selected_ids) >= max_nodes:
            break
        if node_id in selected_ids:
            continue
        if indexed.parents.get(node_id) in selected_ids:
            selected_ids.add(node_id)


def _reduce_compact_tree(
    compact_tree: dict[str, object],
    *,
    max_chars: int,
    outer: dict[str, object],
) -> dict[str, object] | None:
    nodes = compact_tree.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return None
    reduced_tree = dict(compact_tree)
    keep = max(1, len(nodes) // 2)
    while keep > 0:
        reduced_tree["nodes"] = nodes[:keep]
        reduced_tree["truncated"] = True
        outer["compact_tree"] = reduced_tree
        candidate = json.dumps(outer, ensure_ascii=False, sort_keys=True, default=str)
        if len(candidate) <= max_chars:
            return outer
        keep //= 2
    reduced_tree["nodes"] = []
    outer["compact_tree"] = reduced_tree
    candidate = json.dumps(outer, ensure_ascii=False, sort_keys=True, default=str)
    return outer if len(candidate) <= max_chars else None


def _preview_payload(text: str, *, max_chars: int) -> dict[str, object]:
    return {
        "truncated": True,
        "approx_chars": len(text),
        "preview": text[: max(0, max_chars - 64)],
    }


def _node_id(item: Mapping[str, object]) -> str | None:
    for key in ("id", "node_id"):
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
