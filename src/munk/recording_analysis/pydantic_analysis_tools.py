from __future__ import annotations

import json
from typing import Any, cast

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

from .models import (
    FinalizeStageDeps,
    StepStageDeps,
)


def register_step_read_tools(agent: Agent[StepStageDeps, Any]) -> None:
    @agent.tool
    def read_page_identity(ctx: PydanticRunContext[StepStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_page_identity")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        payload = cast(dict[str, Any], deps.step.get("page_identity") or {})
        if not payload:
            return "page identity unavailable"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_action_evidence(ctx: PydanticRunContext[StepStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_action_evidence")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        payload = deps.step.get("action_evidence")
        if not isinstance(payload, dict):
            return "action evidence unavailable"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_outcome_evidence(ctx: PydanticRunContext[StepStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_outcome_evidence")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        payload = deps.step.get("outcome_evidence")
        if not isinstance(payload, dict):
            return "outcome evidence unavailable"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_target_candidates(ctx: PydanticRunContext[StepStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_target_candidates")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        action_evidence = deps.step.get("action_evidence")
        if not isinstance(action_evidence, dict):
            return "target candidates unavailable"
        payload = action_evidence.get("target_candidates")
        if not isinstance(payload, list):
            return "target candidates unavailable"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_timeline_entry(  # noqa: ANN202
        ctx: PydanticRunContext[StepStageDeps],
        seq: int | None = None,
        entry_id: str | None = None,
    ) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_timeline_entry")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        timeline = cast(list[dict[str, Any]], deps.bundle.get("timeline") or [])
        for item in timeline:
            if seq is not None and item.get("seq") == seq:
                return json.dumps(item, ensure_ascii=False, sort_keys=True)
            if entry_id is not None and item.get("entry_id") == entry_id:
                return json.dumps(item, ensure_ascii=False, sort_keys=True)
        return "timeline entry not found"

    @agent.tool
    def read_recording_event(ctx: PydanticRunContext[StepStageDeps], event_id: str) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_recording_event")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        return _read_event(deps.bundle, key="recording_events", event_id_key="event_id", event_id=event_id)

    @agent.tool
    def read_forwarding_event(ctx: PydanticRunContext[StepStageDeps], forwarding_event_id: str) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_forwarding_event")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        return _read_event(
            deps.bundle,
            key="forwarding_events",
            event_id_key="forwarding_event_id",
            event_id=forwarding_event_id,
        )

    @agent.tool
    def read_observation(ctx: PydanticRunContext[StepStageDeps], observation_id: str) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_observation")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        observations = cast(dict[str, Any], deps.bundle.get("observations") or {})
        payload = observations.get(observation_id)
        if payload is None:
            return "observation not found"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_observation_tree(ctx: PydanticRunContext[StepStageDeps], observation_id: str) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_observation_tree")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured step analysis now"
        observations = cast(dict[str, Any], deps.bundle.get("observations") or {})
        payload = observations.get(observation_id)
        if not isinstance(payload, dict):
            return "observation not found"
        tree_text = cast(object | None, payload.get("tree_text"))
        return tree_text if isinstance(tree_text, str) and tree_text else "tree unavailable"


def register_finalize_read_tools(agent: Agent[FinalizeStageDeps, Any]) -> None:
    @agent.tool
    def read_session_summary(ctx: PydanticRunContext[FinalizeStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_session_summary")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured case draft now"
        session = cast(dict[str, Any], deps.bundle.get("session") or {})
        return "\n".join(
            [
                f"recording_id={session.get('recording_id') or 'unknown'}",
                f"app_id={session.get('app_id') or 'unknown'}",
                f"case_id={session.get('case_id') or 'none'}",
                f"entry_identity={session.get('app_target', {}).get('entry_identity') or 'none'}",
            ]
        )

    @agent.tool
    def read_step_summaries(ctx: PydanticRunContext[FinalizeStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_step_summaries")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured case draft now"
        if not deps.step_summaries:
            return "- none"
        return "\n".join(
            (
                f"- action={step.action}; intent={step.intent}; "
                f"state_change={step.state_change}; procedure_step={step.procedure_step}"
            )
            for step in deps.step_summaries
        )

    @agent.tool
    def read_step_warnings(ctx: PydanticRunContext[FinalizeStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_step_warnings")
        if not _consume_budget(deps):
            return "tool budget exhausted; stop reading and return the structured case draft now"
        return "\n".join(f"- {warning}" for warning in deps.warnings) if deps.warnings else "- none"

    @agent.tool
    def read_source_summary(ctx: PydanticRunContext[FinalizeStageDeps]) -> str:
        deps = ctx.deps
        _remember_tool(deps, "read_source_summary")
        if not _consume_budget(deps):
            return "tool budget exhausted"
        summary = deps.bundle.get("source_summary")
        return summary if isinstance(summary, str) and summary.strip() else "none"


def _read_event(bundle: dict[str, Any], *, key: str, event_id_key: str, event_id: str) -> str:
    entries = cast(list[dict[str, Any]], bundle.get(key) or [])
    for item in entries:
        if item.get(event_id_key) == event_id:
            return json.dumps(item, ensure_ascii=False, sort_keys=True)
    return "event not found"


def _consume_budget(deps: StepStageDeps | FinalizeStageDeps) -> bool:
    if deps.tool_budget <= 0:
        deps.last_submission_error = (
            "tool budget exhausted; stop calling read_* tools and return the structured payload immediately"
        )
        return False
    deps.tool_budget -= 1
    return True


def _remember_tool(deps: StepStageDeps | FinalizeStageDeps, tool_name: str) -> None:
    deps.tool_calls.append(tool_name)
    deps.attempt_tool_names.append(tool_name)
