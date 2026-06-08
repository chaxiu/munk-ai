from munk.perception import ObservationTree
from munk_perception_full.tree_registry import parse_observation_tree, resolve_tree_parser


def test_resolve_tree_parser_supports_android_and_web() -> None:
    assert resolve_tree_parser("android_uixml").source_type == "android_uixml"
    assert resolve_tree_parser("web_dom").source_type == "web_dom"


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
