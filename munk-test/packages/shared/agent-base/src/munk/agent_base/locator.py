from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from munk.perception.types import ClickableElement

if TYPE_CHECKING:
    from munk.core.screen_graph import TreeNodeSnapshot


def _contains(haystack: str | None, needle: str | None) -> bool:
    if needle is None:
        return True
    if haystack is None:
        return False
    return needle.lower() in haystack.lower()


@dataclass(frozen=True)
class ElementLocator:
    text_contains: str | None = None
    resource_id_contains: str | None = None
    content_desc_contains: str | None = None
    class_name: str | None = None
    package: str | None = None

    def __post_init__(self) -> None:
        values = [
            self.text_contains,
            self.resource_id_contains,
            self.content_desc_contains,
            self.class_name,
            self.package,
        ]
        if not any(value and value.strip() for value in values):
            raise ValueError("element locator requires at least one non-empty field")

    def to_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.text_contains:
            payload["text_contains"] = self.text_contains
        if self.resource_id_contains:
            payload["resource_id_contains"] = self.resource_id_contains
        if self.content_desc_contains:
            payload["content_desc_contains"] = self.content_desc_contains
        if self.class_name:
            payload["class_name"] = self.class_name
        if self.package:
            payload["package"] = self.package
        return payload

    def summary(self) -> str:
        parts = [f"{key}={value}" for key, value in self.to_dict().items()]
        return ", ".join(parts)


def element_matches_locator(element: ClickableElement, locator: ElementLocator) -> bool:
    return (
        _contains(element.text, locator.text_contains)
        and _contains(element.resource_id, locator.resource_id_contains)
        and _contains(element.content_desc, locator.content_desc_contains)
        and _contains(element.class_name, locator.class_name)
    )


def tree_node_matches_locator(node: TreeNodeSnapshot, locator: ElementLocator) -> bool:
    return (
        _contains(node.text, locator.text_contains)
        and _contains(node.resource_id, locator.resource_id_contains)
        and _contains(node.content_desc, locator.content_desc_contains)
        and _contains(node.class_name, locator.class_name)
        and _contains(node.package_name, locator.package)
    )


def find_matching_elements(
    elements: list[ClickableElement],
    locator: ElementLocator,
) -> list[ClickableElement]:
    return [element for element in elements if element_matches_locator(element, locator)]


def find_matching_tree_nodes(
    nodes: list[TreeNodeSnapshot],
    locator: ElementLocator,
) -> list[TreeNodeSnapshot]:
    return [node for node in nodes if tree_node_matches_locator(node, locator)]
