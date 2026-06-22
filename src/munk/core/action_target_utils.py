from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalized_text(value: object) -> str:
    return str(value or "").strip().lower()


def compact_box(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        return (int(value[0]), int(value[1]), int(value[2]), int(value[3]))
    except (TypeError, ValueError):
        return None


def state_bool(state: Mapping[str, object] | None, key: str) -> bool | None:
    if state is None:
        return None
    value = state.get(key)
    return value if isinstance(value, bool) else None


def compact_node_text(linked_compact_node: Mapping[str, object] | None) -> str | None:
    if linked_compact_node is None:
        return None
    value = linked_compact_node.get("txt")
    if has_text(value):
        return str(value).strip()
    return None


def clip_ocr_text(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if len(text) <= 48:
        return text
    return f"{text[:45]}..."


def first_int(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return None
