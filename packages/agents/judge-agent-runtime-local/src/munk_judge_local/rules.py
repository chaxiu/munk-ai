from __future__ import annotations

from dataclasses import dataclass

from munk.judging.models import JudgeEventRecord, JudgeExecutionSummary, JudgeVerdict

from .focus_terms import extract_focus_terms
from .models import JudgeEvidencePack


@dataclass(frozen=True)
class RuleGateDecision:
    verdict: JudgeVerdict
    summary: str
    reason: str
    failure_hypothesis: str | None = None
    supporting_evidence_ids: list[str] | None = None


def apply_hard_rule_gate(
    execution: JudgeExecutionSummary,
    events: list[JudgeEventRecord],
    evidence_pack: JudgeEvidencePack,
) -> RuleGateDecision | None:
    if execution.status == "failed":
        return RuleGateDecision(
            verdict="failed",
            summary="case execution failed",
            reason=execution.error_message or execution.stop_reason or "execution failed",
            failure_hypothesis="runner execution failed before case completion",
            supporting_evidence_ids=["execution"],
        )
    if any(event.event_type == "run_failed" for event in events):
        return RuleGateDecision(
            verdict="failed",
            summary="run failed event observed",
            reason="run failed event present in execution trace",
            failure_hypothesis="execution produced an explicit run failure signal",
            supporting_evidence_ids=["execution"],
        )
    if any(event.event_type == "action_execution_failed" for event in events):
        return RuleGateDecision(
            verdict="failed",
            summary="action execution failure observed",
            reason="action execution failed event present in execution trace",
            failure_hypothesis="runner action failed before reliable completion",
            supporting_evidence_ids=["execution"],
        )
    if execution.status == "incomplete" and _looks_like_missing_required_affordance(evidence_pack):
        return RuleGateDecision(
            verdict="failed",
            summary="required feature or entry was not found before execution stopped",
            reason="runner explored relevant screens but did not find the required actionable affordance",
            failure_hypothesis="the expected feature may be missing, hidden, or unreachable in the current app state",
            supporting_evidence_ids=_supporting_evidence_ids(evidence_pack),
        )
    return None


def _looks_like_missing_required_affordance(evidence_pack: JudgeEvidencePack) -> bool:
    terminal_actions = _recent_terminal_actions(evidence_pack)
    if len(terminal_actions) < 4:
        return False
    search_actions = [
        action
        for action in terminal_actions
        if any(token in action.lower() for token in ("look", "find", "search", "option", "menu", "entry"))
    ]
    navigation_actions = [
        action
        for action in terminal_actions
        if any(token in action.lower() for token in ("click", "scroll", "back", "redetect"))
    ]
    if len(search_actions) < 2 or len(navigation_actions) < 3:
        return False
    element_list_text = " ".join(_recent_element_lists(evidence_pack)).lower()
    goal_text = " ".join([evidence_pack.runner_goal, *evidence_pack.expected]).lower()
    return _mentions_goal_keyword(search_actions, goal_text) and not _goal_keyword_present_in_list(
        goal_text, element_list_text
    )


def _recent_terminal_actions(evidence_pack: JudgeEvidencePack) -> list[str]:
    history_actions = _recent_terminal_actions_from_history(evidence_pack)
    if history_actions:
        return history_actions
    return _recent_terminal_actions_from_trace(evidence_pack)


def _recent_terminal_actions_from_history(evidence_pack: JudgeEvidencePack) -> list[str]:
    for item in evidence_pack.evidence:
        if item.kind != "runner_history":
            continue
        excerpt = item.payload.get("excerpt")
        if not isinstance(excerpt, list):
            continue
        actions: list[str] = []
        for raw_entry in excerpt:
            if not isinstance(raw_entry, dict):
                continue
            entry = raw_entry
            action_type = str(entry.get("action_type", "")).strip()
            summary = str(entry.get("summary", "")).strip()
            detail = str(entry.get("detail", "")).strip()
            parts = [part for part in (action_type, summary, detail) if part]
            if parts:
                actions.append(" ".join(parts))
        if actions:
            return actions
    return []


def _recent_element_lists(evidence_pack: JudgeEvidencePack) -> list[str]:
    frame_lists = _recent_element_lists_from_frame(evidence_pack)
    if frame_lists:
        return frame_lists
    return _recent_element_lists_from_trace(evidence_pack)


def _recent_element_lists_from_frame(evidence_pack: JudgeEvidencePack) -> list[str]:
    for item in reversed(evidence_pack.evidence):
        if item.kind != "screen_frame":
            continue
        excerpt = item.payload.get("excerpt")
        if not isinstance(excerpt, dict):
            continue
        compact_tree = excerpt.get("compact_tree")
        if not isinstance(compact_tree, dict):
            continue
        nodes = compact_tree.get("nodes")
        if not isinstance(nodes, list):
            continue
        labels: list[str] = []
        for raw_node in nodes:
            if not isinstance(raw_node, dict):
                continue
            node = raw_node
            label = node.get("txt") or node.get("cd") or node.get("rid")
            if label:
                labels.append(str(label))
        if labels:
            return labels
    return []


def _recent_terminal_actions_from_trace(evidence_pack: JudgeEvidencePack) -> list[str]:
    actions: list[str] = []
    for item in evidence_pack.evidence:
        if item.kind != "decision_trace":
            continue
        tool_name = str(item.payload.get("tool_name", "")).strip()
        if tool_name not in {"click", "scroll", "back", "home", "wait", "redetect", "stop"}:
            continue
        summary = item.summary.strip()
        if summary:
            actions.append(summary)
    return actions[-5:]


def _recent_element_lists_from_trace(evidence_pack: JudgeEvidencePack) -> list[str]:
    entries: list[str] = []
    for item in evidence_pack.evidence:
        if item.kind != "decision_trace":
            continue
        tool_name = str(item.payload.get("tool_name", "")).strip()
        if tool_name != "list_clickable_elements":
            continue
        summary = item.summary.strip()
        if summary:
            entries.append(summary)
    return entries[-3:]


def _mentions_goal_keyword(actions: list[str], goal_text: str) -> bool:
    keywords = extract_focus_terms(goal_text)
    if not keywords:
        return False
    action_text = " ".join(actions).lower()
    return any(keyword in action_text for keyword in keywords)


def _goal_keyword_present_in_list(goal_text: str, element_list_text: str) -> bool:
    keywords = extract_focus_terms(goal_text)
    if not keywords:
        return False
    return any(keyword in element_list_text for keyword in keywords)


def _supporting_evidence_ids(evidence_pack: JudgeEvidencePack) -> list[str]:
    candidates = ["execution"]
    primary_screen_diff = next(
        (item.evidence_id for item in evidence_pack.primary_evidence if item.kind == "screen_diff"),
        None,
    )
    primary_runner_history = next(
        (item.evidence_id for item in evidence_pack.primary_evidence if item.kind == "runner_history"),
        None,
    )
    primary_screen_frame = next(
        (item.evidence_id for item in evidence_pack.primary_evidence if item.kind == "screen_frame"),
        None,
    )
    latest_trace = next(
        (
            item.evidence_id
            for item in reversed(evidence_pack.evidence)
            if item.kind == "decision_trace"
        ),
        None,
    )
    latest_event = next(
        (item.evidence_id for item in reversed(evidence_pack.evidence) if item.evidence_id.startswith("event-")),
        None,
    )
    for evidence_id in (
        primary_screen_diff,
        primary_runner_history,
        primary_screen_frame,
        latest_trace,
        latest_event,
    ):
        if evidence_id:
            candidates.append(evidence_id)
    seen: set[str] = set()
    ordered: list[str] = []
    for evidence_id in candidates:
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        ordered.append(evidence_id)
    return ordered[:5]
