from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from munk.perception import ObservationTree

from .tree_models import ParsedTreeNode, filter_parsed_tree_nodes
from .tree_parsers import (
    filter_android_uixml_nodes,
    filter_web_dom_nodes,
    parse_android_uixml,
    parse_web_dom_snapshot,
)

TreeParseFn = Callable[[str], list[ParsedTreeNode]]
TreeFilterFn = Callable[[list[ParsedTreeNode], tuple[int, int], str | None], list[ParsedTreeNode]]


@dataclass(frozen=True)
class RegisteredTreeParser:
    source_type: str
    parse: TreeParseFn
    filter_nodes: TreeFilterFn


def parse_observation_tree(
    observation_tree: ObservationTree,
    *,
    screen_size: tuple[int, int],
    current_app_identity: str | None = None,
) -> list[ParsedTreeNode]:
    parser = resolve_tree_parser(observation_tree.source_type)
    parsed_nodes = parser.parse(observation_tree.payload)
    filtered_nodes = parser.filter_nodes(parsed_nodes, screen_size, current_app_identity)
    return filter_parsed_tree_nodes(filtered_nodes, screen_size)


def resolve_tree_parser(source_type: str) -> RegisteredTreeParser:
    try:
        return _DEFAULT_TREE_PARSERS[source_type]
    except KeyError as exc:
        raise KeyError(f"unsupported tree source: {source_type}") from exc


def _filter_android(
    nodes: list[ParsedTreeNode],
    screen_size: tuple[int, int],
    current_app_identity: str | None,
) -> list[ParsedTreeNode]:
    return filter_android_uixml_nodes(nodes, screen_size, current_package=current_app_identity)


def _filter_web(
    nodes: list[ParsedTreeNode],
    screen_size: tuple[int, int],
    current_app_identity: str | None,
) -> list[ParsedTreeNode]:
    del current_app_identity
    return filter_web_dom_nodes(nodes, screen_size)


_DEFAULT_TREE_PARSERS = {
    "android_uixml": RegisteredTreeParser(
        source_type="android_uixml",
        parse=parse_android_uixml,
        filter_nodes=_filter_android,
    ),
    "web_dom": RegisteredTreeParser(
        source_type="web_dom",
        parse=parse_web_dom_snapshot,
        filter_nodes=_filter_web,
    ),
}
