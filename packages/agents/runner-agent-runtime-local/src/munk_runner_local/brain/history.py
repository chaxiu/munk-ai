from __future__ import annotations

from typing import Any

from munk.agent_base.action import Action, ActionType
from munk.agent_base.base import ActionHistoryEntry


def action_history_detail(action: Action) -> str | None:
    if action.type == ActionType.INPUT and action.text:
        detail = f"text={action.text!r}"
        if action.dismiss_keyboard is not None:
            detail = f"{detail} dismiss_keyboard={str(action.dismiss_keyboard).lower()}"
        return detail
    if action.type == ActionType.CLEAR_AND_INPUT and action.text:
        detail = f"text={action.text!r}"
        if action.dismiss_keyboard is not None:
            detail = f"{detail} dismiss_keyboard={str(action.dismiss_keyboard).lower()}"
        return detail
    if action.type == ActionType.LONG_PRESS:
        if action.duration is not None:
            return f"duration={action.duration:g}"
        return None
    if action.type in {ActionType.SCROLL, ActionType.SWIPE} and action.direction is not None and action.distance_px is not None:
        detail = f"direction={action.direction} distance_px={action.distance_px}"
        if action.start is not None and action.end is not None:
            detail = f"{detail} start={action.start} end={action.end}"
        return detail
    if action.type in {
        ActionType.WAIT_FOR_ELEMENT,
        ActionType.WAIT_UNTIL_GONE,
        ActionType.SCROLL_UNTIL_VISIBLE,
    } and action.locator is not None:
        detail = action.locator.summary()
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
    if action.type == ActionType.INPUT and action.text:
        return f"input | {action.text}"
    if action.type == ActionType.CLEAR_AND_INPUT and action.text:
        return f"clear_and_input | {action.text}"
    if action.type == ActionType.CLICK:
        return "click"
    if action.type == ActionType.LONG_PRESS:
        return "long_press"
    if action.type == ActionType.SCROLL:
        return "scroll"
    if action.type == ActionType.SWIPE:
        return "swipe"
    if action.type == ActionType.DISMISS_SOFT_KEYBOARD:
        return "dismiss_soft_keyboard"
    if action.type == ActionType.WAIT_FOR_ELEMENT:
        return "wait_for_element"
    if action.type == ActionType.WAIT_UNTIL_GONE:
        return "wait_until_gone"
    if action.type == ActionType.SCROLL_UNTIL_VISIBLE:
        return "scroll_until_visible"
    if action.type == ActionType.BACK:
        return "back"
    if action.type == ActionType.HOME:
        return "home"
    if action.type == ActionType.WAIT:
        return "wait"
    if action.type == ActionType.REDETECT:
        return "redetect"
    if action.type == ActionType.STOP:
        return "stop"
    return action.type.value


def build_action_history_entry(action: Action) -> ActionHistoryEntry:
    summary = canonical_action_summary(action)
    target_label = summary if action.type in {ActionType.CLICK, ActionType.LONG_PRESS} else None
    return ActionHistoryEntry(
        action_type=action.type.value,
        target_id=None,
        target_label=target_label,
        summary=summary,
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
        item = f"{index}) {entry.action_type} | {entry.summary}"
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
