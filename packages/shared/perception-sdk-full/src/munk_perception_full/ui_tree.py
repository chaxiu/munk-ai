from __future__ import annotations

from .tree_models import ParsedTreeNode, summarize_tree_nodes
from .tree_parsers.android_uixml import (
    filter_android_uixml_nodes,
    is_android_system_ui_node,
    parse_android_uixml,
)

UiTreeNode = ParsedTreeNode


def parse_ui_hierarchy(xml_text: str) -> list[UiTreeNode]:
    return parse_android_uixml(xml_text)


def filter_ui_tree_nodes(
    nodes: list[UiTreeNode],
    screen_size: tuple[int, int],
    *,
    current_package: str | None = None,
    allow_external_packages: bool = False,
    exclude_system_ui: bool = True,
) -> list[UiTreeNode]:
    return filter_android_uixml_nodes(
        nodes,
        screen_size,
        current_package=current_package,
        allow_external_packages=allow_external_packages,
        exclude_system_ui=exclude_system_ui,
    )


def is_system_ui_node(node: UiTreeNode) -> bool:
    return is_android_system_ui_node(node)


def summarize_ui_tree_nodes(nodes: list[UiTreeNode]) -> str:
    return summarize_tree_nodes(nodes)
