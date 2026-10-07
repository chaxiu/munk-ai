from __future__ import annotations

import json
from typing import Any

from .case_run_evidence import (
    DEFAULT_DECISION_TRACE_TAIL,
    DEFAULT_HISTORY_TAIL,
    build_attempts_overview_items,
    compact_decision_trace_entries,
    compact_history_entries,
    normalize_history_entries,
)

PROMPT_SEED_SOFT_CHAR_LIMIT = 180_000
DEFAULT_SEED_HISTORY_TAIL = 8
DEFAULT_SEED_DECISION_TRACE_TAIL = 20


def estimate_prompt_chars(payload: object) -> int:
    if isinstance(payload, str):
        return len(payload)
    return len(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))


def estimate_prompt_tokens(prompt_chars: int) -> int:
    return max(0, prompt_chars // 4)


def build_prompt_size_diagnostics(prompt_text: str, *, degraded: bool = False) -> dict[str, object]:
    prompt_chars = len(prompt_text)
    return {
        "prompt_chars": prompt_chars,
        "prompt_tokens_estimate": estimate_prompt_tokens(prompt_chars),
        "soft_char_limit": PROMPT_SEED_SOFT_CHAR_LIMIT,
        "degraded": degraded,
        "over_soft_limit": prompt_chars > PROMPT_SEED_SOFT_CHAR_LIMIT,
    }


def compact_judge_result_summary(judge_result: object) -> dict[str, object] | None:
    if not isinstance(judge_result, dict):
        return None
    fields = (
        "verdict",
        "summary",
        "reason",
        "failure_hypothesis",
        "needs_optimization",
        "optimization_fields",
        "optimization_reason",
        "confidence",
    )
    compact: dict[str, object] = {}
    for field in fields:
        if field in judge_result:
            compact[field] = judge_result[field]
    return compact or None


def build_evidence_index(structured_evidence: dict[str, object]) -> dict[str, object]:
    index: dict[str, object] = {}
    for key, value in structured_evidence.items():
        if isinstance(value, list):
            index[key] = {
                "count": len(value),
                "approx_chars": estimate_prompt_chars(value),
            }
        elif isinstance(value, dict):
            index[key] = {
                "count": 1,
                "approx_chars": estimate_prompt_chars(value),
            }
        elif value is None:
            index[key] = {"count": 0, "approx_chars": 0}
        else:
            index[key] = {
                "count": 1,
                "approx_chars": estimate_prompt_chars(value),
            }
    return index


def build_post_run_prompt_seed(
    structured_evidence: dict[str, object] | None,
    *,
    include_tails: bool = True,
    history_tail: int = DEFAULT_SEED_HISTORY_TAIL,
    decision_trace_tail: int = DEFAULT_SEED_DECISION_TRACE_TAIL,
) -> dict[str, object]:
    evidence = dict(structured_evidence or {})
    history_entries = normalize_history_entries(evidence.get("history"))
    decision_trace = evidence.get("decision_trace")
    decision_entries = decision_trace if isinstance(decision_trace, list) else []
    retry_handoffs = evidence.get("retry_handoffs")
    handoff_entries = retry_handoffs if isinstance(retry_handoffs, list) else []

    seed: dict[str, object] = {
        "judge_result": compact_judge_result_summary(evidence.get("judge_result")),
        "attempts_overview": build_attempts_overview_items(evidence.get("attempts")),
        "evidence_index": build_evidence_index(evidence),
        "read_tools_hint": (
            "Use read_attempts_overview / read_attempt_summary / read_event_history_tail / "
            "read_decision_trace_tail / read_retry_handoffs / read_artifact_manifest when more detail is required."
        ),
    }

    if include_tails:
        bounded_history_n = max(1, min(history_tail, DEFAULT_HISTORY_TAIL))
        bounded_trace_n = max(1, min(decision_trace_tail, DEFAULT_DECISION_TRACE_TAIL))
        seed["history_tail"] = compact_history_entries(history_entries[-bounded_history_n:])
        seed["decision_trace_tail"] = compact_decision_trace_entries(decision_entries[-bounded_trace_n:])
        seed["retry_handoffs_count"] = len(handoff_entries)
    else:
        seed["history_count"] = len(history_entries)
        seed["decision_trace_count"] = len(decision_entries)
        seed["retry_handoffs_count"] = len(handoff_entries)

    return seed


def maybe_degrade_prompt_seed(seed: dict[str, Any], *, soft_char_limit: int = PROMPT_SEED_SOFT_CHAR_LIMIT) -> tuple[dict[str, Any], bool]:
    if estimate_prompt_chars(seed) <= soft_char_limit:
        return seed, False
    degraded = dict(seed)
    degraded.pop("history_tail", None)
    degraded.pop("decision_trace_tail", None)
    evidence_index = degraded.get("evidence_index")
    if isinstance(evidence_index, dict):
        degraded["history_count"] = _index_count(evidence_index, "history")
        degraded["decision_trace_count"] = _index_count(evidence_index, "decision_trace")
    degraded["degraded"] = True
    degraded["read_tools_hint"] = (
        "Seed was degraded due to size. Prefer overview tools first, then narrow tails "
        "(read_event_history_tail / read_decision_trace_tail / read_attempt_summary)."
    )
    return degraded, True


def _index_count(evidence_index: dict[str, object], key: str) -> int:
    entry = evidence_index.get(key)
    if isinstance(entry, dict):
        count = entry.get("count")
        if isinstance(count, int):
            return count
    return 0
