from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

DEFAULT_HISTORY_TAIL = 20
DEFAULT_DECISION_TRACE_TAIL = 50
MAX_RETRY_HANDOFFS = 12
MAX_HANDOFF_CHARS = 400
MAX_HISTORY_ENTRY_CHARS = 800
MAX_TRACE_ENTRY_CHARS = 1_200
MAX_ATTEMPT_SUMMARY_CHARS = 8_000
MAX_TOOL_PAYLOAD_CHARS = 24_000
MAX_ATTEMPT_ERROR_CHARS = 500
MAX_ATTEMPT_STEP_SUMMARIES = 8


class CaseRunEvidenceToolProvider(Protocol):
    def consume_tool_budget(self, tool_name: str) -> bool: ...

    def tool_budget_exhausted_message(self) -> str: ...

    def read_judge_result(self) -> str: ...

    def read_attempts_overview(self) -> str: ...

    def read_attempt_summary(self, attempt_index: int) -> str: ...

    def read_retry_handoffs(self) -> str: ...

    def read_event_history_tail(self, last_n: int) -> str: ...

    def read_decision_trace_tail(self, last_n: int) -> str: ...

    def read_artifact_manifest(self) -> str: ...


def register_case_run_evidence_tools(
    agent: Agent[Any, Any],
    *,
    provider_getter: Callable[[Any], CaseRunEvidenceToolProvider],
) -> None:
    @agent.tool
    def read_judge_result(ctx: PydanticRunContext[Any]) -> str:
        """Read the structured judge result for the current case."""
        provider = provider_getter(ctx.deps)
        if not provider.consume_tool_budget("read_judge_result"):
            return provider.tool_budget_exhausted_message()
        return provider.read_judge_result()

    @agent.tool
    def read_attempts_overview(ctx: PydanticRunContext[Any]) -> str:
        """Read a compact overview of all attempts before opening one attempt in detail."""
        provider = provider_getter(ctx.deps)
        if not provider.consume_tool_budget("read_attempts_overview"):
            return provider.tool_budget_exhausted_message()
        return provider.read_attempts_overview()

    @agent.tool
    def read_attempt_summary(ctx: PydanticRunContext[Any], attempt_index: int) -> str:
        """Read one attempt summary by index."""
        provider = provider_getter(ctx.deps)
        if not provider.consume_tool_budget("read_attempt_summary"):
            return provider.tool_budget_exhausted_message()
        return provider.read_attempt_summary(attempt_index)

    @agent.tool
    def read_retry_handoffs(ctx: PydanticRunContext[Any]) -> str:
        """Read retry handoff messages captured for the case."""
        provider = provider_getter(ctx.deps)
        if not provider.consume_tool_budget("read_retry_handoffs"):
            return provider.tool_budget_exhausted_message()
        return provider.read_retry_handoffs()

    @agent.tool
    def read_event_history_tail(ctx: PydanticRunContext[Any], last_n: int = 8) -> str:
        """Read the tail of history events for the case."""
        provider = provider_getter(ctx.deps)
        if not provider.consume_tool_budget("read_event_history_tail"):
            return provider.tool_budget_exhausted_message()
        return provider.read_event_history_tail(last_n)

    @agent.tool
    def read_decision_trace_tail(ctx: PydanticRunContext[Any], last_n: int = 20) -> str:
        """Read the tail of the runner decision trace."""
        provider = provider_getter(ctx.deps)
        if not provider.consume_tool_budget("read_decision_trace_tail"):
            return provider.tool_budget_exhausted_message()
        return provider.read_decision_trace_tail(last_n)

    @agent.tool
    def read_artifact_manifest(ctx: PydanticRunContext[Any]) -> str:
        """Read the artifact manifest and the list of available evidence artifacts."""
        provider = provider_getter(ctx.deps)
        if not provider.consume_tool_budget("read_artifact_manifest"):
            return provider.tool_budget_exhausted_message()
        return provider.read_artifact_manifest()


def build_unavailable_payload(artifact_id: str) -> str:
    return json.dumps(
        {"status": "unavailable", "artifact_id": artifact_id, "reason": "artifact not provided"},
        ensure_ascii=False,
        sort_keys=True,
    )


def normalize_history_entries(history: object) -> list[object]:
    if isinstance(history, list):
        return list(history)
    if isinstance(history, Mapping):
        entries = history.get("entries")
        if isinstance(entries, list):
            return list(entries)
    return []


def build_attempts_overview_items(attempts: object) -> list[dict[str, object]]:
    if not isinstance(attempts, list):
        return []
    overview: list[dict[str, object]] = []
    for item in attempts:
        if not isinstance(item, dict):
            continue
        execution = item.get("execution")
        execution_payload = execution if isinstance(execution, dict) else {}
        overview.append(
            {
                "attempt_index": item.get("attempt_index"),
                "verdict": item.get("verdict"),
                "retry_reason": item.get("retry_reason"),
                "judge_reason": item.get("judge_reason"),
                "status": execution_payload.get("status"),
                "stop_reason": execution_payload.get("stop_reason"),
                "error_type": execution_payload.get("error_type"),
            }
        )
    return overview


def build_attempts_overview_payload(attempts: object) -> str:
    if not isinstance(attempts, list):
        return build_unavailable_payload("attempts")
    return _dumps_bounded({"attempts": build_attempts_overview_items(attempts)})


def build_attempt_summary_payload(attempts: object, attempt_index: int) -> str:
    if not isinstance(attempts, list):
        return build_unavailable_payload("attempts")
    for item in attempts:
        if isinstance(item, dict) and item.get("attempt_index") == attempt_index:
            return _dumps_bounded(compact_attempt_summary(item), max_chars=MAX_ATTEMPT_SUMMARY_CHARS)
    return json.dumps(
        {
            "status": "unavailable",
            "artifact_id": "attempts",
            "reason": f"unknown attempt index: {attempt_index}",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def compact_attempt_summary(attempt: Mapping[str, object]) -> dict[str, object]:
    execution = attempt.get("execution")
    execution_payload = execution if isinstance(execution, Mapping) else {}
    compact: dict[str, object] = {
        "attempt_index": attempt.get("attempt_index"),
        "verdict": attempt.get("verdict"),
        "retry_reason": attempt.get("retry_reason"),
        "judge_reason": attempt.get("judge_reason"),
        "execution": {
            "status": execution_payload.get("status"),
            "stop_reason": execution_payload.get("stop_reason"),
            "error_type": execution_payload.get("error_type"),
            "error_message": _truncate_text(execution_payload.get("error_message"), MAX_ATTEMPT_ERROR_CHARS),
            "steps_completed": execution_payload.get("steps_completed"),
            "last_action_summary": _truncate_text(
                execution_payload.get("last_action_summary"),
                MAX_ATTEMPT_ERROR_CHARS,
            ),
        },
    }
    step_summaries = _extract_attempt_step_summaries(attempt)
    if step_summaries:
        compact["step_summaries"] = step_summaries
    artifacts = attempt.get("artifacts")
    if isinstance(artifacts, Mapping):
        compact["artifact_ids"] = sorted(str(key) for key in artifacts.keys())
    return compact


def build_retry_handoffs_payload(handoffs: object) -> str:
    if not isinstance(handoffs, list):
        return build_unavailable_payload("retry_handoffs")
    compact_handoffs = [_compact_handoff(item) for item in handoffs[:MAX_RETRY_HANDOFFS]]
    payload: dict[str, object] = {
        "retry_handoffs": compact_handoffs,
        "total_count": len(handoffs),
        "truncated": len(handoffs) > MAX_RETRY_HANDOFFS,
    }
    return _dumps_bounded(payload)


def build_event_history_tail_payload(
    history: object,
    *,
    last_n: int,
    fallback: object | None = None,
) -> str:
    payload = normalize_history_entries(history)
    if not payload and fallback is not None:
        payload = normalize_history_entries(fallback)
    if not payload:
        return build_unavailable_payload("history")
    bounded_last_n = max(1, min(last_n, DEFAULT_HISTORY_TAIL))
    entries = compact_history_entries(payload[-bounded_last_n:])
    return _dumps_bounded(
        {
            "entries": entries,
            "total_count": len(payload),
            "returned_count": len(entries),
        }
    )


def build_decision_trace_tail_payload(entries: object, *, last_n: int) -> str:
    if not isinstance(entries, list):
        return build_unavailable_payload("decision_trace")
    bounded_last_n = max(1, min(last_n, DEFAULT_DECISION_TRACE_TAIL))
    compact_entries = compact_decision_trace_entries(entries[-bounded_last_n:])
    return _dumps_bounded(
        {
            "entries": compact_entries,
            "total_count": len(entries),
            "returned_count": len(compact_entries),
        }
    )


def build_artifact_manifest_payload(
    manifest: object,
    *,
    available_artifacts: list[str],
) -> str:
    payload: dict[str, object] = {"available_artifacts": available_artifacts}
    if isinstance(manifest, dict):
        payload["manifest"] = manifest
    return _dumps_bounded(payload)


def compact_history_entries(entries: Sequence[object]) -> list[object]:
    compact: list[object] = []
    for item in entries:
        if isinstance(item, Mapping):
            compact.append(_compact_mapping(item, max_chars=MAX_HISTORY_ENTRY_CHARS))
        else:
            compact.append(_truncate_text(item, MAX_HISTORY_ENTRY_CHARS))
    return compact


def compact_decision_trace_entries(entries: Sequence[object]) -> list[object]:
    compact: list[object] = []
    for item in entries:
        if isinstance(item, Mapping):
            compact.append(_compact_trace_entry(item))
        else:
            compact.append(_truncate_text(item, MAX_TRACE_ENTRY_CHARS))
    return compact


def _extract_attempt_step_summaries(attempt: Mapping[str, object]) -> list[dict[str, object]]:
    runner_history = attempt.get("runner_history")
    if not isinstance(runner_history, list):
        return []
    summaries: list[dict[str, object]] = []
    for item in runner_history[-MAX_ATTEMPT_STEP_SUMMARIES:]:
        if not isinstance(item, Mapping):
            continue
        summaries.append(
            {
                "step_index": item.get("step_index"),
                "action_type": item.get("action_type"),
                "summary": _truncate_text(item.get("summary"), 240),
                "outcome_summary": _truncate_text(item.get("outcome_summary"), 240),
            }
        )
    return summaries


def _compact_handoff(item: object) -> object:
    if isinstance(item, Mapping):
        return _compact_mapping(item, max_chars=MAX_HANDOFF_CHARS)
    return _truncate_text(item, MAX_HANDOFF_CHARS)


def _compact_trace_entry(item: Mapping[str, object]) -> dict[str, object]:
    compact: dict[str, object] = {}
    for key, value in item.items():
        key_text = str(key)
        if key_text in {"arguments", "raw_line", "raw", "payload", "tool_arguments"}:
            compact[key_text] = _truncate_text(value, 240)
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            compact[key_text] = _truncate_text(value, 240) if isinstance(value, str) else value
            continue
        compact[key_text] = _truncate_text(value, 240)
    return compact


def _compact_mapping(item: Mapping[str, object], *, max_chars: int) -> dict[str, object]:
    compact: dict[str, object] = {}
    for key, value in item.items():
        key_text = str(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            compact[key_text] = _truncate_text(value, max_chars) if isinstance(value, str) else value
            continue
        compact[key_text] = _truncate_text(value, max_chars)
    serialized = json.dumps(compact, ensure_ascii=False, sort_keys=True, default=str)
    if len(serialized) <= max_chars:
        return compact
    return {"truncated": True, "preview": serialized[: max_chars - 32]}


def _truncate_text(value: object, limit: int) -> object:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(text) <= limit:
        return text if isinstance(value, str) else text
    return text[: max(0, limit - 16)] + "...(truncated)"


def _dumps_bounded(payload: object, *, max_chars: int = MAX_TOOL_PAYLOAD_CHARS) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    if len(text) <= max_chars:
        return text
    return json.dumps(
        {
            "truncated": True,
            "max_chars": max_chars,
            "approx_chars": len(text),
            "preview": text[: max(0, max_chars - 128)],
            "hint": "Payload truncated. Request a smaller last_n or a more specific attempt_index.",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
