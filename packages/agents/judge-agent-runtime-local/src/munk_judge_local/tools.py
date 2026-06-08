from __future__ import annotations

import json
from typing import Any, cast

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext
from pydantic_ai.messages import ToolReturn

from .image_payloads import load_screenshot_binary_image
from .step_projection import (
    build_recent_step_summaries,
    build_step_summary,
    find_screen_evidence_by_step,
    find_transition_evidence_by_step,
)
from .tool_models import JudgeRunDeps


def register_judge_tools(agent: Agent[JudgeRunDeps, object]) -> None:
    @agent.tool
    def read_recent_step_summaries(ctx: PydanticRunContext[JudgeRunDeps], last_n: int = 5) -> str:
        """Read bounded summaries for the most recent steps when primary evidence is insufficient."""
        if not _consume_budget(ctx.deps, "read_recent_step_summaries"):
            return "tool budget exhausted; make the best judgment from the current evidence"
        bounded_last_n = max(1, min(last_n, 8))
        summaries = build_recent_step_summaries(ctx.deps, bounded_last_n)
        if not summaries:
            return "no recent step summaries available"
        return json.dumps(summaries, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_step_summary(ctx: PydanticRunContext[JudgeRunDeps], step_index: int) -> str:
        """Read a bounded summary for a single step before requesting detailed screen evidence."""
        if not _consume_budget(ctx.deps, "read_step_summary"):
            return "tool budget exhausted; make the best judgment from the current evidence"
        if step_index < 0:
            return f"unknown step index: {step_index}"
        summary = build_step_summary(ctx.deps, step_index)
        if summary is None:
            return f"unknown step index: {step_index}"
        return json.dumps(summary, ensure_ascii=False, sort_keys=True)

    @agent.tool
    def read_step_screen(ctx: PydanticRunContext[JudgeRunDeps], step_index: int) -> str:
        """Read bounded screen-state details for a single step."""
        return _read_step_screen(ctx.deps, step_index=step_index)

    @agent.tool
    def read_step_transition(ctx: PydanticRunContext[JudgeRunDeps], step_index: int) -> str:
        """Read bounded state-transition details for a single step."""
        return _read_step_transition(ctx.deps, step_index=step_index)

    @agent.tool
    def read_runner_memory(ctx: PydanticRunContext[JudgeRunDeps], key: str | None = None) -> str:
        """Read runner-saved memory summaries or one saved entry when the verdict depends on baseline facts."""
        return _read_runner_memory(ctx.deps, key=key)

    @agent.tool
    def read_step_screen_raw_image(ctx: PydanticRunContext[JudgeRunDeps], step_index: int) -> str | ToolReturn:
        """Read the compressed raw screenshot image for a single step when visual confirmation is still needed."""
        return _read_step_screen_raw_image(ctx.deps, step_index=step_index)


def _read_step_screen(deps: JudgeRunDeps, *, step_index: int) -> str:
    if not _consume_budget(deps, "read_step_screen"):
        return "tool budget exhausted; make the best judgment from the current evidence"
    evidence = find_screen_evidence_by_step(deps, step_index)
    if evidence is None:
        return f"unknown step index: {step_index}"
    excerpt = evidence.payload.get("excerpt")
    detail: dict[str, Any] = {
        "summary": evidence.summary,
        "compact_tree": _trim_compact_tree(excerpt),
        "focus_hits": _trim_focus_hits(excerpt),
    }
    return json.dumps(detail, ensure_ascii=False, sort_keys=True)


def _read_step_transition(deps: JudgeRunDeps, *, step_index: int) -> str:
    if not _consume_budget(deps, "read_step_transition"):
        return "tool budget exhausted; make the best judgment from the current evidence"
    evidence = find_transition_evidence_by_step(deps, step_index)
    if evidence is None:
        return f"unknown step index: {step_index}"
    detail: dict[str, Any] = {
        "summary": evidence.summary,
        "excerpt": evidence.payload.get("excerpt"),
        "changes": _trim_change_lists(evidence.payload.get("data")),
    }
    return json.dumps(detail, ensure_ascii=False, sort_keys=True)


def _read_step_screen_raw_image(deps: JudgeRunDeps, *, step_index: int) -> str | ToolReturn:
    if not _consume_budget(deps, "read_step_screen_raw_image"):
        return "tool budget exhausted; make the best judgment from the current evidence"
    screenshot_ref = deps.raw_screenshot_refs_by_step().get(step_index)
    if screenshot_ref is None:
        return f"unknown step index: {step_index}"
    image = load_screenshot_binary_image(
        screenshot_ref.path,
        identifier=f"judge_tool_step_{step_index:04d}_raw",
        vl_max_side=deps.vl_max_side,
    )
    if image is None:
        return f"raw screenshot unavailable for step index: {step_index}"
    return ToolReturn(
        return_value=f"raw screenshot loaded for step {step_index}",
        content=[
            (
                f"Raw screenshot for step={step_index}; "
                f"action={screenshot_ref.action_summary or 'none'}; "
                f"observation={screenshot_ref.observation_summary or 'none'}"
            ),
            image,
        ],
    )


def _read_runner_memory(deps: JudgeRunDeps, *, key: str | None) -> str:
    if not _consume_budget(deps, "read_runner_memory"):
        return "tool budget exhausted; make the best judgment from the current evidence"
    if key is None:
        return json.dumps(
            {"entries": deps.evidence_pack.runner_memory_summary},
            ensure_ascii=False,
            sort_keys=True,
        )
    entry = deps.runner_memory_by_key().get(key)
    if entry is None:
        return f"unknown runner memory key: {key}"
    detail = {
        "key": entry.get("key"),
        "summary": entry.get("summary"),
        "value": entry.get("value"),
        "updated_step_index": entry.get("updated_step_index"),
        "timestamp": entry.get("timestamp"),
    }
    return json.dumps(detail, ensure_ascii=False, sort_keys=True)


def _trim_change_lists(raw_data: object) -> dict[str, object]:
    if not isinstance(raw_data, dict):
        return {}
    data = cast(dict[str, object], raw_data)
    trimmed: dict[str, object] = {}
    for key in ("appeared_nodes", "updated_nodes", "disappeared_nodes", "linked_visual_changes"):
        value = data.get(key)
        if isinstance(value, list):
            trimmed[key] = value[:4]
    return trimmed


def _trim_compact_tree(excerpt: object) -> dict[str, object]:
    if not isinstance(excerpt, dict):
        return {}
    excerpt_dict = cast(dict[str, object], excerpt)
    compact_tree = excerpt_dict.get("compact_tree")
    if not isinstance(compact_tree, dict):
        return {}
    compact_tree_dict = cast(dict[str, object], compact_tree)
    nodes = compact_tree_dict.get("nodes")
    if not isinstance(nodes, list):
        return dict(compact_tree_dict)
    return {
        **compact_tree_dict,
        "nodes": nodes,
    }


def _trim_focus_hits(excerpt: object) -> list[object]:
    if not isinstance(excerpt, dict):
        return []
    excerpt_dict = cast(dict[str, object], excerpt)
    focus_hits = excerpt_dict.get("focus_hits")
    if not isinstance(focus_hits, list):
        return []
    return cast(list[object], focus_hits[:6])


def _consume_budget(deps: JudgeRunDeps, tool_name: str) -> bool:
    if deps.tool_budget <= 0:
        return False
    deps.tool_budget -= 1
    deps.tool_calls.append(tool_name)
    return True
