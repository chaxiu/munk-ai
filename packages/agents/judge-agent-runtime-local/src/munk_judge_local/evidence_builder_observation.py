from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast

from munk.judging.models import JudgeEvidence, JudgeScreenDiffEvidence, JudgeScreenFrameEvidence

from munk.core.compact_tree import build_compact_tree

from .evidence_builder_parsers import (
    _dict_list,
    _screen_diff_payload,
    _screen_frame_payload,
)
from .focus_terms import count_focus_matches
from .tree_excerpt import build_focus_compact_tree

SCREEN_FRAME_WINDOW = 3
SCREEN_DIFF_WINDOW = 5


def _build_observation_evidence(
    kind: str,
    directory_value: str | None,
    focus_terms: list[str],
    *,
    tree_directory_value: str | None = None,
) -> list[JudgeEvidence]:
    if not directory_value:
        return []
    directory = Path(directory_value)
    if not directory.exists() or not directory.is_dir():
        return []
    files = sorted(path for path in directory.iterdir() if path.suffix == ".json")
    if not files:
        return []

    evidence: list[JudgeEvidence] = []
    selected_files = files[-SCREEN_FRAME_WINDOW:] if kind == "screen_frame" else files[-SCREEN_DIFF_WINDOW:]
    for path in selected_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"raw": path.read_text(encoding="utf-8")}
        tree_parent_map = (
            _load_tree_parent_map(tree_directory_value=tree_directory_value, step_stem=path.stem)
            if kind == "screen_frame"
            else {}
        )
        excerpt = _build_observation_excerpt(kind, payload, focus_terms, tree_parent_map=tree_parent_map)
        summary = _build_observation_summary(kind, path.name, payload, excerpt)
        step_index = _step_index_from_name(path.stem)
        if kind == "screen_diff":
            evidence.append(
                JudgeScreenDiffEvidence(
                    evidence_id=f"{kind}-{path.stem}",
                    kind="screen_diff",
                    source="artifact",
                    summary=summary,
                    payload=_screen_diff_payload(
                        path=path,
                        step_index=step_index,
                        payload=payload,
                        excerpt=excerpt,
                    ),
                )
            )
            continue
        evidence.append(
            JudgeScreenFrameEvidence(
                evidence_id=f"{kind}-{path.stem}",
                kind="screen_frame",
                source="artifact",
                summary=summary,
                payload=_screen_frame_payload(
                    path=path,
                    step_index=step_index,
                    excerpt=excerpt,
                ),
            )
        )
    return evidence


def _build_observation_summary(
    kind: str,
    file_name: str,
    payload: object,
    excerpt: dict[str, object],
) -> str:
    if kind == "screen_diff":
        data = cast(dict[str, object], payload) if isinstance(payload, dict) else {}
        summary = str(data.get("summary", "")).strip()
        if summary:
            return f"{kind} artifact: {summary}"
        labels_obj = excerpt.get("appeared_labels") or excerpt.get("updated_labels")
        if isinstance(labels_obj, list) and labels_obj:
            labels = [str(label) for label in cast(list[object], labels_obj[:2])]
            joined = ", ".join(labels)
            return f"{kind} artifact: {joined}"
    if kind == "screen_frame":
        focus_hits = _dict_list(excerpt.get("focus_hits"))
        if focus_hits:
            labels: list[str] = []
            for item in focus_hits[:2]:
                label = item.get("label")
                if label:
                    labels.append(str(label))
            if labels:
                return f"{kind} artifact: focus_hits={', '.join(labels)}"
        if isinstance(payload, dict):
            tree_summary = str(payload.get("tree_summary", "")).strip()
            if tree_summary:
                return f"{kind} artifact: {tree_summary}"
    return f"{kind} artifact: {file_name}"


def _build_observation_excerpt(
    kind: str,
    payload: object,
    focus_terms: list[str],
    *,
    tree_parent_map: dict[str, str | None] | None = None,
) -> dict[str, object]:
    data = cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    if kind == "screen_diff":
        return {
            "summary": data.get("summary"),
            "appeared_labels": _collect_change_labels(data.get("appeared_nodes")),
            "updated_labels": _collect_change_labels(data.get("updated_nodes")),
            "disappeared_labels": _collect_change_labels(data.get("disappeared_nodes")),
            "linked_visual_changes": list(cast(list[object], data.get("linked_visual_changes", [])))[:4]
            if isinstance(data.get("linked_visual_changes"), list)
            else [],
        }
    return {
        "package": data.get("package"),
        "tree_available": data.get("tree_available"),
        "tree_summary": data.get("tree_summary"),
        "compact_tree": _build_compact_tree_excerpt(
            data.get("tree_nodes"),
            focus_terms,
            tree_parent_map=tree_parent_map or {},
        ),
        "focus_hits": _extract_focus_hits(data.get("tree_nodes"), focus_terms),
    }


def _collect_change_labels(raw_changes: object) -> list[str]:
    labels: list[str] = []
    for item in _dict_list(raw_changes)[:4]:
        label = item.get("label")
        if label:
            labels.append(str(label))
    return labels


def _extract_focus_hits(raw_nodes: object, focus_terms: list[str]) -> list[dict[str, object]]:
    ranked_nodes: list[tuple[int, dict[str, object]]] = []
    for item in _dict_list(raw_nodes):
        searchable = " ".join(
            str(item.get(field, "")).strip()
            for field in ("text", "content_desc", "resource_id", "stable_key", "class_name")
        )
        score = count_focus_matches(searchable, focus_terms)
        if score <= 0:
            continue
        ranked_nodes.append(
            (
                score,
                {
                    "node_id": item.get("node_id"),
                    "label": item.get("text") or item.get("content_desc") or item.get("resource_id") or item.get("class_name"),
                    "score": score,
                },
            )
        )
    ranked_nodes.sort(key=lambda item: item[0], reverse=True)
    return [node for _, node in ranked_nodes[:6]]


def _build_compact_tree_excerpt(
    raw_nodes: object,
    focus_terms: list[str],
    *,
    tree_parent_map: dict[str, str | None],
) -> dict[str, object]:
    compact_tree = build_compact_tree(raw_nodes, tree_parent_map=tree_parent_map)
    compact_tree["focus_term_count"] = len(focus_terms)
    focus_hits = _extract_focus_hits(raw_nodes, focus_terms)
    return build_focus_compact_tree(compact_tree, focus_hits=focus_hits)


def _load_tree_parent_map(
    *,
    tree_directory_value: str | None,
    step_stem: str,
) -> dict[str, str | None]:
    if not tree_directory_value:
        return {}
    tree_path = Path(tree_directory_value) / f"{step_stem}.xml"
    if not tree_path.exists():
        return {}
    try:
        root = ET.fromstring(tree_path.read_text(encoding="utf-8"))
    except ET.ParseError:
        return {}

    xml_entries: list[tuple[tuple[object, ...], tuple[object, ...] | None]] = []

    def visit(element: ET.Element, parent_signature: tuple[object, ...] | None) -> None:
        if element.tag != "node":
            for child in list(element):
                visit(child, parent_signature)
            return
        signature = _xml_node_signature(element)
        xml_entries.append((signature, parent_signature))
        for child in list(element):
            visit(child, signature)

    visit(root, None)
    parent_by_signature_occurrence: dict[tuple[tuple[object, ...], int], tuple[object, ...] | None] = {}
    signature_counts: dict[tuple[object, ...], int] = {}
    for signature, parent_signature in xml_entries:
        occurrence = signature_counts.get(signature, 0)
        parent_by_signature_occurrence[(signature, occurrence)] = parent_signature
        signature_counts[signature] = occurrence + 1

    frame_path = Path(tree_directory_value).parent / "frames" / f"{step_stem}.json"
    if not frame_path.exists():
        return {}
    try:
        frame_payload = json.loads(frame_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    raw_payload = cast(dict[str, object], frame_payload) if isinstance(frame_payload, dict) else {}
    raw_node_items = _dict_list(raw_payload.get("tree_nodes"))
    if not raw_node_items:
        return {}

    node_counts: dict[tuple[object, ...], int] = {}
    node_id_by_signature_occurrence: dict[tuple[tuple[object, ...], int], str] = {}
    ordered_nodes: list[tuple[str, tuple[object, ...], int]] = []
    for item in raw_node_items:
        node_id = str(item.get("node_id") or "")
        signature = _frame_node_signature(item)
        occurrence = node_counts.get(signature, 0)
        node_counts[signature] = occurrence + 1
        node_id_by_signature_occurrence[(signature, occurrence)] = node_id
        ordered_nodes.append((node_id, signature, occurrence))

    parent_map: dict[str, str | None] = {}
    for node_id, signature, occurrence in ordered_nodes:
        parent_signature = parent_by_signature_occurrence.get((signature, occurrence))
        if parent_signature is None:
            parent_map[node_id] = None
            continue
        parent_node_id = node_id_by_signature_occurrence.get((parent_signature, 0))
        if parent_node_id is None:
            parent_node_id = _find_matching_node_id(parent_signature, node_id_by_signature_occurrence)
        parent_map[node_id] = parent_node_id
    return parent_map


def _xml_node_signature(element: ET.Element) -> tuple[object, ...]:
    return (
        element.attrib.get("package") or None,
        element.attrib.get("class") or None,
        element.attrib.get("resource-id") or None,
        element.attrib.get("text") or None,
        element.attrib.get("content-desc") or None,
        element.attrib.get("bounds") or None,
    )


def _frame_node_signature(item: dict[str, object]) -> tuple[object, ...]:
    bounds = item.get("bounds")
    bounds_text = None
    if isinstance(bounds, list | tuple) and len(bounds) == 4:
        bounds_text = f"[{bounds[0]},{bounds[1]}][{bounds[2]},{bounds[3]}]"
    return (
        item.get("package_name"),
        item.get("class_name"),
        item.get("resource_id"),
        item.get("text"),
        item.get("content_desc"),
        bounds_text,
    )


def _find_matching_node_id(
    signature: tuple[object, ...],
    node_id_by_signature_occurrence: dict[tuple[tuple[object, ...], int], str],
) -> str | None:
    matches = [
        node_id
        for (candidate_signature, _), node_id in node_id_by_signature_occurrence.items()
        if candidate_signature == signature
    ]
    return matches[0] if matches else None


def _step_index_from_name(name: str) -> int:
    parts = name.rsplit("_", maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        return -1
    return int(parts[1])
