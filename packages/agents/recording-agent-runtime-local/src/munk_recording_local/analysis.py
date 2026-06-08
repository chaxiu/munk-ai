from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, cast

from munk.recording import (
    RecordingAnalysisScreenshotRef,
    RecordingAnalysisTreeExcerpt,
    RecordingAnalysisTreeFocusHit,
    RecordingAnalysisTreeNode,
)

from .store import RecordingStore

MAX_FOCUS_HITS = 6
MAX_COMPACT_NODES = 24
MAX_DIFF_FOCUS_HITS = 4
MAX_DIFF_NODES = 8


def build_recording_asset_bundle(
    store: RecordingStore,
    *,
    recording_id: str,
) -> dict[str, Any]:
    recording_dir = store.find_recording_dir(recording_id)
    session = store.read_session(recording_dir)
    manifest = store.read_manifest(recording_dir)
    forwarding_events = store.read_forwarding_events(recording_dir)
    recording_events = store.read_events(recording_dir)
    timeline = store.read_timeline(recording_dir)
    forwarding_by_id = {event.forwarding_event_id: event for event in forwarding_events}
    recording_by_id = {event.event_id: event for event in recording_events}
    observations: dict[str, dict[str, Any]] = {}
    for observation_id in _list_observation_ids(store, recording_dir):
        observation = store.read_observation(recording_dir, observation_id)
        tree_text = store.read_observation_tree_text(recording_dir, observation_id)
        observations[observation_id] = {
            "observation": observation.model_dump(mode="json"),
            "metadata": store.read_observation_metadata(recording_dir, observation_id),
            "tree_text": tree_text,
        }
    steps: list[dict[str, Any]] = []
    for entry in timeline:
        before_payload = observations.get(entry.before_observation_id)
        after_payload = observations.get(entry.after_observation_id)
        if before_payload is None or after_payload is None:
            continue
        before_observation = cast(dict[str, Any], before_payload["observation"])
        after_observation = cast(dict[str, Any], after_payload["observation"])
        forwarding_event = forwarding_by_id.get(entry.forwarding_event_id)
        recording_event = recording_by_id.get(entry.recording_event_id)
        focus_terms = _build_focus_terms(
            entry_payload=entry.model_dump(mode="json"),
            recording_event=recording_event.model_dump(mode="json") if recording_event is not None else None,
            forwarding_event=forwarding_event.model_dump(mode="json") if forwarding_event is not None else None,
        )
        before_excerpt = _build_compact_tree_excerpt(cast(str | None, before_payload.get("tree_text")), focus_terms)
        after_excerpt = _build_compact_tree_excerpt(cast(str | None, after_payload.get("tree_text")), focus_terms)
        before_excerpt_payload = before_excerpt.model_dump(mode="json") if before_excerpt else None
        after_excerpt_payload = after_excerpt.model_dump(mode="json") if after_excerpt else None
        before_payload["compact_tree_excerpt"] = before_excerpt_payload
        after_payload["compact_tree_excerpt"] = after_excerpt_payload
        tree_diff = _build_tree_diff(before_excerpt, after_excerpt)
        before_ref = RecordingAnalysisScreenshotRef(
            recording_id=recording_id,
            entry_id=entry.entry_id,
            seq=entry.seq,
            role="before",
            observation_id=entry.before_observation_id,
            path=store.observation_image_path(recording_dir, entry.before_observation_id),
            entry_identity=before_observation.get("entry_identity"),
            surface_identity=before_observation.get("surface_identity"),
            summary=_observation_summary(before_observation),
            tree_available=bool(before_observation.get("tree_available")),
            tree_evidence_id=f"observation-{entry.before_observation_id}",
            compact_tree_excerpt=before_excerpt,
        )
        after_ref = RecordingAnalysisScreenshotRef(
            recording_id=recording_id,
            entry_id=entry.entry_id,
            seq=entry.seq,
            role="after",
            observation_id=entry.after_observation_id,
            path=store.observation_image_path(recording_dir, entry.after_observation_id),
            entry_identity=after_observation.get("entry_identity"),
            surface_identity=after_observation.get("surface_identity"),
            summary=_observation_summary(after_observation),
            tree_available=bool(after_observation.get("tree_available")),
            tree_evidence_id=f"observation-{entry.after_observation_id}",
            compact_tree_excerpt=after_excerpt,
        )
        steps.append(
            {
                "entry": entry.model_dump(mode="json"),
                "forwarding_event": forwarding_event.model_dump(mode="json") if forwarding_event is not None else None,
                "recording_event": recording_event.model_dump(mode="json") if recording_event is not None else None,
                "before_observation": before_payload,
                "after_observation": after_payload,
                "tree_diff": tree_diff,
                "before_screenshot": before_ref.model_dump(mode="json"),
                "after_screenshot": after_ref.model_dump(mode="json"),
            }
        )
    return {
        "recording_id": recording_id,
        "recording_dir": str(recording_dir),
        "session": session.model_dump(mode="json"),
        "manifest": manifest.model_dump(mode="json"),
        "forwarding_events": [event.model_dump(mode="json") for event in forwarding_events],
        "recording_events": [event.model_dump(mode="json") for event in recording_events],
        "timeline": [entry.model_dump(mode="json") for entry in timeline],
        "observations": observations,
        "steps": steps,
        "source_summary": _source_summary(session.model_dump(mode="json"), timeline_count=len(timeline)),
    }


def _list_observation_ids(store: RecordingStore, recording_dir) -> list[str]:  # noqa: ANN001
    root = store.observations_dir(recording_dir)
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def _observation_summary(payload: dict[str, Any]) -> str:
    entry_identity = payload.get("entry_identity") or "unknown"
    surface_identity = payload.get("surface_identity") or "unknown"
    return f"{entry_identity} {surface_identity}".strip()


def _build_focus_terms(
    *,
    entry_payload: dict[str, Any],
    recording_event: dict[str, Any] | None,
    forwarding_event: dict[str, Any] | None,
) -> list[str]:
    candidates: list[str] = []
    for payload in (entry_payload, recording_event or {}, forwarding_event or {}):
        summary = payload.get("summary")
        if isinstance(summary, str):
            candidates.append(summary)
        raw_payload = payload.get("payload")
        if isinstance(raw_payload, dict):
            payload_values = list(cast(dict[str, object], raw_payload).values())
            for value in payload_values:
                if isinstance(value, str):
                    candidates.append(value)
    seen: set[str] = set()
    terms: list[str] = []
    for candidate in candidates:
        for token in re.findall(r"[A-Za-z0-9_]+", candidate.lower()):
            if len(token) < 3 or token in seen:
                continue
            seen.add(token)
            terms.append(token)
            if len(terms) >= 12:
                return terms
    return terms


def _build_compact_tree_excerpt(
    tree_text: str | None,
    focus_terms: list[str],
) -> RecordingAnalysisTreeExcerpt | None:
    if not tree_text:
        return None
    try:
        root = ET.fromstring(tree_text)
    except ET.ParseError:
        return None
    nodes: list[RecordingAnalysisTreeNode] = []
    focus_hits: list[tuple[int, RecordingAnalysisTreeFocusHit]] = []
    parents: dict[str, str | None] = {}
    node_index = 0

    def visit(element: ET.Element, parent_id: str | None) -> None:
        nonlocal node_index
        if element.tag != "node":
            for child in list(element):
                visit(child, parent_id)
            return
        node_index += 1
        node_id = f"node_{node_index:04d}"
        node = RecordingAnalysisTreeNode(
            node_id=node_id,
            parent_id=parent_id,
            stable_key=_stable_key_from_xml(element),
            class_name=_xml_attr(element, "class"),
            resource_id=_xml_attr(element, "resource-id"),
            text=_xml_attr(element, "text"),
            content_desc=_xml_attr(element, "content-desc"),
            bounds=_parse_bounds(_xml_attr(element, "bounds")),
            state=_sparse_state_from_xml(element),
        )
        nodes.append(node)
        parents[node_id] = parent_id
        score = _focus_score(node, focus_terms)
        if score > 0:
            focus_hits.append(
                (
                    score,
                    RecordingAnalysisTreeFocusHit(
                        node_id=node_id,
                        label=node.text or node.content_desc or node.resource_id or node.class_name or node_id,
                        score=score,
                    ),
                )
            )
        for child in list(element):
            visit(child, node_id)

    visit(root, None)
    focus_hits.sort(key=lambda item: (-item[0], item[1].node_id or ""))
    selected_ids = _select_compact_node_ids(nodes, parents=parents, focus_hits=focus_hits)
    return RecordingAnalysisTreeExcerpt(
        node_count=len(nodes),
        focus_hits=[hit for _, hit in focus_hits[:MAX_FOCUS_HITS]],
        compact_nodes=[node for node in nodes if node.node_id in selected_ids],
    )


def _select_compact_node_ids(
    nodes: list[RecordingAnalysisTreeNode],
    *,
    parents: dict[str, str | None],
    focus_hits: list[tuple[int, RecordingAnalysisTreeFocusHit]],
) -> set[str]:
    selected_ids: set[str] = set()
    nodes_by_id = {node.node_id: node for node in nodes}

    for _, hit in focus_hits[:MAX_FOCUS_HITS]:
        node_id = hit.node_id
        if node_id is None or node_id not in nodes_by_id:
            continue
        current_id: str | None = node_id
        while current_id is not None and current_id not in selected_ids:
            selected_ids.add(current_id)
            current_id = parents.get(current_id)

    if not selected_ids:
        for node in nodes[: min(len(nodes), 12)]:
            selected_ids.add(node.node_id)

    if len(selected_ids) >= MAX_COMPACT_NODES:
        limited_ids = {node.node_id for node in nodes if node.node_id in selected_ids}
        return set(list(limited_ids)[:MAX_COMPACT_NODES])

    for node in nodes:
        if len(selected_ids) >= MAX_COMPACT_NODES:
            break
        if node.node_id in selected_ids:
            continue
        if node.parent_id in selected_ids:
            selected_ids.add(node.node_id)
    return selected_ids


def _xml_attr(element: ET.Element, key: str) -> str | None:
    value = element.attrib.get(key)
    return value if value else None


def _stable_key_from_xml(element: ET.Element) -> str | None:
    resource_id = _xml_attr(element, "resource-id")
    if resource_id:
        return f"rid:{resource_id}"
    class_name = _xml_attr(element, "class")
    text = _xml_attr(element, "text")
    content_desc = _xml_attr(element, "content-desc")
    label = text or content_desc
    if class_name and label:
        return f"{class_name}:{label}"
    return class_name or label


def _parse_bounds(bounds: str | None) -> list[int] | None:
    if not bounds:
        return None
    matches = re.findall(r"-?\d+", bounds)
    if len(matches) != 4:
        return None
    return [int(value) for value in matches]


def _sparse_state_from_xml(element: ET.Element) -> dict[str, Any]:
    class_name = (_xml_attr(element, "class") or "").lower()
    state: dict[str, Any] = {}

    def attr_is_true(name: str) -> bool:
        return (_xml_attr(element, name) or "").lower() == "true"

    if any(token in class_name for token in ("checkbox", "switch", "radiobutton")):
        state["checkable"] = attr_is_true("checkable")
        state["checked"] = attr_is_true("checked")
        state["enabled"] = not (_xml_attr(element, "enabled") or "").lower() == "false"
        if _xml_attr(element, "clickable") is not None:
            state["clickable"] = attr_is_true("clickable")
        return state
    if "edittext" in class_name:
        state["enabled"] = not (_xml_attr(element, "enabled") or "").lower() == "false"
        if attr_is_true("focused"):
            state["focused"] = True
        return state
    for attr_name in ("clickable", "focused", "selected", "scrollable"):
        if attr_is_true(attr_name):
            state[attr_name] = True
    if (_xml_attr(element, "enabled") or "").lower() == "false":
        state["enabled"] = False
    return state


def _focus_score(node: RecordingAnalysisTreeNode, focus_terms: list[str]) -> int:
    if not focus_terms:
        return 0
    searchable = " ".join(
        value.lower()
        for value in (node.text, node.content_desc, node.resource_id, node.stable_key, node.class_name)
        if isinstance(value, str) and value
    )
    return sum(1 for term in focus_terms if term in searchable)


def _build_tree_diff(
    before_excerpt: RecordingAnalysisTreeExcerpt | None,
    after_excerpt: RecordingAnalysisTreeExcerpt | None,
) -> dict[str, Any]:
    if before_excerpt is None or after_excerpt is None:
        return {
            "before_node_count": before_excerpt.node_count if before_excerpt is not None else 0,
            "after_node_count": after_excerpt.node_count if after_excerpt is not None else 0,
            "added_focus_hits": [],
            "removed_focus_hits": [],
            "changed_focus_hits": [],
            "added_nodes": [],
            "removed_nodes": [],
            "changed_nodes": [],
            "summary": "tree diff unavailable",
        }

    before_focus = _focus_hit_map(before_excerpt.focus_hits)
    after_focus = _focus_hit_map(after_excerpt.focus_hits)
    before_nodes = _node_map(before_excerpt.compact_nodes)
    after_nodes = _node_map(after_excerpt.compact_nodes)

    added_focus_keys = sorted(set(after_focus) - set(before_focus))
    removed_focus_keys = sorted(set(before_focus) - set(after_focus))
    shared_focus_keys = sorted(set(before_focus) & set(after_focus))
    changed_focus_hits = [
        {
            "before": before_focus[key],
            "after": after_focus[key],
        }
        for key in shared_focus_keys
        if before_focus[key] != after_focus[key]
    ][:MAX_DIFF_FOCUS_HITS]

    added_node_keys = sorted(set(after_nodes) - set(before_nodes))
    removed_node_keys = sorted(set(before_nodes) - set(after_nodes))
    shared_node_keys = sorted(set(before_nodes) & set(after_nodes))
    changed_nodes = [
        changed_node
        for key in shared_node_keys
        if (changed_node := _build_changed_node(before_nodes[key], after_nodes[key])) is not None
    ][:MAX_DIFF_NODES]

    added_focus_hits = [after_focus[key] for key in added_focus_keys[:MAX_DIFF_FOCUS_HITS]]
    removed_focus_hits = [before_focus[key] for key in removed_focus_keys[:MAX_DIFF_FOCUS_HITS]]
    added_nodes = [after_nodes[key] for key in added_node_keys[:MAX_DIFF_NODES]]
    removed_nodes = [before_nodes[key] for key in removed_node_keys[:MAX_DIFF_NODES]]

    return {
        "before_node_count": before_excerpt.node_count,
        "after_node_count": after_excerpt.node_count,
        "added_focus_hits": added_focus_hits,
        "removed_focus_hits": removed_focus_hits,
        "changed_focus_hits": changed_focus_hits,
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "changed_nodes": changed_nodes,
        "summary": _summarize_tree_diff(
            added_focus_hits=added_focus_hits,
            removed_focus_hits=removed_focus_hits,
            changed_focus_hits=changed_focus_hits,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            changed_nodes=changed_nodes,
        ),
    }


def _focus_hit_map(items: list[RecordingAnalysisTreeFocusHit]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item.node_id or item.label
        mapped[key] = item.model_dump(mode="json")
    return mapped


def _node_map(items: list[RecordingAnalysisTreeNode]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item.stable_key or item.node_id
        mapped[key] = item.model_dump(mode="json")
    return mapped


def _build_changed_node(before_node: dict[str, Any], after_node: dict[str, Any]) -> dict[str, Any] | None:
    field_changes: dict[str, dict[str, Any]] = {}
    for field_name in ("text", "content_desc", "resource_id", "state", "bounds"):
        before_value = before_node.get(field_name)
        after_value = after_node.get(field_name)
        if before_value != after_value:
            field_changes[field_name] = {
                "before": before_value,
                "after": after_value,
            }
    if not field_changes:
        return None
    return {
        "stable_key": after_node.get("stable_key") or before_node.get("stable_key"),
        "node_id": after_node.get("node_id") or before_node.get("node_id"),
        "changes": field_changes,
    }


def _summarize_tree_diff(
    *,
    added_focus_hits: list[dict[str, Any]],
    removed_focus_hits: list[dict[str, Any]],
    changed_focus_hits: list[dict[str, Any]],
    added_nodes: list[dict[str, Any]],
    removed_nodes: list[dict[str, Any]],
    changed_nodes: list[dict[str, Any]],
) -> str:
    parts: list[str] = []
    if added_focus_hits:
        parts.append(f"focus+{len(added_focus_hits)}")
    if removed_focus_hits:
        parts.append(f"focus-{len(removed_focus_hits)}")
    if changed_focus_hits:
        parts.append(f"focus~{len(changed_focus_hits)}")
    if added_nodes:
        parts.append(f"nodes+{len(added_nodes)}")
    if removed_nodes:
        parts.append(f"nodes-{len(removed_nodes)}")
    if changed_nodes:
        parts.append(f"nodes~{len(changed_nodes)}")
    return ", ".join(parts) if parts else "no compact tree change"


def _source_summary(session_payload: dict[str, Any], *, timeline_count: int) -> str:
    return (
        f"recording {session_payload.get('recording_id')} "
        f"for app {session_payload.get('app_id')} with {timeline_count} timeline steps"
    )
