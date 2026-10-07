from __future__ import annotations

import json

from munk_judge_local.tree_excerpt import (
    MAX_COMPACT_NODES,
    bound_json_payload,
    build_focus_compact_tree,
    select_focus_compact_nodes,
)


def test_select_focus_compact_nodes_keeps_focus_ancestors_and_caps() -> None:
    nodes = []
    for index in range(120):
        nodes.append(
            {
                "id": f"node-{index}",
                "pid": None if index == 0 else f"node-{(index - 1) // 2}",
                "txt": f"label-{index}",
            }
        )
    selected = select_focus_compact_nodes(
        nodes,
        focus_hits=[{"node_id": "node-90", "label": "label-90", "score": 3}],
        max_nodes=MAX_COMPACT_NODES,
    )
    selected_ids = {item["id"] for item in selected}
    assert "node-90" in selected_ids
    assert "node-0" in selected_ids
    assert len(selected) <= MAX_COMPACT_NODES


def test_build_focus_compact_tree_preserves_original_count_and_marks_truncated() -> None:
    compact_tree = {
        "node_count": 5,
        "focus_term_count": 2,
        "nodes": [
            {"id": "root", "pid": None, "txt": "Root"},
            {"id": "a", "pid": "root", "txt": "Alpha"},
            {"id": "b", "pid": "root", "txt": "Beta"},
            {"id": "c", "pid": "a", "txt": "Target"},
            {"id": "d", "pid": "b", "txt": "Other"},
        ],
    }
    excerpt = build_focus_compact_tree(
        compact_tree,
        focus_hits=[{"node_id": "c", "label": "Target", "score": 2}],
        max_nodes=3,
    )
    assert excerpt["node_count"] == 5
    assert excerpt["truncated"] is True
    assert excerpt["focus_term_count"] == 2
    assert [item["id"] for item in excerpt["nodes"]] == ["root", "a", "c"]


def test_bound_json_payload_marks_truncated_for_large_excerpt() -> None:
    payload = {
        "compact_tree": {
            "node_count": 100,
            "nodes": [{"id": f"n-{index}", "txt": "x" * 200} for index in range(100)],
        }
    }
    bounded = bound_json_payload(payload, max_chars=1_000)
    text = json.dumps(bounded, ensure_ascii=False, sort_keys=True)
    assert len(text) <= 1_000 or bounded.get("truncated") is True
    assert bounded.get("truncated") is True
