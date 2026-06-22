from __future__ import annotations

import json
from typing import Literal

from munk.agent_base.platform_profile import get_runner_profile
from munk.agent_base.web_platform_context import (
    format_web_dom_summary,
    format_web_focused_element,
    format_web_page_meta,
)
from munk.shared_tools import register_knowledge_tools
from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext
from pydantic_ai.messages import ToolReturn

from munk_runner_local.brain.pydantic_runner_models import (
    ListClickableElementsToolArgs,
    ReadMemoryToolArgs,
    ReportIssueToolArgs,
    RunnerIssueRecord,
    RunnerStepDeps,
    SaveMemoryToolArgs,
)
from munk_runner_local.brain.pydantic_runner_output_models import RunnerActionOutput
from munk_runner_local.brain.pydantic_runner_tool_runtime import (
    load_runner_issues,
    read_step_screenshot as runtime_read_step_screenshot,
    record_issue_result,
    record_read_tool,
    save_memory_result,
)
from munk_runner_local.brain.pydantic_runner_tool_support import (
    build_clickable_elements_text,
    build_target_detail_payload,
    memory_payload_matches,
    resolve_target_part_limit,
)


def register_runner_tools(
    agent: Agent[RunnerStepDeps, RunnerActionOutput], *, platform: str | None = None
) -> None:
    register_common_runner_tools(agent)
    register_knowledge_tools(
        agent,
        provider_getter=lambda deps: deps.knowledge_tools,
        recorder=lambda deps, tool_name, arguments, payload: record_read_tool(deps, tool_name, arguments, payload),
        include_submit_candidate=False,
    )
    register_platform_runner_tools(agent, platform=platform)


def register_common_runner_tools(agent: Agent[RunnerStepDeps, RunnerActionOutput]) -> None:
    @agent.tool
    def list_clickable_elements(
        ctx: PydanticRunContext[RunnerStepDeps],
        max: int | None = None,
        source: Literal["vision", "tree", "all"] = "all",
    ) -> str:
        """Read the numbered clickable elements again when the initial prompt context is insufficient."""
        args = ListClickableElementsToolArgs(max=max, source=source)
        part_limit = resolve_target_part_limit(ctx.deps, override=args.max, remember=bool(args.max is not None))
        payload = build_clickable_elements_text(ctx.deps.screen, part_limit, source=args.source)
        arguments: dict[str, object] = {"source": args.source}
        if args.max is not None:
            arguments["max"] = part_limit
        return record_read_tool(ctx.deps, "list_clickable_elements", arguments, payload)

    @agent.tool
    def inspect_element(ctx: PydanticRunContext[RunnerStepDeps], target_id: int, max: int | None = None) -> str:
        """Read details for one numbered clickable element."""
        part_limit, detail = build_target_detail_payload(
            ctx.deps,
            target_id=target_id,
            override=max,
            remember=bool(max is not None),
        )
        arguments: dict[str, object] = {"target_id": target_id}
        if max is not None:
            arguments["max"] = part_limit
        return record_read_tool(ctx.deps, "inspect_element", arguments, detail)

    @agent.tool
    def read_last_action_outcome(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read the structured outcome from the previous runner step."""
        observation = ctx.deps.screen.last_action_observation
        payload = observation.summary if observation is not None else "none"
        return record_read_tool(ctx.deps, "read_last_action_outcome", {}, payload)

    @agent.tool
    def read_step_screenshot(
        ctx: PydanticRunContext[RunnerStepDeps],
        step_index: int | None = None,
        annotated: bool = True,
    ) -> str | ToolReturn:
        """Read the compressed saved screenshot for a runner step; annotated screenshots align target ids with prompt text."""
        return runtime_read_step_screenshot(ctx.deps, step_index=step_index, annotated=annotated)

    @agent.tool
    def save_memory(
        ctx: PydanticRunContext[RunnerStepDeps],
        key: str,
        value: str,
        summary: str,
    ) -> str:
        """Save a reusable fact string for later runner steps. Keep value concise and directly reusable."""
        args = SaveMemoryToolArgs(
            key=key,
            value=value,
            summary=summary,
        )
        existing = ctx.deps.memory_store.read_one(args.key.strip())
        if existing is not None and memory_payload_matches(
            existing.value, args.value, existing.summary, args.summary
        ):
            return record_read_tool(
                ctx.deps,
                "save_memory",
                {"key": existing.key, "duplicate": True},
                f"no change: memory key={existing.key} already holds this exact value "
                f"(last updated at step {existing.updated_step_index}).",
            )

        arguments, result = save_memory_result(
            ctx.deps,
            key=args.key,
            value=args.value,
            summary=args.summary,
        )
        return record_read_tool(ctx.deps, "save_memory", arguments, result)

    @agent.tool
    def read_memory(ctx: PydanticRunContext[RunnerStepDeps], key: str | None = None) -> str:
        """Read saved runner memory summaries or one saved entry. Call without key to list known entries, or pass key to get the stored value."""
        args = ReadMemoryToolArgs(key=key)
        if args.key is None:
            payload = {"entries": ctx.deps.memory_store.summary_items(limit=20)}
            return record_read_tool(
                ctx.deps,
                "read_memory",
                {},
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )

        entry = ctx.deps.memory_store.read_one(args.key)
        if entry is None:
            return record_read_tool(ctx.deps, "read_memory", {"key": args.key}, f"unknown memory key: {args.key}")
        payload: dict[str, object] = {
            "key": entry.key,
            "summary": entry.summary,
            "value": entry.value,
            "updated_step_index": entry.updated_step_index,
            "timestamp": entry.timestamp,
        }
        return record_read_tool(
            ctx.deps,
            "read_memory",
            {"key": args.key},
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        )

    @agent.tool
    def report_issue(
        ctx: PydanticRunContext[RunnerStepDeps],
        severity: Literal["warning", "error"],
        summary: str,
    ) -> str:
        """Report one non-case issue for the current step. Each step may report at most one issue."""
        args = ReportIssueToolArgs(severity=severity, summary=summary)
        issues = load_runner_issues(ctx.deps)
        current_step = ctx.deps.step_index
        for item in issues:
            if item.step_index == current_step:
                return record_read_tool(
                    ctx.deps,
                    "report_issue",
                    {"severity": args.severity, "duplicate": True},
                    (
                        "issue already reported for this step: "
                        f"severity={item.severity}; summary={item.summary}"
                    ),
                )

        arguments, result = record_issue_result(
            ctx.deps,
            RunnerIssueRecord(
                step_index=current_step,
                severity=args.severity,
                summary=args.summary,
            ),
            issues,
        )
        return record_read_tool(ctx.deps, "report_issue", arguments, result)


def register_platform_runner_tools(
    agent: Agent[RunnerStepDeps, RunnerActionOutput], *, platform: str | None = None
) -> None:
    profile = get_runner_profile(platform)
    enabled_read_tools = set(profile.enabled_read_tools)
    if "read_page_meta" in enabled_read_tools:
        _register_read_page_meta(agent)
    if "read_dom_summary" in enabled_read_tools:
        _register_read_dom_summary(agent)
    if "read_focused_element" in enabled_read_tools:
        _register_read_focused_element(agent)


def _register_read_page_meta(agent: Agent[RunnerStepDeps, RunnerActionOutput]) -> None:
    @agent.tool
    def read_page_meta(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read Web page title, URL, and origin when the initial prompt context is insufficient."""
        payload = format_web_page_meta(ctx.deps.screen.platform_context)
        return record_read_tool(ctx.deps, "read_page_meta", {}, payload)


def _register_read_dom_summary(agent: Agent[RunnerStepDeps, RunnerActionOutput]) -> None:
    @agent.tool
    def read_dom_summary(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read a concise DOM summary for the current Web page."""
        payload = format_web_dom_summary(ctx.deps.screen.platform_context)
        return record_read_tool(ctx.deps, "read_dom_summary", {}, payload)


def _register_read_focused_element(agent: Agent[RunnerStepDeps, RunnerActionOutput]) -> None:
    @agent.tool
    def read_focused_element(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read the currently focused Web element, if any."""
        payload = format_web_focused_element(ctx.deps.screen.platform_context)
        return record_read_tool(ctx.deps, "read_focused_element", {}, payload)
