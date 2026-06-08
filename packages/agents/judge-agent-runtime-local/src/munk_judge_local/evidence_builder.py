from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal, cast

from munk.judging.models import (
    JudgeEventRecord,
    JudgeEvidence,
    JudgeExecutionSummary,
    JudgeRequest,
)

from munk.core.compact_tree import build_compact_tree, compact_tree_node, sparse_state_fields

from .focus_terms import count_focus_matches, extract_focus_terms
from .models import JudgeEvidencePack, JudgeScreenshotRef

MAX_PRIMARY_EVIDENCE = 6
SCREEN_FRAME_WINDOW = 3
SCREEN_DIFF_WINDOW = 5
SCREENSHOT_WINDOW = 3
RUNTIME_ERROR_LOG_CHAR_BUDGET = 4096


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


def build_evidence_pack(
    *,
    request: JudgeRequest,
) -> JudgeEvidencePack:
    execution = request.execution
    events = request.events
    artifacts = _artifacts_from_bundle(request)
    focus_terms = extract_focus_terms(request.intent, request.runner_goal, *request.expected)
    execution_evidence = JudgeEvidence(
        evidence_id="execution",
        kind="execution_outcome",
        source="execution",
        summary=_summarize_execution(execution),
        payload=execution.model_dump(mode="json"),
    )
    supporting_candidates: list[JudgeEvidence] = []
    supporting_candidates.extend(_build_event_evidence(events))
    runner_history_evidence = _build_runner_history_evidence(artifacts.get("runner_history"))
    supporting_candidates.extend(runner_history_evidence)
    runner_memory_evidence = _build_runner_memory_evidence(artifacts.get("runner_memory"))
    supporting_candidates.extend(runner_memory_evidence)
    supporting_candidates.extend(_build_trace_evidence(artifacts.get("decision_trace")))
    runtime_log_evidence = _build_runtime_error_log_evidence(artifacts.get("runtime_logs"))
    supporting_candidates.extend(runtime_log_evidence)
    frame_evidence = _build_observation_evidence(
        "screen_frame",
        artifacts.get("observation_frames"),
        focus_terms,
        tree_directory_value=artifacts.get("observation_tree"),
    )
    supporting_candidates.extend(frame_evidence)
    diff_evidence = _build_observation_evidence(
        "screen_diff",
        artifacts.get("observation_diffs"),
        focus_terms,
    )
    supporting_candidates.extend(diff_evidence)
    recent_raw_screenshots = _build_screenshot_refs(
        kind="raw",
        directory_value=artifacts.get("raw_screenshots"),
        frame_evidence=frame_evidence,
        diff_evidence=diff_evidence,
        runner_history_evidence=runner_history_evidence,
    )
    recent_annotated_screenshots = _build_screenshot_refs(
        kind="annotated",
        directory_value=artifacts.get("annotated_screenshots"),
        frame_evidence=frame_evidence,
        diff_evidence=diff_evidence,
        runner_history_evidence=runner_history_evidence,
    )
    supporting_candidates.extend(_build_screenshot_evidence(recent_raw_screenshots))
    primary_evidence = _select_primary_evidence(supporting_candidates, focus_terms)
    primary_ids = {item.evidence_id for item in primary_evidence}
    supporting_evidence = [item for item in supporting_candidates if item.evidence_id not in primary_ids]
    evidence = [execution_evidence, *primary_evidence, *supporting_evidence]
    return JudgeEvidencePack(
        plan_id=request.plan_id,
        case_id=request.case_id,
        case_title=request.case_title,
        intent=request.intent,
        preconditions=list(request.preconditions),
        expected=list(request.expected),
        runner_goal=request.runner_goal,
        ai_guidance=request.ai_guidance.model_copy(deep=True) if request.ai_guidance is not None else None,
        execution=execution,
        primary_evidence=primary_evidence,
        supporting_evidence=supporting_evidence,
        evidence=evidence,
        runner_memory_summary=_runner_memory_summary(runner_memory_evidence),
        recent_raw_screenshots=recent_raw_screenshots,
        recent_annotated_screenshots=recent_annotated_screenshots,
        artifacts=artifacts,
    )


def _artifacts_from_bundle(request: JudgeRequest) -> dict[str, str]:
    bundle = request.evidence_bundle
    artifacts: dict[str, str] = {}
    field_map = {
        "runner_history": bundle.runner_history_path,
        "runner_memory": bundle.runner_memory_path,
        "decision_trace": bundle.decision_trace_path,
        "runtime_logs": bundle.runtime_logs_path,
        "observation_frames": bundle.observation_frames_path,
        "observation_diffs": bundle.observation_diffs_path,
        "observation_tree": bundle.observation_tree_path,
        "raw_screenshots": bundle.raw_screenshots_path,
        "annotated_screenshots": bundle.annotated_screenshots_path,
        "llm_transcript": bundle.llm_transcript_path,
        "artifact_manifest": bundle.artifact_manifest_path,
    }
    for key, value in field_map.items():
        if value is not None:
            artifacts[key] = str(value)
    return artifacts


def _summarize_execution(execution: JudgeExecutionSummary) -> str:
    parts = [f"status={execution.status}"]
    if execution.stop_reason:
        parts.append(f"stop_reason={execution.stop_reason}")
    if execution.error_type:
        parts.append(f"error_type={execution.error_type}")
    if execution.error_message:
        parts.append(f"error_message={execution.error_message}")
    parts.append(f"steps_completed={execution.steps_completed}")
    if execution.last_action_summary:
        parts.append(f"last_action_summary={execution.last_action_summary}")
    if execution.last_target_identity:
        parts.append(f"last_target_identity={execution.last_target_identity}")
    if execution.last_surface_identity:
        parts.append(f"last_surface_identity={execution.last_surface_identity}")
    return "; ".join(parts)


def _build_event_evidence(events: list[JudgeEventRecord]) -> list[JudgeEvidence]:
    evidence: list[JudgeEvidence] = []
    for index, event in enumerate(events):
        payload = event.data
        summary = event.message or event.event_type
        if payload:
            summary = f"{summary} | data={json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
        evidence.append(
            JudgeEvidence(
                evidence_id=f"event-{index}",
                kind=event.event_type,
                source="event",
                summary=summary,
                payload={
                    "type": event.event_type,
                    "timestamp": event.timestamp,
                    "message": event.message,
                    "data": payload,
                },
            )
        )
    return evidence


def _build_trace_evidence(trace_path_value: str | None) -> list[JudgeEvidence]:
    if not trace_path_value:
        return []
    trace_path = Path(trace_path_value)
    if not trace_path.exists():
        return []
    lines = [line.strip() for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    evidence: list[JudgeEvidence] = []
    for index, line in enumerate(lines[-20:]):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"raw": line}
        payload_dict = cast(dict[str, object], payload) if isinstance(payload, dict) else {"raw": str(payload)}
        result_summary = str(payload_dict.get("result_summary", line))
        evidence.append(
            JudgeEvidence(
                evidence_id=f"trace-{index}",
                kind="decision_trace",
                source="artifact",
                summary=str(result_summary),
                payload=payload_dict,
            )
        )
    return evidence


def _build_runner_history_evidence(history_path_value: str | None) -> list[JudgeEvidence]:
    if not history_path_value:
        return []
    history_path = Path(history_path_value)
    if not history_path.exists():
        return []
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list) or not payload:
        return []
    entries = _dict_list(payload)
    if not entries:
        return []
    latest = entries[0]
    latest_action = str(latest.get("action_type", "unknown"))
    latest_outcome = str(latest.get("outcome_summary") or latest.get("summary") or "").strip()
    summary = f"runner_history artifact: latest={latest_action}"
    if latest_outcome:
        summary = f"{summary}; outcome={latest_outcome}"
    latest_step_index = max(
        (
            step_index
            for item in entries
            for step_index in [item.get("step_index")]
            if isinstance(step_index, int)
        ),
        default=-1,
    )
    return [
        JudgeEvidence(
            evidence_id="runner-history",
            kind="runner_history",
            source="artifact",
            summary=summary,
            payload={
                "path": str(history_path),
                "entries": entries,
                "excerpt": entries[:8],
                "step_index": latest_step_index,
            },
        )
    ]


def _build_runner_memory_evidence(memory_path_value: str | None) -> list[JudgeEvidence]:
    if not memory_path_value:
        return []
    memory_path = Path(memory_path_value)
    if not memory_path.exists():
        return []
    try:
        payload = json.loads(memory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    payload_dict = _dict_or_none(payload)
    if payload_dict is None:
        return []
    entries = _dict_list(payload_dict.get("entries"))
    if not entries:
        return []
    keys = ", ".join(str(item.get("key")) for item in entries[:3] if item.get("key"))
    summary = f"runner memory artifact: keys={keys or 'none'}"
    excerpt = [
        {
            "key": item.get("key"),
            "summary": item.get("summary"),
            "updated_step_index": item.get("updated_step_index"),
        }
        for item in entries[:8]
    ]
    return [
        JudgeEvidence(
            evidence_id="runner-memory",
            kind="runner_memory",
            source="artifact",
            summary=summary,
            payload={
                "path": str(memory_path),
                "entries": entries,
                "excerpt": excerpt,
            },
        )
    ]


def _build_runtime_error_log_evidence(runtime_logs_path_value: str | None) -> list[JudgeEvidence]:
    if not runtime_logs_path_value:
        return []
    runtime_logs_dir = Path(runtime_logs_path_value)
    if not runtime_logs_dir.exists() or not runtime_logs_dir.is_dir():
        return []
    step_files = sorted(path for path in runtime_logs_dir.iterdir() if path.name.startswith("step_") and path.suffix == ".json")
    if not step_files:
        return []
    collected_entries: list[dict[str, object]] = []
    step_indexes: list[int] = []
    for path in step_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        payload_dict = _dict_or_none(payload)
        if payload_dict is None:
            continue
        entries = _dict_list(payload_dict.get("entries"))
        if not entries:
            continue
        error_entries = [
            item
            for item in entries
            if isinstance(item, dict) and str(item.get("level", "")).strip() == "error"
        ]
        if not error_entries:
            continue
        step_index = payload_dict.get("step_index")
        if isinstance(step_index, int):
            step_indexes.append(step_index)
        collected_entries.extend(error_entries)
    if not collected_entries:
        return []
    excerpt = _trim_runtime_error_log_excerpt(collected_entries)
    if not excerpt:
        return []
    summary = f"runtime error logs observed in {len(step_indexes) or 1} step(s)"
    if step_indexes:
        summary = f"{summary}; latest_step={max(step_indexes)}"
    return [
        JudgeEvidence(
            evidence_id="runtime-error-log",
            kind="runtime_error_log",
            source="artifact",
            summary=summary,
            payload={
                "path": str(runtime_logs_dir),
                "excerpt": excerpt,
                "entries": collected_entries[-8:],
                "step_indexes": sorted(set(step_indexes)),
            },
        )
    ]


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
        evidence.append(
            JudgeEvidence(
                evidence_id=f"{kind}-{path.stem}",
                kind=kind,
                source="artifact",
                summary=summary,
                payload={
                    "path": str(path),
                    "data": payload,
                    "excerpt": excerpt,
                    "step_index": _step_index_from_name(path.stem),
                },
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
    return compact_tree


def _compact_tree_node(
    item: dict[str, object],
    tree_parent_map: dict[str, str | None],
) -> dict[str, object]:
    payload = compact_tree_node(item, tree_parent_map=tree_parent_map)
    assert payload is not None
    return payload


def _sparse_state_fields(item: dict[str, object]) -> dict[str, object]:
    return sparse_state_fields(item)


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
    raw_nodes = frame_payload.get("tree_nodes")
    raw_node_items = _dict_list(raw_nodes)
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
        parent_occurrence = 0
        parent_node_id = node_id_by_signature_occurrence.get((parent_signature, parent_occurrence))
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


def _build_screenshot_refs(
    *,
    kind: Literal["raw", "annotated"],
    directory_value: str | None,
    frame_evidence: list[JudgeEvidence],
    diff_evidence: list[JudgeEvidence],
    runner_history_evidence: list[JudgeEvidence],
) -> list[JudgeScreenshotRef]:
    if not directory_value:
        return []
    directory = Path(directory_value)
    if not directory.exists() or not directory.is_dir():
        return []
    files = sorted(path for path in directory.iterdir() if path.suffix.lower() == ".png")
    if not files:
        return []
    selected_files = files[-SCREENSHOT_WINDOW:]
    frame_meta_by_step: dict[int, tuple[str, str | None]] = {}
    for item in frame_evidence:
        step_index = item.payload.get("step_index")
        excerpt = _dict_or_none(item.payload.get("excerpt"))
        package = excerpt.get("package") if excerpt is not None else None
        if isinstance(step_index, int):
            frame_meta_by_step[step_index] = (item.evidence_id, str(package) if package else None)
    diff_id_by_step = {
        step_index: item.evidence_id
        for item in diff_evidence
        for step_index in [item.payload.get("step_index")]
        if isinstance(step_index, int)
    }
    history_by_step = _runner_history_by_step(runner_history_evidence)
    refs: list[JudgeScreenshotRef] = []
    for path in selected_files:
        step_index = _step_index_from_name(path.stem)
        frame_meta = frame_meta_by_step.get(step_index, (None, None))
        history_entry = history_by_step.get(step_index - 1) or history_by_step.get(step_index)
        screenshot_kind: Literal["raw", "annotated"] = "raw" if kind == "raw" else "annotated"
        refs.append(
            JudgeScreenshotRef(
                screenshot_id=f"{kind}-{path.stem}",
                step_index=step_index,
                kind=screenshot_kind,
                path=str(path),
                package=frame_meta[1],
                action_summary=_string_or_none(history_entry.get("summary")) if history_entry else None,
                observation_summary=_string_or_none(history_entry.get("outcome_summary")) if history_entry else None,
                tree_evidence_id=frame_meta[0],
                diff_evidence_id=diff_id_by_step.get(step_index),
            )
        )
    return refs


def _build_screenshot_evidence(screenshots: list[JudgeScreenshotRef]) -> list[JudgeEvidence]:
    evidence: list[JudgeEvidence] = []
    for screenshot in screenshots:
        summary_parts = [f"{screenshot.kind} screenshot step={screenshot.step_index}"]
        if screenshot.action_summary:
            summary_parts.append(f"action={screenshot.action_summary}")
        if screenshot.observation_summary:
            summary_parts.append(f"observation={screenshot.observation_summary}")
        evidence.append(
            JudgeEvidence(
                evidence_id=f"screenshot-{screenshot.screenshot_id}",
                kind="screenshot",
                source="artifact",
                summary="; ".join(summary_parts),
                payload={
                    "path": screenshot.path,
                    "step_index": screenshot.step_index,
                    "excerpt": screenshot.model_dump(mode="json"),
                },
            )
        )
    return evidence


def _runner_memory_summary(runner_memory_evidence: list[JudgeEvidence]) -> list[dict[str, object]]:
    for evidence in runner_memory_evidence:
        excerpt = _dict_list(evidence.payload.get("excerpt"))
        if excerpt:
            return excerpt
    return []


def _runner_history_by_step(runner_history_evidence: list[JudgeEvidence]) -> dict[int, dict[str, object]]:
    for evidence in runner_history_evidence:
        entries = _dict_list(evidence.payload.get("entries"))
        if not entries:
            continue
        return {
            step_index: entry
            for entry in entries
            for step_index in [entry.get("step_index")]
            if isinstance(step_index, int)
        }
    return {}


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _select_primary_evidence(
    evidence: list[JudgeEvidence],
    focus_terms: list[str],
) -> list[JudgeEvidence]:
    scored = sorted(
        evidence,
        key=lambda item: (_evidence_priority_score(item, focus_terms), _evidence_step_index(item)),
        reverse=True,
    )
    primary: list[JudgeEvidence] = []
    seen_ids: set[str] = set()
    for item in scored:
        if item.kind == "runner_memory":
            continue
        if item.evidence_id in seen_ids:
            continue
        primary.append(item)
        seen_ids.add(item.evidence_id)
        if len(primary) >= MAX_PRIMARY_EVIDENCE:
            break
    return primary


def _evidence_priority_score(item: JudgeEvidence, focus_terms: list[str]) -> int:
    kind_priority = {
        "screen_diff": 500,
        "screenshot": 450,
        "runner_history": 150,
        "screen_frame": 400,
        "runtime_error_log": 220,
        "decision_trace": 180,
    }.get(item.kind, 100)
    summary_hits = count_focus_matches(item.summary, focus_terms) * 80
    excerpt_hits = count_focus_matches(_excerpt_text(item.payload.get("excerpt")), focus_terms) * 60
    positive_signal = 0
    excerpt = item.payload.get("excerpt")
    if item.kind == "screen_diff" and isinstance(excerpt, dict):
        for key in ("appeared_labels", "updated_labels", "linked_visual_changes"):
            value = cast(object, excerpt.get(key))
            if isinstance(value, list) and value:
                positive_signal += 25
    if item.kind == "screen_frame" and isinstance(excerpt, dict):
        compact_tree = cast(object, excerpt.get("compact_tree"))
        if isinstance(compact_tree, dict) and isinstance(compact_tree.get("nodes"), list) and compact_tree.get("nodes"):
            positive_signal += 40
    if item.kind == "screenshot" and isinstance(excerpt, dict):
        if excerpt.get("observation_summary"):
            positive_signal += 30
    if item.kind == "runner_history":
        entries = item.payload.get("excerpt")
        if isinstance(entries, list) and entries:
            positive_signal += 35
    return kind_priority + summary_hits + excerpt_hits + positive_signal + min(_evidence_step_index(item), 99)


def _excerpt_text(excerpt: object) -> str:
    if excerpt is None:
        return ""
    if isinstance(excerpt, str):
        return excerpt
    return json.dumps(excerpt, ensure_ascii=False, sort_keys=True)


def _evidence_step_index(item: JudgeEvidence) -> int:
    step_index = item.payload.get("step_index")
    if isinstance(step_index, int):
        return step_index
    return _step_index_from_name(item.evidence_id)


def _step_index_from_name(name: str) -> int:
    match = re.search(r"(\d+)$", name)
    if match is None:
        return -1
    return int(match.group(1))


def _trim_runtime_error_log_excerpt(entries: list[dict[str, object]]) -> str:
    lines: list[str] = []
    total = 0
    for entry in reversed(entries):
        message = str(entry.get("message", "")).strip()
        if not message:
            continue
        step_index = entry.get("step_index")
        source = str(entry.get("source", "")).strip() or "runtime"
        surface_identity = str(entry.get("surface_identity", "")).strip()
        prefix = f"step={step_index if isinstance(step_index, int) else 'unknown'} source={source}"
        if surface_identity:
            prefix = f"{prefix} surface={surface_identity}"
        line = f"- {prefix} message={message}"
        projected = total + len(line) + 1
        if lines and projected > RUNTIME_ERROR_LOG_CHAR_BUDGET:
            break
        if not lines and len(line) > RUNTIME_ERROR_LOG_CHAR_BUDGET:
            return line[:RUNTIME_ERROR_LOG_CHAR_BUDGET]
        lines.append(line)
        total = projected
    return "\n".join(reversed(lines))
