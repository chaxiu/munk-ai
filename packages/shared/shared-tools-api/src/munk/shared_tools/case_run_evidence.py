from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext


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


def build_attempts_overview_payload(attempts: object) -> str:
    if not isinstance(attempts, list):
        return build_unavailable_payload("attempts")
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
    return json.dumps({"attempts": overview}, ensure_ascii=False, sort_keys=True)


def build_attempt_summary_payload(attempts: object, attempt_index: int) -> str:
    if not isinstance(attempts, list):
        return build_unavailable_payload("attempts")
    for item in attempts:
        if isinstance(item, dict) and item.get("attempt_index") == attempt_index:
            return json.dumps(item, ensure_ascii=False, sort_keys=True)
    return json.dumps(
        {
            "status": "unavailable",
            "artifact_id": "attempts",
            "reason": f"unknown attempt index: {attempt_index}",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def build_retry_handoffs_payload(handoffs: object) -> str:
    if not isinstance(handoffs, list):
        return build_unavailable_payload("retry_handoffs")
    return json.dumps({"retry_handoffs": handoffs}, ensure_ascii=False, sort_keys=True)


def build_event_history_tail_payload(
    history: object,
    *,
    last_n: int,
    fallback: object | None = None,
) -> str:
    payload = history if isinstance(history, list) else fallback
    if not isinstance(payload, list):
        return build_unavailable_payload("history")
    bounded_last_n = max(1, min(last_n, 20))
    return json.dumps({"entries": payload[-bounded_last_n:]}, ensure_ascii=False, sort_keys=True)


def build_decision_trace_tail_payload(entries: object, *, last_n: int) -> str:
    if not isinstance(entries, list):
        return build_unavailable_payload("decision_trace")
    bounded_last_n = max(1, min(last_n, 50))
    return json.dumps({"entries": entries[-bounded_last_n:]}, ensure_ascii=False, sort_keys=True)


def build_artifact_manifest_payload(
    manifest: object,
    *,
    available_artifacts: list[str],
) -> str:
    payload: dict[str, object] = {"available_artifacts": available_artifacts}
    if isinstance(manifest, dict):
        payload["manifest"] = manifest
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
