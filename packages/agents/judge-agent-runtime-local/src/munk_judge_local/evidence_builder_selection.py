from __future__ import annotations

import json

from munk.judging.models import (
    JudgeEvidence,
    is_runner_history_evidence,
    is_runner_issue_evidence,
    is_runner_memory_evidence,
    is_screen_diff_evidence,
    is_screen_frame_evidence,
    is_screenshot_evidence,
)

from .evidence_builder_support import _step_index_from_name
from .focus_terms import count_focus_matches

MAX_PRIMARY_EVIDENCE = 6


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
        if item.kind == "runner_memory" or item.kind == "runner_issue":
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
    excerpt = _evidence_excerpt(item)
    excerpt_hits = count_focus_matches(_excerpt_text(excerpt), focus_terms) * 60
    positive_signal = 0
    if is_screen_diff_evidence(item):
        if item.payload.appeared_labels or item.payload.updated_labels or item.payload.linked_visual_changes:
            positive_signal += 25
    if is_screen_frame_evidence(item):
        if item.payload.compact_tree.nodes:
            positive_signal += 40
    if is_screenshot_evidence(item) and item.payload.observation_summary:
        positive_signal += 30
    if is_runner_history_evidence(item) and item.payload.excerpt:
        positive_signal += 35
    return kind_priority + summary_hits + excerpt_hits + positive_signal + min(_evidence_step_index(item), 99)


def _excerpt_text(excerpt: object) -> str:
    if excerpt is None:
        return ""
    if isinstance(excerpt, str):
        return excerpt
    return json.dumps(excerpt, ensure_ascii=False, sort_keys=True)


def _evidence_excerpt(item: JudgeEvidence) -> object:
    if is_screen_diff_evidence(item):
        return {
            "summary": item.payload.summary,
            "appeared_labels": list(item.payload.appeared_labels),
            "updated_labels": list(item.payload.updated_labels),
            "disappeared_labels": list(item.payload.disappeared_labels),
            "linked_visual_changes": list(item.payload.linked_visual_changes),
        }
    if is_screen_frame_evidence(item):
        return {
            "package": item.payload.package,
            "tree_available": item.payload.tree_available,
            "tree_summary": item.payload.tree_summary,
            "compact_tree": item.payload.compact_tree.model_dump(mode="json"),
            "focus_hits": [entry.model_dump(mode="json") for entry in item.payload.focus_hits],
        }
    if is_runner_history_evidence(item):
        return [entry.model_dump(mode="json") for entry in item.payload.excerpt]
    if is_runner_memory_evidence(item):
        return [entry.model_dump(mode="json") for entry in item.payload.excerpt]
    if is_runner_issue_evidence(item):
        return item.payload.issue.model_dump(mode="json")
    if is_screenshot_evidence(item):
        return item.payload.model_dump(mode="json")
    if item.kind == "runtime_error_log":
        return item.payload.excerpt
    return item.payload.model_dump(mode="json")


def _evidence_step_index(item: JudgeEvidence) -> int:
    if is_screen_frame_evidence(item) or is_screen_diff_evidence(item) or is_screenshot_evidence(item):
        return item.payload.step_index
    if is_runner_history_evidence(item) and isinstance(item.payload.latest_step_index, int):
        return item.payload.latest_step_index
    return _step_index_from_name(item.evidence_id)
