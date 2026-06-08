from munk.perception.types import ClickableElement
from munk_perception_full.screen_graph_builder import (
    STABLE_KEY_GRID_COLUMNS,
    STABLE_KEY_GRID_ROWS,
    build_observed_screen_frame,
)
from munk_perception_full.ui_tree import UiTreeNode


def test_build_observed_screen_frame_enriches_visual_element_with_tree_fields() -> None:
    elements = [ClickableElement(box=(10, 20, 110, 70), kind="text", text="Confirm", score=0.9)]
    tree_nodes = [
        UiTreeNode(
            node_id="node-1",
            bounds=(8, 18, 112, 74),
            class_name="android.widget.Button",
            text="Confirm",
            resource_id="btn_confirm",
            clickable=True,
            semantic_role="button",
        )
    ]

    enriched, frame = build_observed_screen_frame(
        entry_identity="test.package",
        screen_size=(1080, 1920),
        elements=elements,
        tree_nodes=tree_nodes,
        tree_available=True,
    )

    assert len(enriched) == 1
    assert enriched[0].resource_id == "btn_confirm"
    assert enriched[0].class_name == "android.widget.Button"
    assert enriched[0].semantic_role == "button"
    assert len(frame.links) == 1


def test_build_observed_screen_frame_keeps_unmatched_tree_nodes_only_in_frame() -> None:
    tree_nodes = [
        UiTreeNode(
            node_id="node-2",
            bounds=(200, 300, 320, 360),
            package_name="test.package",
            class_name="android.widget.Button",
            text="Submit",
            resource_id="btn_submit",
            clickable=True,
            semantic_role="button",
        )
    ]

    enriched, frame = build_observed_screen_frame(
        entry_identity="test.package",
        screen_size=(1080, 1920),
        elements=[],
        tree_nodes=tree_nodes,
        tree_available=True,
    )

    assert enriched == []
    assert frame.tree_nodes[0].resource_id == "btn_submit"
    assert frame.tree_nodes[0].promoted_to_actionable is False


def test_build_observed_screen_frame_keeps_system_ui_tree_nodes_out_of_elements() -> None:
    tree_nodes = [
        UiTreeNode(
            node_id="node-3",
            bounds=(0, 1800, 100, 1900),
            package_name="com.android.systemui",
            class_name="android.widget.Button",
            text="Back",
            resource_id="com.android.systemui:id/back",
            clickable=True,
            semantic_role="button",
        )
    ]

    enriched, frame = build_observed_screen_frame(
        entry_identity="test.package",
        screen_size=(1080, 1920),
        elements=[],
        tree_nodes=tree_nodes,
        tree_available=True,
    )

    assert enriched == []
    assert frame.tree_nodes[0].package_name == "com.android.systemui"


def test_build_observed_screen_frame_keeps_tree_nodes_without_injecting_tree_only_elements() -> None:
    tree_nodes = [
        UiTreeNode(
            node_id="fab",
            bounds=(1160, 2484, 1356, 2680),
            package_name="test.package",
            class_name="com.google.android.material.floatingactionbutton.FloatingActionButton",
            resource_id="test.package:id/fab_add_task",
            clickable=True,
            semantic_role="button",
        )
    ]

    enriched, frame = build_observed_screen_frame(
        entry_identity="test.package",
        screen_size=(1440, 2960),
        elements=[],
        tree_nodes=tree_nodes,
        tree_available=True,
    )

    assert enriched == []
    assert frame.tree_nodes[0].node_id == "fab"
    assert frame.tree_nodes[0].resource_id == "test.package:id/fab_add_task"


def test_build_observed_screen_frame_keeps_unique_resource_id_key_unchanged() -> None:
    tree_nodes = [
        UiTreeNode(
            node_id="node-unique",
            bounds=(120, 240, 240, 320),
            package_name="test.package",
            class_name="android.widget.Button",
            resource_id="test.package:id/btn_unique",
            clickable=True,
            semantic_role="button",
        )
    ]

    _, frame = build_observed_screen_frame(
        entry_identity="test.package",
        screen_size=(1080, 1920),
        elements=[],
        tree_nodes=tree_nodes,
        tree_available=True,
    )

    assert frame.tree_nodes[0].stable_key == "rid:test.package:id/btn_unique"


def test_build_observed_screen_frame_disambiguates_duplicate_resource_ids_with_grid_key() -> None:
    tree_nodes = [
        UiTreeNode(
            node_id="node-top",
            bounds=(40, 120, 180, 220),
            package_name="test.package",
            class_name="android.widget.CompoundButton",
            resource_id="test.package:id/filter_switch",
            checkable=True,
        ),
        UiTreeNode(
            node_id="node-middle",
            bounds=(40, 960, 180, 1060),
            package_name="test.package",
            class_name="android.widget.CompoundButton",
            resource_id="test.package:id/filter_switch",
            checkable=True,
        ),
        UiTreeNode(
            node_id="node-bottom",
            bounds=(40, 1680, 180, 1780),
            package_name="test.package",
            class_name="android.widget.CompoundButton",
            resource_id="test.package:id/filter_switch",
            checkable=True,
        ),
    ]

    _, frame = build_observed_screen_frame(
        entry_identity="test.package",
        screen_size=(1080, 1920),
        elements=[],
        tree_nodes=tree_nodes,
        tree_available=True,
    )

    stable_keys = [node.stable_key for node in frame.tree_nodes]

    assert len(set(stable_keys)) == 3
    assert stable_keys[0] == "rid:test.package:id/filter_switch|grid:0:1"
    assert stable_keys[1] == f"rid:test.package:id/filter_switch|grid:0:{(960 * STABLE_KEY_GRID_ROWS) // 1920}"
    assert stable_keys[2] == f"rid:test.package:id/filter_switch|grid:0:{min((1680 * STABLE_KEY_GRID_ROWS) // 1920, STABLE_KEY_GRID_ROWS - 1)}"
    assert all(key.startswith("rid:test.package:id/filter_switch|grid:") for key in stable_keys)
    assert STABLE_KEY_GRID_COLUMNS == 8
