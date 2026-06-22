import json

from munk_perception_full.tree_parsers.ios_ax_tree import filter_ios_ax_tree_nodes, parse_ios_ax_tree


def _sample_tree(*, wrapped: bool) -> str:
    root = {
        "type": "XCUIElementTypeApplication",
        "name": "Demo",
        "bundleId": "com.example.demo",
        "children": [
            {
                "type": "XCUIElementTypeButton",
                "name": "Continue",
                "label": "Continue",
                "rect": {"x": 10, "y": 20, "width": 100, "height": 44},
                "enabled": True,
            },
            {
                "type": "XCUIElementTypeSwitch",
                "name": "Dark Mode",
                "label": "Dark Mode",
                "value": "1",
                "rect": {"x": 12, "y": 90, "width": 52, "height": 32},
                "enabled": True,
            },
            {
                "type": "XCUIElementTypeKeyboard",
                "nativeFrame": "{{0, 1900}, {1179, 656}}",
            },
            {
                "type": "XCUIElementTypeOther",
                "rect": {"x": 0, "y": 0, "width": 2, "height": 2},
                "visible": False,
            },
        ],
    }
    payload = {"value": root} if wrapped else root
    return json.dumps(payload)


def test_parse_ios_ax_tree_supports_wrapped_and_unwrapped_payloads() -> None:
    wrapped_nodes = parse_ios_ax_tree(_sample_tree(wrapped=True))
    unwrapped_nodes = parse_ios_ax_tree(_sample_tree(wrapped=False))

    assert len(wrapped_nodes) == len(unwrapped_nodes) == 3
    by_type = {node.class_name: node for node in wrapped_nodes}
    button = by_type["XCUIElementTypeButton"]
    assert button.text == "Continue"
    assert button.semantic_role == "button"
    assert button.clickable is True
    assert button.package_name == "com.example.demo"
    switch = by_type["XCUIElementTypeSwitch"]
    assert switch.semantic_role == "switch"
    assert switch.checkable is True
    assert switch.checked is True


def test_parse_ios_ax_tree_parses_native_frame_bounds() -> None:
    payload = json.dumps(
        {
            "type": "XCUIElementTypeApplication",
            "children": [
                {
                    "type": "XCUIElementTypeKeyboard",
                    "nativeFrame": "{{0, 1900}, {1179, 656}}",
                }
            ],
        }
    )

    nodes = parse_ios_ax_tree(payload)

    assert len(nodes) == 1
    assert nodes[0].bounds == (0, 1900, 1179, 2556)


def test_filter_ios_ax_tree_nodes_excludes_keyboard_and_tiny_nodes() -> None:
    nodes = parse_ios_ax_tree(_sample_tree(wrapped=False))
    filtered = filter_ios_ax_tree_nodes(nodes, (1179, 2556))

    assert [node.class_name for node in filtered] == ["XCUIElementTypeButton", "XCUIElementTypeSwitch"]
