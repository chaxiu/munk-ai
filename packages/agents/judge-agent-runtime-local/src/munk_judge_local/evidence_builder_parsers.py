from __future__ import annotations

from pathlib import Path
from typing import cast

from munk.judging.models import (
    JudgeCompactUiNode,
    JudgeCompactUiNodeState,
    JudgeCompactUiTree,
    JudgeFocusHit,
    JudgeRunnerHistoryEntry,
    JudgeRunnerMemoryEntry,
    JudgeRuntimeLogEntry,
    JudgeScreenDiffEvidencePayload,
    JudgeScreenFrameEvidencePayload,
    JudgeScreenNodeChange,
    JsonObject,
    JsonValue,
)


def _dict_list(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, object]] = []
    for candidate in cast(list[object], raw):  # pyright: ignore[reportUnknownVariableType]
        if isinstance(candidate, dict):
            items.append(cast(dict[str, object], candidate))
    return items


def _dict_or_none(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        return None
    return cast(dict[str, object], raw)


def _json_value(raw: object) -> JsonValue:
    if raw is None or isinstance(raw, str | int | float | bool):
        return raw
    if isinstance(raw, list):
        items: list[JsonValue] = []
        for item in cast(list[object], raw):
            items.append(_json_value(item))
        return items
    if isinstance(raw, dict):
        values: JsonObject = {}
        for key, value in raw.items():
            values[str(key)] = _json_value(value)
        return values
    return str(raw)


def _json_object(raw: dict[str, object] | dict[str, str]) -> JsonObject:
    payload: JsonObject = {}
    for key, value in raw.items():
        payload[str(key)] = _json_value(value)
    return payload


def _runner_history_entry(item: dict[str, object]) -> JudgeRunnerHistoryEntry:
    step_index = item.get("step_index")
    return JudgeRunnerHistoryEntry(
        step_index=step_index if isinstance(step_index, int) else None,
        action_type=_string_or_none(item.get("action_type")),
        summary=_string_or_none(item.get("summary")),
        outcome_summary=_string_or_none(item.get("outcome_summary")),
        record=_json_object(item),
    )


def _runner_memory_entry(item: dict[str, object]) -> JudgeRunnerMemoryEntry:
    updated_step_index = item.get("updated_step_index")
    return JudgeRunnerMemoryEntry(
        key=_string_or_none(item.get("key")),
        summary=_string_or_none(item.get("summary")),
        value=_json_value(item.get("value")),
        updated_step_index=updated_step_index if isinstance(updated_step_index, int) else None,
        timestamp=_string_or_none(item.get("timestamp")),
    )


def _runtime_log_entry(item: dict[str, object]) -> JudgeRuntimeLogEntry:
    step_index = item.get("step_index")
    return JudgeRuntimeLogEntry(
        step_index=step_index if isinstance(step_index, int) else None,
        source=_string_or_none(item.get("source")),
        surface_identity=_string_or_none(item.get("surface_identity")),
        message=str(item.get("message", "")).strip(),
    )


def _screen_frame_payload(
    *,
    path: Path,
    step_index: int,
    excerpt: dict[str, object],
) -> JudgeScreenFrameEvidencePayload:
    compact_tree = excerpt.get("compact_tree")
    package = excerpt.get("package")
    tree_available = excerpt.get("tree_available")
    tree_summary = excerpt.get("tree_summary")
    focus_hits = _dict_list(excerpt.get("focus_hits"))
    return JudgeScreenFrameEvidencePayload(
        path=str(path),
        step_index=step_index,
        package=str(package) if package else None,
        tree_available=tree_available if isinstance(tree_available, bool) else None,
        tree_summary=_string_or_none(tree_summary),
        compact_tree=_compact_ui_tree(compact_tree),
        focus_hits=[
            JudgeFocusHit(
                node_id=_string_or_none(item.get("node_id")),
                label=_string_or_none(item.get("label")),
                score=_focus_hit_score(item),
            )
            for item in focus_hits
        ],
    )


def _screen_diff_payload(
    *,
    path: Path,
    step_index: int,
    payload: object,
    excerpt: dict[str, object],
) -> JudgeScreenDiffEvidencePayload:
    data = _dict_or_none(payload) or {}
    return JudgeScreenDiffEvidencePayload(
        path=str(path),
        step_index=step_index,
        summary=_string_or_none(excerpt.get("summary")) or _string_or_none(data.get("summary")),
        appeared_labels=_string_list(excerpt.get("appeared_labels")),
        updated_labels=_string_list(excerpt.get("updated_labels")),
        disappeared_labels=_string_list(excerpt.get("disappeared_labels")),
        linked_visual_changes=_string_list(data.get("linked_visual_changes")),
        appeared_nodes=_screen_node_changes(data.get("appeared_nodes")),
        updated_nodes=_screen_node_changes(data.get("updated_nodes")),
        disappeared_nodes=_screen_node_changes(data.get("disappeared_nodes")),
    )


def _focus_hit_score(item: dict[str, object]) -> int | None:
    score = item.get("score")
    return score if isinstance(score, int) else None


def _compact_ui_tree(raw: object) -> JudgeCompactUiTree:
    raw_tree = _dict_or_none(raw) or {}
    raw_nodes = _dict_list(raw_tree.get("nodes"))
    focus_term_count = raw_tree.get("focus_term_count")
    node_count = raw_tree.get("node_count")
    return JudgeCompactUiTree(
        node_count=node_count if isinstance(node_count, int) else len(raw_nodes),
        focus_term_count=focus_term_count if isinstance(focus_term_count, int) else None,
        nodes=[_compact_ui_node(item) for item in raw_nodes],
    )


def _compact_ui_node(item: dict[str, object]) -> JudgeCompactUiNode:
    bounds_values: list[int] = []
    bounds = item.get("b")
    if isinstance(bounds, list):
        for value in cast(list[object], bounds):
            if isinstance(value, int):
                bounds_values.append(value)
    return JudgeCompactUiNode(
        node_id=_string_or_none(item.get("id")),
        stable_key=_string_or_none(item.get("sk")),
        parent_node_id=_string_or_none(item.get("pid")),
        class_name=_string_or_none(item.get("cls")),
        resource_id=_string_or_none(item.get("rid")),
        text=_string_or_none(item.get("txt")),
        content_desc=_string_or_none(item.get("cd")),
        bounds=bounds_values,
        state=_compact_ui_node_state(item.get("state")),
        role=_string_or_none(item.get("role")),
        visual_ids=_string_list(item.get("visual_ids")),
    )


def _compact_ui_node_state(raw: object) -> JudgeCompactUiNodeState:
    state = _dict_or_none(raw) or {}
    clickable = state.get("clickable")
    enabled = state.get("enabled")
    checkable = state.get("checkable")
    checked = state.get("checked")
    focused = state.get("focused")
    selected = state.get("selected")
    scrollable = state.get("scrollable")
    return JudgeCompactUiNodeState(
        clickable=clickable if isinstance(clickable, bool) else None,
        enabled=enabled if isinstance(enabled, bool) else None,
        checkable=checkable if isinstance(checkable, bool) else None,
        checked=checked if isinstance(checked, bool) else None,
        focused=focused if isinstance(focused, bool) else None,
        selected=selected if isinstance(selected, bool) else None,
        scrollable=scrollable if isinstance(scrollable, bool) else None,
    )


def _screen_node_changes(raw: object) -> list[JudgeScreenNodeChange]:
    return [_screen_node_change(item) for item in _dict_list(raw)]


def _screen_node_change(item: dict[str, object]) -> JudgeScreenNodeChange:
    return JudgeScreenNodeChange(
        change_type=_string_or_none(item.get("change_type")),
        stable_key=_string_or_none(item.get("stable_key")),
        label=_string_or_none(item.get("label")),
    )


def _string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    items: list[str] = []
    for item in cast(list[object], raw):
        if isinstance(item, str):
            items.append(str(item))
    return items


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
