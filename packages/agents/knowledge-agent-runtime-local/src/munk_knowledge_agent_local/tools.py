from __future__ import annotations

import json
from typing import Any

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

from .tool_models import KnowledgeToolDeps


def register_knowledge_agent_tools(agent: Agent[KnowledgeToolDeps, object]) -> None:
    @agent.tool
    def read_judge_result(ctx: PydanticRunContext[KnowledgeToolDeps]) -> str:
        """Read the structured judge result for the current case."""
        if not _consume_budget(ctx.deps, "read_judge_result"):
            return _budget_exhausted()
        payload = ctx.deps.request.evidence_bundle.judge_result.model_dump(mode="json")
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_attempts_overview(ctx: PydanticRunContext[KnowledgeToolDeps]) -> str:
        """Read a compact overview of all attempts before opening one attempt in detail."""
        if not _consume_budget(ctx.deps, "read_attempts_overview"):
            return _budget_exhausted()
        attempts = ctx.deps.read_json_artifact("attempts")
        if not isinstance(attempts, list):
            return _unavailable_payload("attempts")
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

    @agent.tool
    def read_attempt_summary(ctx: PydanticRunContext[KnowledgeToolDeps], attempt_index: int) -> str:
        """Read one attempt summary by index."""
        if not _consume_budget(ctx.deps, "read_attempt_summary"):
            return _budget_exhausted()
        attempts = ctx.deps.read_json_artifact("attempts")
        if not isinstance(attempts, list):
            return _unavailable_payload("attempts")
        for item in attempts:
            if isinstance(item, dict) and item.get("attempt_index") == attempt_index:
                return json.dumps(item, ensure_ascii=False, sort_keys=True)
        return json.dumps(
            {"status": "unavailable", "artifact_id": "attempts", "reason": f"unknown attempt index: {attempt_index}"},
            ensure_ascii=False,
            sort_keys=True,
        )

    @agent.tool
    def read_retry_handoffs(ctx: PydanticRunContext[KnowledgeToolDeps]) -> str:
        """Read retry handoff messages captured for the case."""
        if not _consume_budget(ctx.deps, "read_retry_handoffs"):
            return _budget_exhausted()
        payload = ctx.deps.read_json_artifact("retry_handoffs")
        if not isinstance(payload, list):
            return _unavailable_payload("retry_handoffs")
        return json.dumps({"retry_handoffs": payload}, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_event_history_tail(ctx: PydanticRunContext[KnowledgeToolDeps], last_n: int = 8) -> str:
        """Read the tail of history events for the case."""
        if not _consume_budget(ctx.deps, "read_event_history_tail"):
            return _budget_exhausted()
        payload = ctx.deps.read_json_artifact("history")
        if not isinstance(payload, list):
            payload = ctx.deps.read_json_artifact("runner_history")
        if not isinstance(payload, list):
            return _unavailable_payload("history")
        bounded_last_n = max(1, min(last_n, 20))
        return json.dumps({"entries": payload[-bounded_last_n:]}, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_decision_trace_tail(ctx: PydanticRunContext[KnowledgeToolDeps], last_n: int = 20) -> str:
        """Read the tail of the runner decision trace."""
        if not _consume_budget(ctx.deps, "read_decision_trace_tail"):
            return _budget_exhausted()
        payload = ctx.deps.read_jsonl_artifact("decision_trace")
        if not isinstance(payload, list):
            return _unavailable_payload("decision_trace")
        bounded_last_n = max(1, min(last_n, 50))
        return json.dumps({"entries": payload[-bounded_last_n:]}, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_artifact_manifest(ctx: PydanticRunContext[KnowledgeToolDeps]) -> str:
        """Read the artifact manifest and the list of available evidence artifacts."""
        if not _consume_budget(ctx.deps, "read_artifact_manifest"):
            return _budget_exhausted()
        manifest = ctx.deps.read_json_artifact("artifact_manifest")
        payload: dict[str, Any] = {"available_artifacts": ctx.deps.artifact_ids()}
        if isinstance(manifest, dict):
            payload["manifest"] = manifest
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _consume_budget(deps: KnowledgeToolDeps, tool_name: str) -> bool:
    if deps.tool_budget <= 0:
        return False
    deps.tool_budget -= 1
    deps.tool_calls.append(tool_name)
    return True


def _budget_exhausted() -> str:
    return "tool budget exhausted; make the best knowledge candidate judgment from the current context"


def _unavailable_payload(artifact_id: str) -> str:
    return json.dumps(
        {"status": "unavailable", "artifact_id": artifact_id, "reason": "artifact not provided"},
        ensure_ascii=False,
        sort_keys=True,
    )
