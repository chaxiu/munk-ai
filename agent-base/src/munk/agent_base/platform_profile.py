from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from munk.app import AppPlatform

STATUS_BAR_TOP_RATIO = 0.06
STATUS_BAR_MAX_HEIGHT_RATIO = 0.04


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
            mission_lines=(
                "Decide exactly one next action for this step only, not the whole case.",
                "Use the current objective, history, screen evidence, targets, and image to choose the highest-confidence next action.",
            ),
            completion_contract_lines=(
                "When you have enough information, call exactly one final structured action output.",
                "Do not answer with plain text or explanations outside the final output.",
                "If the objective is already satisfied, or further action would be redundant or blocked, use stop.",
            ),
            tool_policy_lines=(
                "Read-only tools are optional and only for missing evidence.",
                "Do not call read tools when the seeded screen and targets already identify the next action.",
                "Do not repeat the same read tool just to restate the same evidence.",
            ),
            action_bias_lines=(
                "Prefer stop when the objective is already satisfied.",
                "Prefer a high-confidence direct action on a seeded target before exploratory actions.",
                "Prefer high-level actions before raw click, scroll, input_text, or wait.",
                "Use redetect or wait only when the target is genuinely uncertain; do not guess.",
            ),
            platform_capability_notes=(
                "Use page metadata, DOM summary, and focused-element reads only when the seeded visual context is insufficient.",
                "Reason about page state and browser focus explicitly; do not treat the web page like an Android screen.",
            ),
            status_bar_filter_enabled=False,
            enabled_read_tools=("read_page_meta", "read_dom_summary", "read_focused_element"),
        )
    if normalized == "ios":
        return PlatformRunnerProfile(
            platform="ios",
            role_identity="You are the iOS runner decision agent for the current step.",
            mission_lines=(
                "Decide exactly one next action for this step only, not the whole case.",
                "Use the current objective, history, screen evidence, targets, and image to choose the highest-confidence next action.",
            ),
            completion_contract_lines=(
                "When you have enough information, call exactly one final structured action output.",
                "Do not answer with plain text or explanations outside the final output.",
                "If the objective is already satisfied, or further action would be redundant or blocked, use stop.",
            ),
            tool_policy_lines=(
                "Read-only tools are optional and only for missing evidence.",
                "Do not call read tools when the seeded screen and targets already identify the next action.",
                "Do not repeat the same read tool just to restate the same evidence.",
            ),
            action_bias_lines=(
                "Prefer stop when the objective is already satisfied.",
                "Prefer a high-confidence direct action on a seeded target before exploratory actions.",
                "Prefer high-level actions before raw click, scroll, input_text, or wait.",
                "Use redetect or wait only when the target is genuinely uncertain; do not guess.",
            ),
            platform_capability_notes=(
                "Use only the actions and visible evidence that are actually available in this step.",
                "Do not invent Android-only widget semantics or browser-only tools when reasoning about iOS screens.",
            ),
            status_bar_filter_enabled=False,
        )
    return PlatformRunnerProfile(
        platform="android",
        role_identity="You are the Android runner decision agent for the current step.",
        mission_lines=(
            "Decide exactly one next action for this step only, not the whole case.",
            "Use the current objective, history, screen evidence, targets, and image to choose the highest-confidence next action.",
        ),
        completion_contract_lines=(
            "When you have enough information, call exactly one final structured action output.",
            "Do not answer with plain text or explanations outside the final output.",
            "Use stop only when the objective is already satisfied, the device is in a hard-stop state such as lock screen or app crash, or concrete recovery attempts show the current step still cannot progress.",
        ),
        tool_policy_lines=(
            "Read-only tools are optional and only for missing evidence.",
            "Do not call read tools when the seeded screen and targets already identify the next action.",
            "Do not repeat the same read tool just to restate the same evidence.",
            "If the required target is not visible in the seeded targets, do not click a semantically similar nearby control as a substitute.",
            "Use click only for a currently visible numbered target; never use click to stand in for back, home, or dismiss_soft_keyboard.",
        ),
        action_bias_lines=(
            "Prefer stop when the objective is already satisfied.",
            "Prefer a high-confidence direct action on a seeded target before exploratory actions or stop.",
            "Prefer high-level actions before raw click, scroll, swipe, input_text, or wait.",
            "When using scroll or swipe, output direction plus distance_px only; let the host derive concrete coordinates and duration.",
            "Use redetect or wait only when the target is genuinely uncertain; do not guess.",
            "When blockers such as a soft keyboard, popup, dropdown, picker, or modal are present and a clear removal action is available, clear the blocker first, then re-observe before choosing the next action; treat these blockers as recoverable and do not stop only because they exist.",
            "Use input_text only when the intended input already has focus; use clear_and_input when a specific visible input target must be chosen and reset.",
        ),
        platform_capability_notes=(
            "Treat numbered targets as the primary interaction surface for Android UI decisions.",
            "If the keyboard is the only blocker, prefer dismiss_soft_keyboard over navigation-oriented fallbacks.",
            "Use back only for the Android system back event, never by clicking a guessed back-like region.",
            "Use scroll for content navigation: direction names the content you want to reveal, such as scroll down for lower content and scroll up toward the top.",
            "Use swipe for gesture-driven interaction: direction names the finger motion, such as swipe down for pull-to-refresh or swipe left for card dismissal.",
            "Do not treat generic containers such as popup lists or dropdown overlays as proof that the business objective is complete.",
        ),
        status_bar_filter_enabled=True,
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
