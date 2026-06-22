from munk.perception import ObservationTree
from munk_perception_full.tree_registry import parse_observation_tree, resolve_tree_parser


def test_resolve_tree_parser_supports_android_web_and_ios() -> None:
    assert resolve_tree_parser("android_uixml").source_type == "android_uixml"
    assert resolve_tree_parser("web_dom").source_type == "web_dom"
    assert resolve_tree_parser("ios_ax_tree").source_type == "ios_ax_tree"


def test_parse_observation_tree_routes_web_dom_payload() -> None:
    observation_tree = ObservationTree(
        source_type="web_dom",
        content_type="json",
        payload=(
            '{"format_version":1,"url":"https://example.com","title":"Example","nodes":['
            '{"node_id":"node-0","bounds":[10,20,110,60],"tag_name":"button","role":"button",'
            '"text":"Confirm","name":"Confirm","resource_id":"confirm","clickable":true,'
            '"checkable":false,"checked":false,"enabled":true,"focused":false,'
            '"selected":false,"scrollable":false}]}'
        ),
    )

    nodes = parse_observation_tree(
        observation_tree,
        screen_size=(1440, 900),
        current_app_identity="https://example.com",
    )

    assert len(nodes) == 1
    assert nodes[0].semantic_role == "button"
    assert nodes[0].resource_id == "confirm"


def test_parse_observation_tree_routes_ios_ax_tree_payload() -> None:
    observation_tree = ObservationTree(
        source_type="ios_ax_tree",
        content_type="json",
        payload=(
            '{"type":"XCUIElementTypeApplication","bundleId":"com.example.demo","children":['
            '{"type":"XCUIElementTypeButton","name":"Continue","label":"Continue",'
            '"rect":{"x":10,"y":20,"width":100,"height":44},"enabled":true}]}'
        ),
    )

    nodes = parse_observation_tree(
        observation_tree,
        screen_size=(1179, 2556),
        current_app_identity="com.example.demo",
    )

    assert len(nodes) == 1
    assert nodes[0].semantic_role == "button"
    assert nodes[0].text == "Continue"
    assert nodes[0].package_name == "com.example.demo"
