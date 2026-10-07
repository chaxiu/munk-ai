import json

from munk_perception_full.tree_parsers.web_dom import filter_web_dom_nodes, parse_web_dom_snapshot


def test_parse_web_dom_snapshot_extracts_structured_nodes() -> None:
    payload = json.dumps(
        {
            "format_version": 1,
            "url": "https://example.com/docs",
            "title": "Docs",
            "nodes": [
                {
                    "node_id": "node-0",
                    "bounds": [100, 40, 220, 84],
                    "tag_name": "button",
                    "role": "button",
                    "text": "Docs",
                    "name": "Docs",
                    "resource_id": "docs",
                    "clickable": True,
                    "checkable": False,
                    "checked": False,
                    "enabled": True,
                    "focused": False,
                    "selected": False,
                    "scrollable": False,
                }
            ],
        }
    )

    nodes = parse_web_dom_snapshot(payload)

    assert len(nodes) == 1
    assert nodes[0].class_name == "button"
    assert nodes[0].semantic_role == "button"
    assert nodes[0].content_desc == "Docs"


def test_filter_web_dom_nodes_keeps_semantic_or_interactive_nodes() -> None:
    nodes = parse_web_dom_snapshot(
        json.dumps(
            {
                "format_version": 1,
                "nodes": [
                    {
                        "node_id": "node-0",
                        "bounds": [0, 0, 1, 1],
                        "tag_name": "div",
                        "role": None,
                        "text": None,
                        "name": None,
                        "resource_id": None,
                        "clickable": False,
                        "checkable": False,
                        "checked": False,
                        "enabled": True,
                        "focused": False,
                        "selected": False,
                        "scrollable": False,
                    },
                    {
                        "node_id": "node-1",
                        "bounds": [10, 10, 120, 48],
                        "tag_name": "a",
                        "role": "link",
                        "text": "Docs",
                        "name": "Docs",
                        "resource_id": "docs",
                        "clickable": True,
                        "checkable": False,
                        "checked": False,
                        "enabled": True,
                        "focused": False,
                        "selected": False,
                        "scrollable": False,
                    },
                ],
            }
        )
    )

    filtered = filter_web_dom_nodes(nodes, (1440, 900))

    assert [node.node_id for node in filtered] == ["node-1"]
