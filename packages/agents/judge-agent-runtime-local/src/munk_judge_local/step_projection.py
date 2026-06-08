from __future__ import annotations

from munk.judging.models import JudgeEvidence

from .tool_models import JudgeRunDeps


def build_recent_step_summaries(deps: JudgeRunDeps, last_n: int) -> list[dict[str, object]]:
    step_indexes = sorted(_known_step_indexes(deps))
    if not step_indexes:
        return []
    selected_indexes = step_indexes[-last_n:]
    return [
        summary
        for step_index in selected_indexes
        for summary in [_recent_step_summary(deps, step_index)]
        if summary is not None
    ]


def build_step_summary(deps: JudgeRunDeps, step_index: int) -> dict[str, object] | None:
    summary = _base_step_summary(deps, step_index)
    if summary is None:
        return None
    return {
        **summary,
        "has_screenshot": step_index in deps.recent_screenshot_refs_by_step(),
    }


def find_screen_evidence_by_step(deps: JudgeRunDeps, step_index: int) -> JudgeEvidence | None:
    return deps.screen_evidence_by_step().get(step_index)


def find_transition_evidence_by_step(deps: JudgeRunDeps, step_index: int) -> JudgeEvidence | None:
    return deps.transition_evidence_by_step().get(step_index)


def _recent_step_summary(deps: JudgeRunDeps, step_index: int) -> dict[str, object] | None:
    summary = _base_step_summary(deps, step_index)
    if summary is None:
        return None
    return {
        "step_index": summary["step_index"],
        "action_summary": summary["action_summary"],
        "outcome_summary": summary["outcome_summary"],
        "screen_change_status": summary["screen_change_status"],
        "has_screen": summary["has_screen"],
        "has_transition": summary["has_transition"],
    }


def _base_step_summary(deps: JudgeRunDeps, step_index: int) -> dict[str, object] | None:
    runner_history_by_step = deps.runner_history_by_step()
    screenshot_refs_by_step = deps.recent_screenshot_refs_by_step()
    screen_evidence = find_screen_evidence_by_step(deps, step_index)
    transition_evidence = find_transition_evidence_by_step(deps, step_index)
    history_entry = runner_history_by_step.get(step_index)
    screenshot_ref = screenshot_refs_by_step.get(step_index)
    if (
        history_entry is None
        and screenshot_ref is None
        and screen_evidence is None
        and transition_evidence is None
    ):
        return None
    action_summary = _string_or_none(history_entry.get("summary")) if history_entry else None
    outcome_summary = _string_or_none(history_entry.get("outcome_summary")) if history_entry else None
    if action_summary is None and screenshot_ref is not None:
        action_summary = screenshot_ref.action_summary
    if outcome_summary is None and screenshot_ref is not None:
        outcome_summary = screenshot_ref.observation_summary
    return {
        "step_index": step_index,
        "action_summary": action_summary or "none",
        "outcome_summary": outcome_summary or "none",
        "screen_change_status": _screen_change_status(transition_evidence),
        "has_screen": screen_evidence is not None,
        "has_transition": transition_evidence is not None,
    }


def _known_step_indexes(deps: JudgeRunDeps) -> set[int]:
    indexes: set[int] = set(deps.runner_history_by_step())
    indexes.update(deps.screen_evidence_by_step())
    indexes.update(deps.transition_evidence_by_step())
    indexes.update(deps.recent_screenshot_refs_by_step())
    return indexes


def _screen_change_status(item: JudgeEvidence | None) -> str:
    if item is None:
        return "unknown"
    excerpt = item.payload.get("excerpt")
    summary_parts = [item.summary]
    if isinstance(excerpt, dict):
        excerpt_summary = excerpt.get("summary")
        if isinstance(excerpt_summary, str):
            summary_parts.append(excerpt_summary)
    summary_text = " ".join(summary_parts).lower()
    if "screen_changed=yes" in summary_text:
        return "changed"
    if "screen_changed=no" in summary_text:
        return "unchanged"
    return "unknown"


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
