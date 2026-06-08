from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..tree_models import ParsedTreeNode

_BOUNDS_PATTERN = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def parse_android_uixml(payload: str) -> list[ParsedTreeNode]:
    cleaned = payload.strip()
    if not cleaned:
        return []
    root = ET.fromstring(cleaned)
    nodes: list[ParsedTreeNode] = []
    counter = 0
    for element in root.iter("node"):
        bounds = _parse_bounds(element.attrib.get("bounds"))
        if bounds is None:
            continue
        node_id = f"node-{counter}"
        counter += 1
        class_name = _clean_text(element.attrib.get("class"))
        text = _clean_text(element.attrib.get("text"))
        content_desc = _clean_text(element.attrib.get("content-desc"))
        resource_id = _clean_text(element.attrib.get("resource-id"))
        nodes.append(
            ParsedTreeNode(
                node_id=node_id,
                bounds=bounds,
                package_name=_clean_text(element.attrib.get("package")),
                class_name=class_name,
                text=text,
                content_desc=content_desc,
                resource_id=resource_id,
                clickable=_parse_bool(element.attrib.get("clickable")),
                checkable=_parse_bool(element.attrib.get("checkable")),
                checked=_parse_bool(element.attrib.get("checked")),
                enabled=_parse_bool(element.attrib.get("enabled"), default=True),
                focused=_parse_bool(element.attrib.get("focused")),
                selected=_parse_bool(element.attrib.get("selected")),
                scrollable=_parse_bool(element.attrib.get("scrollable")),
                semantic_role=_infer_semantic_role(class_name, text, content_desc),
            )
        )
    return nodes


def filter_android_uixml_nodes(
    nodes: list[ParsedTreeNode],
    screen_size: tuple[int, int],
    *,
    current_package: str | None = None,
    allow_external_packages: bool = False,
    exclude_system_ui: bool = True,
) -> list[ParsedTreeNode]:
    screen_width, screen_height = screen_size
    screen_area = max(1, screen_width * screen_height)
    kept: list[ParsedTreeNode] = []
    for node in nodes:
        if exclude_system_ui and is_android_system_ui_node(node):
            continue
        if (
            current_package
            and node.package_name
            and node.package_name != current_package
            and not allow_external_packages
        ):
            continue
        area = _box_area(node.bounds)
        if area <= 4:
            continue
        if area >= int(screen_area * 0.98) and not _has_semantics(node):
            continue
        if not (_has_semantics(node) or _has_action_value(node) or _has_interesting_class(node.class_name)):
            continue
        kept.append(node)
    return kept


def is_android_system_ui_node(node: ParsedTreeNode) -> bool:
    package_name = (node.package_name or "").lower()
    resource_id = (node.resource_id or "").lower()
    class_name = (node.class_name or "").lower()
    label = f"{node.text or ''} {node.content_desc or ''}".strip().lower()
    return any(
        [
            package_name.startswith("com.android.systemui"),
            package_name.startswith("com.google.android.apps.nexuslauncher"),
            resource_id.startswith("com.android.systemui:"),
            resource_id.startswith("android:id/navigationbar"),
            resource_id.startswith("android:id/statusbar"),
            "navigationbar" in resource_id,
            "statusbar" in resource_id,
            "recent_apps" in resource_id,
            "home_handle" in resource_id,
            "back" == label and "button" in class_name,
            "home" == label and "button" in class_name,
        ]
    )


def _parse_bounds(value: str | None) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    match = _BOUNDS_PATTERN.fullmatch(value.strip())
    if match is None:
        return None
    x1, y1, x2, y2 = (int(group) for group in match.groups())
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2, y2)


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() == "true"


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _infer_semantic_role(
    class_name: str | None,
    text: str | None,
    content_desc: str | None,
) -> str | None:
    class_text = (class_name or "").lower()
    if "button" in class_text:
        return "button"
    if "checkbox" in class_text:
        return "checkbox"
    if "switch" in class_text:
        return "switch"
    if "edittext" in class_text:
        return "input"
    if "imagebutton" in class_text:
        return "image_button"
    if "tab" in class_text:
        return "tab"
    if text or content_desc:
        return "label"
    return None


def _box_area(box: tuple[int, int, int, int]) -> int:
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def _has_semantics(node: ParsedTreeNode) -> bool:
    return any([node.text, node.content_desc, node.resource_id, node.semantic_role])


def _has_action_value(node: ParsedTreeNode) -> bool:
    return any(
        [
            node.clickable,
            node.checkable,
            node.checked,
            node.scrollable,
            node.focused,
            node.selected,
        ]
    )


def _has_interesting_class(class_name: str | None) -> bool:
    class_text = (class_name or "").lower()
    return any(
        token in class_text
        for token in (
            "button",
            "checkbox",
            "switch",
            "radio",
            "edittext",
            "tab",
        )
    )
