from __future__ import annotations

from typing import Any

from munk.agent_base.action import Action, ActionType
from munk.agent_base.base import ActionHistoryEntry


def action_history_detail(action: Action) -> str | None:
    if action.type in {ActionType.INPUT, ActionType.EDIT_TEXT} and action.text:
        detail = f"text={action.text!r}"
        if action.text_mode is not None:
            detail = f"{detail} mode={action.text_mode}"
        if action.dismiss_keyboard is not None:
            detail = f"{detail} dismiss_keyboard={str(action.dismiss_keyboard).lower()}"
        return detail
    if action.type == ActionType.SET_VALUE and action.text:
        detail = f"value={action.text!r}"
        if action.target_ref is not None:
            detail = f"{detail} target_ref={action.target_ref}"
        if action.handle is not None and action.handle.fill_mode is not None:
            detail = f"{detail} fill_mode={action.handle.fill_mode}"
        return detail
    if action.type == ActionType.LONG_PRESS:
        if action.duration is not None:
            return f"duration={action.duration:g}"
        return None
    if action.type == ActionType.DRAG and action.start is not None and action.end is not None:
        detail = f"start={action.start} end={action.end}"
        if action.duration is not None:
            detail = f"{detail} duration={action.duration:g}"
        return detail
    if (
        action.type in {ActionType.SCROLL, ActionType.SWIPE}
        and action.direction is not None
        and action.start_x_ratio is not None
        and action.start_y_ratio is not None
        and action.distance_ratio is not None
    ):
        detail = (
            f"direction={action.direction} start_x_ratio={action.start_x_ratio:g} "
            f"start_y_ratio={action.start_y_ratio:g} "
            f"distance_ratio={action.distance_ratio:g}"
        )
        if action.distance_px is not None:
            detail = f"{detail} distance_px={action.distance_px}"
        if action.start is not None and action.end is not None:
            detail = f"{detail} start={action.start} end={action.end}"
        return detail
    if action.type in {
        ActionType.WAIT_FOR_TEXT,
        ActionType.SCROLL_UNTIL_TEXT,
    } and action.match_type is not None and action.match_texts is not None:
        detail = f"match_type={action.match_type} texts={list(action.match_texts)!r}"
        if action.max_attempts is not None:
            detail = f"{detail} max_attempts={action.max_attempts}"
        if action.duration is not None:
            detail = f"{detail} timeout={action.duration:g}"
        if action.direction is not None:
            detail = f"{detail} direction={action.direction}"
        return detail
    if action.type == ActionType.WAIT and action.duration is not None:
        return f"duration={action.duration:g}"
    return None


def canonical_action_summary(action: Action) -> str:
    if action.summary:
        cleaned = action.summary.strip()
        if cleaned:
            return cleaned
    if action.type in {ActionType.INPUT, ActionType.EDIT_TEXT} and action.text:
        prefix = "edit_text" if action.type == ActionType.EDIT_TEXT else "input"
        return f"{prefix} | {action.text}"
    if action.type == ActionType.SET_VALUE and action.text:
        return f"set_value | {action.text}"
    if action.type == ActionType.CLICK:
        return "click"
    if action.type == ActionType.LONG_PRESS:
        return "long_press"
    if action.type == ActionType.SCROLL:
        return "scroll"
    if action.type == ActionType.SWIPE:
        return "swipe"
    if action.type == ActionType.DRAG:
        return "drag"
    if action.type == ActionType.DISMISS_SOFT_KEYBOARD:
        return "dismiss_soft_keyboard"
    if action.type == ActionType.WAIT_FOR_TEXT:
        return "wait_for_text"
    if action.type == ActionType.SCROLL_UNTIL_TEXT:
        return "scroll_until_text"
    if action.type == ActionType.BACK:
        return "back"
    if action.type == ActionType.HOME:
        return "home"
    if action.type == ActionType.RESTART_APP:
        return "restart_app"
    if action.type == ActionType.WAIT:
        return "wait"
    if action.type == ActionType.REDETECT:
        return "redetect"
    if action.type == ActionType.STOP:
        return "stop"
    return action.type.value


def build_action_history_entry(
    action: Action,
    *,
    relative_time_sec: float | None = None,
) -> ActionHistoryEntry:
    summary = canonical_action_summary(action)
    target_label = summary if action.type in {ActionType.CLICK, ActionType.LONG_PRESS} else None
    return ActionHistoryEntry(
        action_type=action.type.value,
        target_id=None,
        target_label=target_label,
        summary=summary,
        relative_time_sec=relative_time_sec,
        detail=action_history_detail(action),
    )


def build_memory_history_entry(*, operation: str, key: str, summary: str) -> ActionHistoryEntry:
    return ActionHistoryEntry(
        action_type="memory",
        target_id=None,
        target_label=None,
        summary=f"{operation}d memory",
        detail=f"key={key}",
        memory_operation=operation,
        memory_key=key,
        memory_summary=summary,
    )


def format_history_entries(entries: list[ActionHistoryEntry]) -> str:
    if not entries:
        return "none"
    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        item = f"{index}) {_format_history_time(entry)}{entry.action_type} | {entry.summary}"
        if entry.detail:
            item = f"{item} | detail={entry.detail}"
        if entry.outcome_summary:
            item = f"{item} | outcome={entry.outcome_summary}"
        lines.append(item)
    return "\n".join(lines)


def build_history_artifact(entries: list[ActionHistoryEntry], *, max_entries: int = 10) -> list[dict[str, Any]]:
    recent_entries = entries[-max_entries:]
    artifact: list[dict[str, Any]] = []
    total = len(entries)
    for reverse_index, entry in enumerate(reversed(recent_entries)):
        item = entry.to_compact_dict()
        item["step_index"] = total - reverse_index - 1
        artifact.append(item)
    return artifact


def _format_history_time(entry: ActionHistoryEntry) -> str:
    if entry.relative_time_sec is None:
        return ""
    return f"t+{entry.relative_time_sec:.1f}s | "
