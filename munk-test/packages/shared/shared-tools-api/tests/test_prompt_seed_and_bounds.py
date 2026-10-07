from __future__ import annotations

import json

from munk.shared_tools.case_run_evidence import (
    build_attempt_summary_payload,
    build_decision_trace_tail_payload,
    build_event_history_tail_payload,
    build_retry_handoffs_payload,
    normalize_history_entries,
)
from munk.shared_tools.prompt_seed import (
    PROMPT_SEED_SOFT_CHAR_LIMIT,
    build_post_run_prompt_seed,
    maybe_degrade_prompt_seed,
)


def test_normalize_history_entries_accepts_entries_object() -> None:
    assert normalize_history_entries({"entries": [{"type": "a"}, {"type": "b"}]}) == [
        {"type": "a"},
        {"type": "b"},
    ]


def test_build_post_run_prompt_seed_is_compact() -> None:
    seed = build_post_run_prompt_seed(
        {
            "attempts": [
                {
                    "attempt_index": 0,
                    "verdict": "failed",
                    "execution": {"status": "failed", "error_type": "TimeoutError"},
                    "runner_history": [{"step_index": 0, "summary": "huge " * 200}],
                }
            ],
            "history": [{"event_type": f"event-{index}", "payload": "x" * 200} for index in range(30)],
            "decision_trace": [{"step": index, "arguments": {"raw": "y" * 500}} for index in range(40)],
            "judge_result": {
                "verdict": "failed",
                "summary": "failed",
                "reason": "timeout",
                "needs_optimization": True,
                "optimization_fields": ["interaction_hints"],
                "extra_noise": "should-not-appear",
            },
            "artifact_manifest": {"items": [{"artifact_id": "attempts"}]},
        }
    )

    assert "attempts" not in seed
    assert "history" not in seed
    assert "decision_trace" not in seed
    assert "artifact_manifest" not in seed
    assert seed["judge_result"]["verdict"] == "failed"
    assert "extra_noise" not in seed["judge_result"]
    assert seed["attempts_overview"][0]["error_type"] == "TimeoutError"
    assert len(seed["history_tail"]) == 8
    assert len(seed["decision_trace_tail"]) == 20
    assert seed["evidence_index"]["attempts"]["count"] == 1


def test_maybe_degrade_prompt_seed_drops_tails_when_over_limit() -> None:
    seed = {
        "attempts_overview": [{"attempt_index": 0}],
        "history_tail": [{"event": "x" * 1000} for _ in range(50)],
        "decision_trace_tail": [{"step": "y" * 1000} for _ in range(50)],
        "evidence_index": {
            "history": {"count": 50, "approx_chars": 50_000},
            "decision_trace": {"count": 50, "approx_chars": 50_000},
        },
        "read_tools_hint": "use tools",
    }
    # Force degrade by using a tiny soft limit.
    degraded, was_degraded = maybe_degrade_prompt_seed(seed, soft_char_limit=200)
    assert was_degraded is True
    assert "history_tail" not in degraded
    assert "decision_trace_tail" not in degraded
    assert degraded["degraded"] is True
    assert degraded["history_count"] == 50


def test_build_attempt_summary_payload_is_compact() -> None:
    payload = json.loads(
        build_attempt_summary_payload(
            [
                {
                    "attempt_index": 0,
                    "verdict": "failed",
                    "retry_reason": "timeout",
                    "execution": {
                        "status": "failed",
                        "error_type": "TimeoutError",
                        "error_message": "boom",
                        "steps_completed": 3,
                    },
                    "runner_history": [
                        {"step_index": 0, "summary": "open", "outcome_summary": "ok"},
                        {"step_index": 1, "summary": "submit", "outcome_summary": "fail"},
                    ],
                    "artifacts": {"runner_history": "/tmp/history.json", "decision_trace": "/tmp/trace.jsonl"},
                    "huge_blob": "z" * 10_000,
                }
            ],
            attempt_index=0,
        )
    )
    assert payload["attempt_index"] == 0
    assert payload["execution"]["error_type"] == "TimeoutError"
    assert "huge_blob" not in payload
    assert payload["artifact_ids"] == ["decision_trace", "runner_history"]
    assert len(payload["step_summaries"]) == 2


def test_build_retry_handoffs_and_trace_payloads_truncate() -> None:
    handoffs = json.loads(
        build_retry_handoffs_payload([{"reason": "r" * 1000, "detail": {"nested": "n" * 1000}} for _ in range(20)])
    )
    assert handoffs["truncated"] is True
    assert handoffs["total_count"] == 20
    assert len(handoffs["retry_handoffs"]) == 12

    history = json.loads(
        build_event_history_tail_payload(
            {"entries": [{"type": "event", "arguments": {"raw": "a" * 2000}} for _ in range(5)]},
            last_n=3,
        )
    )
    assert history["returned_count"] == 3
    assert history["total_count"] == 5

    trace = json.loads(
        build_decision_trace_tail_payload(
            [{"step": 1, "arguments": {"raw": "b" * 2000}, "decision": "retry"}],
            last_n=1,
        )
    )
    assert trace["returned_count"] == 1
    assert "truncated" in str(trace["entries"][0]["arguments"])


def test_prompt_seed_soft_limit_constant_is_positive() -> None:
    assert PROMPT_SEED_SOFT_CHAR_LIMIT > 0
