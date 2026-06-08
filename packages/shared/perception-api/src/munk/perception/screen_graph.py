from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, cast


def empty_str_list() -> list[str]:
    return []


def empty_node_changes() -> list["ObservedNodeChange"]:
    return []


def empty_tree_nodes() -> list["TreeNodeSnapshot"]:
    return []


def empty_links() -> list["VisualElementLink"]:
    return []


@dataclass(frozen=True)
class TreeNodeSnapshot:
    node_id: str
    stable_key: str
    bounds: tuple[int, int, int, int]
    package_name: str | None = None
    text: str | None = None
    content_desc: str | None = None
    resource_id: str | None = None
    class_name: str | None = None
    clickable: bool = False
    checkable: bool = False
    checked: bool = False
    enabled: bool = True
    focused: bool = False
    selected: bool = False
    scrollable: bool = False
    semantic_role: str | None = None
    matched_visual_ids: list[str] = field(default_factory=empty_str_list)
    promoted_to_actionable: bool = False

    def label(self) -> str:
        return self.text or self.content_desc or self.resource_id or self.semantic_role or self.class_name or self.node_id


@dataclass(frozen=True)
class VisualElementLink:
    element_id: str
    tree_node_id: str
    score: float


@dataclass(frozen=True)
class ObservedNodeChange:
    change_type: str
    stable_key: str
    label: str


@dataclass(frozen=True)
class ObservedScreenFrame:
    entry_identity: str | None
    screen_size: tuple[int, int]
    tree_available: bool
    tree_summary: str
    tree_error: str | None = None
    keyboard_visible: bool | None = None
    keyboard_bounds: tuple[int, int, int, int] | None = None
    keyboard_source: str | None = None
    tree_nodes: list[TreeNodeSnapshot] = field(default_factory=empty_tree_nodes)
    links: list[VisualElementLink] = field(default_factory=empty_links)


@dataclass(frozen=True)
class ScreenDiff:
    changed: bool
    summary: str
    appeared_nodes: list[ObservedNodeChange] = field(default_factory=empty_node_changes)
    disappeared_nodes: list[ObservedNodeChange] = field(default_factory=empty_node_changes)
    updated_nodes: list[ObservedNodeChange] = field(default_factory=empty_node_changes)
    linked_visual_changes: list[str] = field(default_factory=empty_str_list)


def to_json_dict(value: object) -> dict[str, object]:
    payload = cast(dict[str, object], asdict(cast(Any, value)))
    if not isinstance(payload, dict):
        raise TypeError("screen graph payload must serialize to a dict")
    return payload
