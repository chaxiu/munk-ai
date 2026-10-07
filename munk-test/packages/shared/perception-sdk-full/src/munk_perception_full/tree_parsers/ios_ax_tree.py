from __future__ import annotations

import json
from typing import Any

from ..tree_models import ParsedTreeNode

_CLICKABLE_TYPE_MARKERS = (
    "button",
    "cell",
    "link",
    "tab",
    "menuitem",
    "picker",
    "segmentedcontrol",
    "searchfield",
    "textfield",
    "securetextfield",
)
_CHECKABLE_TYPE_MARKERS = ("checkbox", "switch")
_SCROLLABLE_TYPE_MARKERS = ("scrollview", "table", "collectionview", "webview")
_SYSTEM_UI_TYPE_MARKERS = ("statusbar", "keyboard")


def parse_ios_ax_tree(payload: str) -> list[ParsedTreeNode]:
    cleaned = payload.strip()
    if not cleaned:
        return []
    try:
        raw = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    root = _normalize_root(raw)
    if root is None:
        return []
    nodes: list[ParsedTreeNode] = []
    counter = 0
    app_bundle_id = _clean_text(root.get("bundleId"))
    for element in _iter_ax_nodes(root):
        bounds = _extract_rect_bounds(element)
        if bounds is None:
            continue
        node_id = f"node-{counter}"
        counter += 1
        class_name = _clean_text(element.get("type"))
        label = _clean_text(element.get("label"))
        name = _clean_text(element.get("name"))
        value = _clean_text(element.get("value"))
        text = value or label or name
        content_desc = label if label and label != text else name if name and name != text else None
        resource_id = _clean_text(element.get("identifier"))
        clickable = _infer_clickable(class_name)
        checkable = _infer_checkable(class_name)
        checked = _infer_checked(element, checkable=checkable)
        nodes.append(
            ParsedTreeNode(
                node_id=node_id,
                bounds=bounds,
                package_name=app_bundle_id,
                class_name=class_name,
                text=text,
                content_desc=content_desc,
                resource_id=resource_id,
                clickable=clickable,
                checkable=checkable,
                checked=checked,
                enabled=_coerce_bool(element.get("enabled"), default=True),
                focused=_coerce_bool(element.get("focused")),
                selected=_coerce_bool(element.get("selected")),
                scrollable=_infer_scrollable(class_name),
                semantic_role=_infer_semantic_role(class_name, text, content_desc),
            )
        )
    return nodes


def filter_ios_ax_tree_nodes(
    nodes: list[ParsedTreeNode],
    screen_size: tuple[int, int],
    *,
    current_bundle_id: str | None = None,
) -> list[ParsedTreeNode]:
    del current_bundle_id
    screen_width, screen_height = screen_size
    screen_area = max(1, screen_width * screen_height)
    kept: list[ParsedTreeNode] = []
    for node in nodes:
        if is_ios_system_ui_node(node):
            continue
        if not node.enabled:
            continue
        area = _box_area(node.bounds)
        if area <= 4:
            continue
        x1, y1, x2, y2 = node.bounds
        if x2 <= 0 or y2 <= 0 or x1 >= screen_width or y1 >= screen_height:
            continue
        if area >= int(screen_area * 0.98) and not _has_semantics(node):
            continue
        if not (_has_semantics(node) or _has_action_value(node) or _has_interesting_class(node.class_name)):
            continue
        kept.append(node)
    return kept


def is_ios_system_ui_node(node: ParsedTreeNode) -> bool:
    class_text = (node.class_name or "").lower()
    return any(marker in class_text for marker in _SYSTEM_UI_TYPE_MARKERS)


def _normalize_root(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    value = raw.get("value")
    if isinstance(value, dict):
        return value
    if raw.get("type") is not None or raw.get("children") is not None:
        return raw
    return None


def _iter_ax_nodes(root: dict[str, Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = [root]
    while stack:
        current = stack.pop()
        children = current.get("children")
        if isinstance(children, list):
            for child in reversed(children):
                if isinstance(child, dict):
                    stack.append(child)
        if _is_visible_node(current):
            collected.append(current)
    return collected


def _is_visible_node(node: dict[str, Any]) -> bool:
    visible = node.get("visible")
    if isinstance(visible, bool) and not visible:
        return False
    accessible = node.get("accessible")
    if isinstance(accessible, bool) and not accessible:
        return False
    return True


def _extract_rect_bounds(node: dict[str, Any]) -> tuple[int, int, int, int] | None:
    rect = node.get("rect")
    if isinstance(rect, dict):
        x = rect.get("x")
        y = rect.get("y")
        width = rect.get("width")
        height = rect.get("height")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return None
        if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
            return None
        left = int(x)
        top = int(y)
        right = int(x + width)
        bottom = int(y + height)
    else:
        frame_text = node.get("nativeFrame") or node.get("frame")
        parsed = _parse_ios_frame_string(frame_text)
        if parsed is None:
            return None
        left, top, right, bottom = parsed
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def _parse_ios_frame_string(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text.startswith("{{") or "}, {" not in text or not text.endswith("}}"):
        return None
    try:
        position_part, size_part = text[2:-2].split("}, {", maxsplit=1)
        x_text, y_text = position_part.split(",", maxsplit=1)
        width_text, height_text = size_part.split(",", maxsplit=1)
        x = float(x_text.strip())
        y = float(y_text.strip())
        width = float(width_text.strip())
        height = float(height_text.strip())
    except ValueError:
        return None
    return (int(x), int(y), int(x + width), int(y + height))


def _infer_clickable(class_name: str | None) -> bool:
    class_text = (class_name or "").lower()
    return any(marker in class_text for marker in _CLICKABLE_TYPE_MARKERS)


def _infer_checkable(class_name: str | None) -> bool:
    class_text = (class_name or "").lower()
    return any(marker in class_text for marker in _CHECKABLE_TYPE_MARKERS)


def _infer_checked(element: dict[str, Any], *, checkable: bool) -> bool:
    if _coerce_bool(element.get("selected")):
        return True
    if not checkable:
        return False
    value = element.get("value")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "on"}
    return False


def _infer_scrollable(class_name: str | None) -> bool:
    class_text = (class_name or "").lower()
    return any(marker in class_text for marker in _SCROLLABLE_TYPE_MARKERS)


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
    if "textfield" in class_text or "searchfield" in class_text:
        return "input"
    if "image" in class_text:
        return "image_button"
    if "tab" in class_text:
        return "tab"
    if "link" in class_text or "cell" in class_text:
        return "button"
    if text or content_desc:
        return "label"
    return None


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _coerce_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


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
            "textfield",
            "searchfield",
            "tab",
            "link",
            "cell",
        )
    )
