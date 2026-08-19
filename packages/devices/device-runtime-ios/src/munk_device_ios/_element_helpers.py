from __future__ import annotations

from typing import Any, cast


def optional_handle_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def optional_handle_box(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        return None
    try:
        left, top, right, bottom = (int(value[0]), int(value[1]), int(value[2]), int(value[3]))
    except (TypeError, ValueError):
        return None
    return (left, top, right, bottom)


def format_ios_xpath_for_box(
    box: tuple[int, int, int, int],
    *,
    class_name: str | None = None,
) -> str:
    left, top, right, bottom = box
    width = max(right - left, 0)
    height = max(bottom - top, 0)
    node = class_name if class_name else "*"
    return f'//{node}[@x="{left}" and @y="{top}" and @width="{width}" and @height="{height}"]'


def coerce_checkbox_desired(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized in {"1", "true", "yes", "on", "checked"}:
        return True
    if normalized in {"0", "false", "no", "off", "unchecked"}:
        return False
    return bool(normalized)


def coerce_ios_checked_value(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "checked"}:
        return True
    if normalized in {"0", "false", "no", "off", "unchecked"}:
        return False
    return None


def is_ios_checkable_class(class_name: str | None) -> bool:
    if not class_name:
        return False
    lowered = class_name.lower()
    return any(token in lowered for token in ("switch", "checkbox", "toggle"))


def parse_wda_element_id(payload: dict[str, Any]) -> str:
    value = payload.get("value")
    if not isinstance(value, dict):
        raise ValueError("WDA element response missing value object")
    value_dict = cast(dict[str, Any], value)
    element_id = _read_string(value_dict, "element-6066-11e4-a52e-4f735466cecf")
    if element_id is None:
        element_id = _read_string(value_dict, "ELEMENT")
    if element_id is None:
        raise ValueError("WDA element response missing element identifier")
    return element_id


def parse_wda_attribute_value(payload: dict[str, Any]) -> str | None:
    value = payload.get("value")
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return None


def _read_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None
