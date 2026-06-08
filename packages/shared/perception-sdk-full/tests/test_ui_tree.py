from munk_perception_full.ui_tree import filter_ui_tree_nodes, parse_ui_hierarchy


def test_parse_ui_hierarchy_extracts_common_android_fields() -> None:
    xml_text = """
    <hierarchy>
      <node
        index="0"
        text="Confirm"
        resource-id="btn_confirm"
        class="android.widget.Button"
        package="test"
        content-desc="confirm button"
        checkable="false"
        checked="false"
        clickable="true"
        enabled="true"
        focused="false"
        selected="false"
        scrollable="false"
        bounds="[10,20][110,70]"
      />
    </hierarchy>
    """

    nodes = parse_ui_hierarchy(xml_text)

    assert len(nodes) == 1
    node = nodes[0]
    assert node.package_name == "test"
    assert node.text == "Confirm"
    assert node.resource_id == "btn_confirm"
    assert node.class_name == "android.widget.Button"
    assert node.content_desc == "confirm button"
    assert node.clickable is True
    assert node.semantic_role == "button"


def test_filter_ui_tree_nodes_keeps_semantic_and_interactive_nodes() -> None:
    xml_text = """
    <hierarchy>
      <node class="android.view.View" bounds="[0,0][1080,1920]" clickable="false" />
      <node class="android.widget.Button" text="OK" clickable="true" package="test.package" bounds="[10,10][120,80]" />
      <node class="android.widget.TextView" text="" clickable="false" bounds="[1,1][2,2]" />
    </hierarchy>
    """

    nodes = parse_ui_hierarchy(xml_text)
    filtered = filter_ui_tree_nodes(nodes, (1080, 1920))

    assert len(filtered) == 1
    assert filtered[0].text == "OK"


def test_filter_ui_tree_nodes_excludes_system_ui_and_external_packages_by_default() -> None:
    xml_text = """
    <hierarchy>
      <node
        class="android.widget.Button"
        text="Back"
        package="com.android.systemui"
        resource-id="com.android.systemui:id/back"
        clickable="true"
        bounds="[0,1800][100,1900]"
      />
      <node
        class="android.widget.Button"
        text="Open"
        package="other.package"
        resource-id="other.package:id/open"
        clickable="true"
        bounds="[10,10][120,80]"
      />
      <node
        class="android.widget.Button"
        text="Save"
        package="test.package"
        resource-id="test.package:id/save"
        clickable="true"
        bounds="[20,20][220,120]"
      />
    </hierarchy>
    """

    nodes = parse_ui_hierarchy(xml_text)
    filtered = filter_ui_tree_nodes(nodes, (1080, 1920), current_package="test.package")

    assert [node.text for node in filtered] == ["Save"]
