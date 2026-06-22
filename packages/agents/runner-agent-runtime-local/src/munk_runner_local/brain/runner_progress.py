from __future__ import annotations

import re

from munk.agent_base.base import ActionHistoryEntry, ScreenState

_TEXT_DETAIL_RE = re.compile(r"text=(?P<quote>['\"])(?P<value>.*?)(?P=quote)")


def build_goal_progress_summary(entries: list[ActionHistoryEntry], screen: ScreenState) -> str:
    recent_entries = entries[-3:]
    if not recent_entries:
        return "progress_state=unknown\nlatest_input_text=none\nlatest_input_visible_on_screen=n/a"

    latest_outcome = _latest_outcome_summary(recent_entries)
    recent_input_texts = _recent_input_texts(recent_entries)
    visible_recent_inputs = [text for text in recent_input_texts if _screen_contains_text(screen, text)]

    lines = [
        f"progress_state={_classify_progress_state(latest_outcome, visible_recent_inputs)}",
    ]
    if recent_input_texts:
        lines.append(f"latest_input_text={recent_input_texts[0]!r}")
        lines.append(
            "latest_input_visible_on_screen="
            + ("yes" if recent_input_texts[0] in visible_recent_inputs else "no")
        )
    else:
        lines.append("latest_input_text=none")
        lines.append("latest_input_visible_on_screen=n/a")
    if visible_recent_inputs:
        lines.append(
            "visible_recent_inputs=" + ", ".join(repr(text) for text in visible_recent_inputs[:2])
        )
    return "\n".join(lines)


def build_prompt_history_summary(entries: list[ActionHistoryEntry]) -> str:
    recent_entries = entries[-3:]
    if not recent_entries:
        return "none"
    lines = [f"recent_action_chain={' -> '.join(entry.action_type for entry in recent_entries)}"]
    for index, entry in enumerate(recent_entries, start=1):
        item = f"{index}) {_format_history_time(entry)}{entry.action_type} | {entry.summary}"
        if entry.detail:
            item = f"{item} | detail={entry.detail}"
        if entry.outcome_summary:
            item = f"{item} | outcome={entry.outcome_summary}"
        lines.append(item)
    return "\n".join(lines)


def _latest_outcome_summary(entries: list[ActionHistoryEntry]) -> str:
    for entry in reversed(entries):
        if entry.outcome_summary:
            return entry.outcome_summary
    return "none"


def _recent_input_texts(entries: list[ActionHistoryEntry]) -> list[str]:
    texts: list[str] = []
    for entry in reversed(entries):
        if entry.action_type not in {"input", "edit_text"}:
            continue
        if not entry.detail:
            continue
        match = _TEXT_DETAIL_RE.search(entry.detail)
        if match is None:
            continue
        text = match.group("value").strip()
        if text and text not in texts:
            texts.append(text)
    return texts


def _screen_contains_text(screen: ScreenState, expected: str) -> bool:
    candidate = _normalize_progress_text(expected)
    if not candidate:
        return False
    frame = screen.screen_frame
    if frame is not None:
        for node in frame.tree_nodes:
            if _normalize_progress_text(node.text) == candidate:
                return True
    for element in screen.elements:
        if _normalize_progress_text(element.text) == candidate:
            return True
    return False


def _normalize_progress_text(value: str | None) -> str:
    if not value:
        return ""
    collapsed = " ".join(value.split()).casefold()
    return "".join(ch for ch in collapsed if ch.isalnum())


def _classify_progress_state(latest_outcome: str, visible_recent_inputs: list[str]) -> str:
    if visible_recent_inputs:
        return "result_visible"
    normalized = latest_outcome.lower()
    if normalized == "none":
        return "unknown"
    if "warning=" in normalized or "screen_changed=no" in normalized:
        return "stalled"
    if "screen_changed=yes" in normalized:
        return "advanced"
    return "unknown"


def _format_history_time(entry: ActionHistoryEntry) -> str:
    if entry.relative_time_sec is None:
        return ""
    return f"t+{entry.relative_time_sec:.1f}s | "
