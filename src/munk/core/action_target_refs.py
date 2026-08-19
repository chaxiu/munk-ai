from __future__ import annotations

import re
from typing import Literal

from munk.core.action_target_models import TARGET_REF_PATTERN, ActionTarget, TargetHandle

_TARGET_REF_RE = re.compile(TARGET_REF_PATTERN)
_VALUE_INPUT_TYPES = frozenset(
    {"date", "time", "datetime-local", "month", "week"}
)
_TEXT_INPUT_TYPES = frozenset(
    {
        "text",
        "search",
        "email",
        "password",
        "tel",
        "url",
        "number",
        "",
        None,
    }
)
_NATIVE_STRUCTURE_FILL_TYPES = frozenset(
    {
        "date",
        "time",
        "datetime-local",
        "month",
        "week",
        "checkbox",
        "radio",
    }
)


def normalize_target_ref(raw: str) -> str:
    normalized = raw.strip()
    if normalized.startswith("#"):
        normalized = normalized[1:]
    normalized = normalized.strip().lower()
    if not _TARGET_REF_RE.fullmatch(normalized):
        raise ValueError(f"invalid target_ref: {raw!r}")
    return normalized


def parse_target_ref(raw: str) -> tuple[Literal["v", "t"], int]:
    ref = normalize_target_ref(raw)
    channel = ref[0]
    index = int(ref[1:])
    if channel not in {"v", "t"}:
        raise ValueError(f"invalid target_ref channel: {raw!r}")
    return channel, index  # type: ignore[return-value]


def build_target_ref(*, channel: Literal["v", "t"], index: int) -> str:
    if index < 1:
        raise ValueError(f"target index must be >= 1, got {index}")
    return f"{channel}{index}"


def derive_fill_mode(*, tag: str | None, input_type: str | None) -> str:
    """Device execution mode for fill_element: check | select | value.

    Distinct from set_value_control_family (rebind compatibility). Date and text
    both map to fill_mode=value because the device API uses the same fill path.
    """
    normalized_tag = (tag or "").strip().lower()
    normalized_type = (input_type or "").strip().lower()
    if normalized_tag == "select":
        return "select"
    if normalized_type in {"checkbox", "radio"} or normalized_tag in {"checkbox", "radio"}:
        return "check"
    if normalized_type in _VALUE_INPUT_TYPES:
        return "value"
    if normalized_tag in {"input", "textarea"} or normalized_type in _TEXT_INPUT_TYPES:
        return "value"
    return "value"


_A11Y_CHECK_CLASS_TOKENS = (
    "checkbox",
    "switch",
    "radiobutton",
    "radio",
    "togglebutton",
    "toggle",
)


def derive_a11y_fill_mode(class_name: str | None) -> str:
    """A11y fill_mode: check for toggle-like controls, otherwise value."""
    normalized = (class_name or "").strip().lower()
    if any(token in normalized for token in _A11Y_CHECK_CLASS_TOKENS):
        return "check"
    return "value"


def derive_dom_selector(
    *,
    node_id: str,
    test_id: str | None = None,
    name: str | None = None,
    resource_id: str | None = None,
) -> str:
    if test_id and test_id.strip():
        escaped = _css_escape(test_id.strip())
        return f'[data-testid="{escaped}"], [data-test-id="{escaped}"]'
    if name and name.strip():
        return f'[name="{_css_escape(name.strip())}"]'
    if resource_id and resource_id.strip() and _is_stable_dom_id(resource_id):
        return f"#{_css_escape(resource_id.strip())}"
    return f'[data-munk-node-id="{_css_escape(node_id)}"]'


def build_spatial_handle(box: tuple[int, int, int, int]) -> TargetHandle:
    return TargetHandle(kind="spatial", box=box)


def build_a11y_handle(
    *,
    node_id: str | None,
    stable_key: str | None = None,
    resource_id: str | None = None,
    class_name: str | None = None,
    box: tuple[int, int, int, int] | None = None,
) -> TargetHandle:
    return TargetHandle(
        kind="a11y",
        node_id=node_id,
        stable_key=stable_key,
        resource_id=resource_id,
        class_name=class_name,
        box=box,
        fill_mode=derive_a11y_fill_mode(class_name),
    )


def build_dom_handle(
    *,
    node_id: str,
    box: tuple[int, int, int, int],
    tag: str | None = None,
    input_type: str | None = None,
    name: str | None = None,
    value: str | None = None,
    resource_id: str | None = None,
    test_id: str | None = None,
    stable_key: str | None = None,
) -> TargetHandle:
    fill_mode = derive_fill_mode(tag=tag, input_type=input_type)
    selector = derive_dom_selector(
        node_id=node_id,
        test_id=test_id,
        name=name,
        resource_id=resource_id,
    )
    return TargetHandle(
        kind="dom",
        box=box,
        node_id=node_id,
        stable_key=stable_key,
        resource_id=resource_id,
        class_name=tag,
        selector=selector,
        tag=tag,
        input_type=input_type,
        name=name,
        value=value,
        fill_mode=fill_mode,
        test_id=test_id,
    )


def is_form_control_target(target: ActionTarget) -> bool:
    handle = target.handle
    tag = (target.class_name or (handle.tag if handle else None) or "").lower()
    input_type = (target.input_type or (handle.input_type if handle else None) or "").lower()
    role = (target.semantic_role or "").lower()
    if tag in {"input", "textarea", "select", "button"}:
        return True
    if role in {"input", "button", "checkbox", "switch"}:
        return True
    if input_type:
        return True
    return False


_TEXT_INPUT_CLASS_TOKENS = (
    "edittext",
    "textfield",
    "textinput",
    "textarea",
    "searchfield",
)
_SET_VALUE_CHECK_ROLES = frozenset({"checkbox", "switch", "radio"})


def requires_set_value_handle(handle: TargetHandle | None) -> bool:
    """Handle-layer: structured control that must use set_value, not edit_text."""
    if handle is None:
        return False
    fill_mode = (handle.fill_mode or "").strip().lower()
    if fill_mode in {"check", "select"}:
        return True
    input_type = (handle.input_type or "").strip().lower()
    if input_type in _NATIVE_STRUCTURE_FILL_TYPES:
        return True
    tag = (handle.tag or "").strip().lower()
    if tag == "select":
        return True
    class_name = (handle.class_name or "").strip().lower()
    return any(token in class_name for token in _A11Y_CHECK_CLASS_TOKENS)


def requires_set_value_action(target: ActionTarget) -> bool:
    """Target-layer gate: date/time/select/checkbox/switch/radio must use set_value.

    Prefers handle signals, then target-level fields for spatial / incomplete handles.
    """
    handle = target.handle
    if requires_set_value_handle(handle):
        return True
    input_type = (target.input_type or (handle.input_type if handle else None) or "").lower()
    if input_type in _NATIVE_STRUCTURE_FILL_TYPES:
        return True
    tag = (target.class_name or (handle.tag if handle else None) or "").lower()
    if tag == "select":
        return True
    class_name = (target.class_name or (handle.class_name if handle else None) or "").lower()
    if any(token in class_name for token in _A11Y_CHECK_CLASS_TOKENS):
        return True
    role = (target.semantic_role or "").strip().lower()
    return role in _SET_VALUE_CHECK_ROLES


def is_text_input_handle(handle: TargetHandle | None) -> bool:
    """Handle-layer: real text input (dom/a11y); excludes set_value-only controls."""
    if handle is None or handle.kind not in {"dom", "a11y"}:
        return False
    if requires_set_value_handle(handle):
        return False
    tag = (handle.tag or "").strip().lower()
    if tag in {"input", "textarea"}:
        input_type = (handle.input_type or "").strip().lower()
        return input_type in _TEXT_INPUT_TYPES or input_type == ""
    class_name = (handle.class_name or "").strip().lower()
    return any(token in class_name for token in _TEXT_INPUT_CLASS_TOKENS)


def is_text_input_target(target: ActionTarget) -> bool:
    """Target-layer: edit_text is allowed (real text input; not check/select/date)."""
    if requires_set_value_action(target):
        return False
    kind = (target.kind or "").strip().lower()
    role = (target.semantic_role or "").strip().lower()
    if kind == "input" or role == "input":
        return True
    class_name = (target.class_name or "").strip().lower()
    if any(token in class_name for token in _TEXT_INPUT_CLASS_TOKENS):
        return True
    return is_text_input_handle(target.handle)


def set_value_control_family(target: ActionTarget) -> str | None:
    """Rebind family: check | select | datetime | text.

    Not the same as handle.fill_mode:
    - fill_mode tells the device *how* to fill (check/select/value)
    - family tells rebind *which controls may substitute* (date ≠ text even when
      both use fill_mode=value)
    """
    handle = target.handle
    if handle is None or handle.kind not in {"dom", "a11y"}:
        return None

    fill_mode = (handle.fill_mode or "").strip().lower()
    if fill_mode == "check":
        return "check"
    if fill_mode == "select":
        return "select"

    input_type = (target.input_type or handle.input_type or "").strip().lower()
    if input_type in _VALUE_INPUT_TYPES:
        return "datetime"

    if requires_set_value_action(target):
        class_name = (target.class_name or handle.class_name or "").lower()
        tag = (handle.tag or target.class_name or "").lower()
        role = (target.semantic_role or "").strip().lower()
        if any(token in class_name for token in _A11Y_CHECK_CLASS_TOKENS) or role in _SET_VALUE_CHECK_ROLES:
            return "check"
        if tag == "select":
            return "select"
        return "datetime"

    if is_text_input_target(target):
        return "text"
    return None


def handle_as_mapping(handle: TargetHandle) -> dict[str, object]:
    payload: dict[str, object] = {"kind": handle.kind}
    for key in (
        "box",
        "node_id",
        "stable_key",
        "resource_id",
        "class_name",
        "selector",
        "tag",
        "input_type",
        "name",
        "value",
        "fill_mode",
        "test_id",
    ):
        value = getattr(handle, key)
        if value is not None:
            payload[key] = value
    return payload


def _css_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _is_stable_dom_id(resource_id: str) -> bool:
    cleaned = resource_id.strip()
    if not cleaned:
        return False
    if " " in cleaned:
        return False
    if cleaned.startswith(("ember", "react-")):
        return False
    return True
