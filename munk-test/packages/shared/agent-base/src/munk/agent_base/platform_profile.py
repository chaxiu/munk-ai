from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from munk.app import AppPlatform

STATUS_BAR_TOP_RATIO = 0.06
STATUS_BAR_MAX_HEIGHT_RATIO = 0.04

SHARED_RUNNER_MISSION_LINES = (
    "Decide exactly one next action for the current test step, not the whole case.",
    "Use the objective, procedure, history, current screen, and seeded target_ref values (vN / tN) to choose the highest-confidence action that advances the test.",
)
SHARED_RUNNER_COMPLETION_CONTRACT_LINES = ("Return exactly one structured action and no extra text.",)
SHARED_RUNNER_RULE_LINES = (
    "Prefer a direct action on a visible seeded target_ref (vN / tN).",
    "If the expected result is already satisfied, use stop.",
    "If a procedure exists, advance the next incomplete procedure step instead of stopping early.",
    "Do not guess or click semantically similar controls when the intended target is not visible.",
    "Use read tools only when seeded evidence is insufficient.",
    "If a recoverable blocker such as keyboard or popup is present, clear it first and then continue.",
)


@dataclass(frozen=True)
class PlatformRunnerProfile:
    platform: AppPlatform
    role_identity: str
    mission_lines: tuple[str, ...]
    completion_contract_lines: tuple[str, ...]
    tool_policy_lines: tuple[str, ...]
    action_bias_lines: tuple[str, ...]
    platform_capability_notes: tuple[str, ...]
    status_bar_filter_enabled: bool
    enabled_read_tools: tuple[str, ...] = ()
    default_tree_seed_limit: int = 0

    def display_kind(self, target: object) -> str:
        semantic_role = _normalized_text(_target_attr(target, "semantic_role"))
        class_name = _normalized_text(_target_attr(target, "class_name"))
        kind = _normalized_text(_target_attr(target, "kind"))
        clickable = _target_attr(target, "clickable") is True
        part = _normalized_text(_target_attr(target, "part"))
        if semantic_role == "input" or (
            self.platform == "android" and "edittext" in class_name
        ):
            return "input"
        if semantic_role == "button" or (
            self.platform == "android"
            and any(token in class_name for token in ("button", "imagebutton", "floatingactionbutton"))
        ):
            return "button"
        if semantic_role == "switch" or (self.platform == "android" and "switch" in class_name):
            return "switch"
        if semantic_role == "checkbox" or (
            self.platform == "android"
            and any(token in class_name for token in ("checkbox", "radiobutton"))
        ):
            return "checkbox"
        if semantic_role == "label":
            return "label"
        if kind == "text":
            return "text"
        if kind == "icon":
            return "icon"
        if clickable and _target_has_primary_label(target):
            return "container"
        if part == "tree":
            return "node"
        return "visual"

    def display_label(self, target: object) -> str | None:
        resource_id = _target_attr(target, "resource_id")
        if self.platform == "android":
            resource_id = self._android_resource_id_label(resource_id)
        for value in (
            _target_attr(target, "text"),
            _target_attr(target, "content_desc"),
            resource_id,
            _target_attr(target, "label"),
        ):
            if _has_text(value):
                return str(value).strip()
        return None

    def compact_state(self, node: Mapping[str, object]) -> dict[str, object]:
        if self.platform == "android":
            return _android_compact_state(node)
        return _generic_compact_state(node)

    def is_status_bar_like_target(self, target: object, *, screen_height: int) -> bool:
        if not self.status_bar_filter_enabled:
            return False
        if _normalized_text(_target_attr(target, "part")) != "vision" or screen_height <= 0:
            return False
        if _target_attr(target, "linked_tree_node_id") is not None:
            return False
        if _target_attr(target, "clickable") is True:
            return False
        if self.explicit_control_kind(target) is not None:
            return False
        if any(_has_text(value) for value in (_target_attr(target, "resource_id"), _target_attr(target, "content_desc"), _target_attr(target, "semantic_role"))):
            return False
        display_kind = self.display_kind(target)
        if display_kind not in {"text", "icon", "visual"}:
            return False
        box = _target_attr(target, "box")
        if not isinstance(box, tuple) or len(box) != 4:
            return False
        _, top, _, bottom = cast(tuple[int, int, int, int], box)
        height = max(0, bottom - top)
        if top > int(screen_height * STATUS_BAR_TOP_RATIO):
            return False
        if height > max(1, int(screen_height * STATUS_BAR_MAX_HEIGHT_RATIO)):
            return False
        if display_kind == "text":
            return _looks_like_status_bar_text(_target_attr(target, "text"))
        return True

    def explicit_control_kind(self, target: object) -> str | None:
        display_kind = self.display_kind(target)
        if display_kind in {"button", "input"}:
            return display_kind
        return None

    @staticmethod
    def _android_resource_id_label(value: object) -> str | None:
        if not _has_text(value):
            return None
        text = str(value).strip()
        if "/" in text:
            text = text.rsplit("/", 1)[-1]
        if ":" in text:
            text = text.rsplit(":", 1)[-1]
        return text or None


def get_runner_profile(platform: str | None) -> PlatformRunnerProfile:
    normalized = (platform or "").strip().lower()
    if normalized == "web":
        return PlatformRunnerProfile(
            platform="web",
            role_identity="You are the web runner decision agent for the current step.",
            mission_lines=SHARED_RUNNER_MISSION_LINES,
            completion_contract_lines=SHARED_RUNNER_COMPLETION_CONTRACT_LINES,
            tool_policy_lines=SHARED_RUNNER_RULE_LINES,
            action_bias_lines=(),
            platform_capability_notes=(
                "Soft-keyboard dismiss is not applicable on web; focused inputs are not soft keyboards.",
                "Prefer dismiss_keyboard=false for edit_text unless a page-specific overlay must be closed.",
                "Use set_value with #t* for date/time/select/checkbox/switch and prefer it for structure text fields.",
                "edit_text is only for real text input (append/replace/keyboard); never use it for check/select/date.",
                "Date/time values must use ISO form (YYYY-MM-DD / HH:mm). Never invent CSS selectors.",
                "Use #v* only for icons/custom visuals without a clear structure node.",
            ),
            status_bar_filter_enabled=False,
            enabled_read_tools=("read_page_meta", "read_dom_summary", "read_focused_element"),
            default_tree_seed_limit=40,
        )
    if normalized == "ios":
        return PlatformRunnerProfile(
            platform="ios",
            role_identity="You are the iOS runner decision agent for the current step.",
            mission_lines=SHARED_RUNNER_MISSION_LINES,
            completion_contract_lines=SHARED_RUNNER_COMPLETION_CONTRACT_LINES,
            tool_policy_lines=SHARED_RUNNER_RULE_LINES,
            action_bias_lines=(),
            platform_capability_notes=(
                "Prefer #t* for structure-backed iOS controls (TextField/Button/Switch).",
                "Use set_value with #t* for Switch and prefer it for TextField value setting.",
                "edit_text is only for real text input; never use it for Switch/checkbox-like controls.",
                "TextField/Switch fill/read uses accessibility node APIs; never invent CSS or web selectors.",
                "Use #v* only for icons/custom visuals without a clear structure node.",
            ),
            status_bar_filter_enabled=False,
            default_tree_seed_limit=40,
        )
    return PlatformRunnerProfile(
        platform="android",
        role_identity="You are the Android runner decision agent for one step of a mobile automated test case.",
        mission_lines=SHARED_RUNNER_MISSION_LINES,
        completion_contract_lines=SHARED_RUNNER_COMPLETION_CONTRACT_LINES,
        tool_policy_lines=SHARED_RUNNER_RULE_LINES,
        action_bias_lines=(),
        platform_capability_notes=(
            "Prefer #t* for structure-backed Android controls (EditText/Button/CheckBox/Switch).",
            "Use set_value with #t* for CheckBox/Switch and prefer it for EditText value setting.",
            "edit_text is only for real text input; never use it for CheckBox/Switch.",
            "EditText fill/read uses accessibility node APIs; never invent CSS or web selectors.",
            "Use #v* only for icons/custom visuals without a clear structure node.",
        ),
        status_bar_filter_enabled=True,
        default_tree_seed_limit=40,
    )


def _target_attr(target: object, name: str) -> object:
    return getattr(target, name, None)


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized_text(value: object) -> str:
    return str(value or "").strip().lower()


def _target_has_primary_label(target: object) -> bool:
    return any(
        _has_text(value)
        for value in (
            _target_attr(target, "text"),
            _target_attr(target, "content_desc"),
            _target_attr(target, "resource_id"),
            _target_attr(target, "label"),
        )
    )


def _android_compact_state(node: Mapping[str, object]) -> dict[str, object]:
    class_name = str(node.get("class_name") or "")
    state: dict[str, object] = {}
    is_checkbox_like = any(token in class_name for token in ("CheckBox", "Switch", "RadioButton"))
    is_edit_text = "EditText" in class_name
    clickable = node.get("clickable")
    enabled = node.get("enabled")
    checkable = node.get("checkable")
    checked = node.get("checked")
    focused = node.get("focused")
    if is_checkbox_like:
        state["checkable"] = bool(checkable)
        state["checked"] = bool(checked)
        state["enabled"] = bool(enabled) if isinstance(enabled, bool) else True
        if isinstance(clickable, bool):
            state["clickable"] = clickable
        return state
    if is_edit_text:
        state["enabled"] = bool(enabled) if isinstance(enabled, bool) else True
        if focused:
            state["focused"] = True
        return state
    return _generic_compact_state(node)


def _generic_compact_state(node: Mapping[str, object]) -> dict[str, object]:
    state: dict[str, object] = {}
    clickable = node.get("clickable")
    enabled = node.get("enabled")
    focused = node.get("focused")
    selected = node.get("selected")
    scrollable = node.get("scrollable")
    checkable = node.get("checkable")
    checked = node.get("checked")
    if isinstance(clickable, bool) and clickable:
        state["clickable"] = True
    if isinstance(enabled, bool):
        if enabled is False or state:
            state["enabled"] = enabled
    if isinstance(checkable, bool) and checkable:
        state["checkable"] = True
    if isinstance(checked, bool) and checked:
        state["checked"] = True
    if isinstance(focused, bool) and focused:
        state["focused"] = True
    if isinstance(selected, bool) and selected:
        state["selected"] = True
    if isinstance(scrollable, bool) and scrollable:
        state["scrollable"] = True
    return state


def _looks_like_status_bar_text(value: object) -> bool:
    if not _has_text(value):
        return False
    text = str(value).strip()
    compact = text.replace(" ", "").upper()
    if ":" in compact and any(ch.isdigit() for ch in compact):
        if all(ch.isdigit() or ch in {":", "A", "P", "M"} for ch in compact):
            return True
    if compact.endswith("%") and compact[:-1].isdigit():
        return True
    return False
