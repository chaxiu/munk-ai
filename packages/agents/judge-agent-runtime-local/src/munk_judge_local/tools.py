from __future__ import annotations

import json
from typing import Any

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext
from pydantic_ai.messages import ToolReturn

from munk.judging.models import is_screen_diff_evidence, is_screen_frame_evidence

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
    def read_step_screenshot(
        ctx: PydanticRunContext[JudgeRunDeps],
        step_index: int | None = None,
        annotated: bool = True,
    ) -> str | ToolReturn:
        """Read the compressed screenshot image for a single step when visual confirmation is still needed."""
        return _read_step_screenshot(ctx.deps, step_index=step_index, annotated=annotated)


def _read_step_screen(deps: JudgeRunDeps, *, step_index: int) -> str:
    if not _consume_budget(deps, "read_step_screen"):
        return "tool budget exhausted; make the best judgment from the current evidence"
    evidence = find_screen_evidence_by_step(deps, step_index)
    if evidence is None or not is_screen_frame_evidence(evidence):
        return f"unknown step index: {step_index}"
    detail: dict[str, Any] = {
        "summary": evidence.summary,
        "compact_tree": evidence.payload.compact_tree.model_dump(mode="json"),
        "focus_hits": [entry.model_dump(mode="json") for entry in evidence.payload.focus_hits[:6]],
    }
    return json.dumps(detail, ensure_ascii=False, sort_keys=True)


def _read_step_transition(deps: JudgeRunDeps, *, step_index: int) -> str:
    if not _consume_budget(deps, "read_step_transition"):
        return "tool budget exhausted; make the best judgment from the current evidence"
    evidence = find_transition_evidence_by_step(deps, step_index)
    if evidence is None or not is_screen_diff_evidence(evidence):
        return f"unknown step index: {step_index}"
    detail: dict[str, Any] = {
        "summary": evidence.summary,
        "excerpt": {
            "summary": evidence.payload.summary,
            "appeared_labels": list(evidence.payload.appeared_labels),
            "updated_labels": list(evidence.payload.updated_labels),
            "disappeared_labels": list(evidence.payload.disappeared_labels),
            "linked_visual_changes": list(evidence.payload.linked_visual_changes),
        },
        "changes": {
            "appeared_nodes": [item.model_dump(mode="json") for item in evidence.payload.appeared_nodes[:4]],
            "updated_nodes": [item.model_dump(mode="json") for item in evidence.payload.updated_nodes[:4]],
            "disappeared_nodes": [item.model_dump(mode="json") for item in evidence.payload.disappeared_nodes[:4]],
            "linked_visual_changes": list(evidence.payload.linked_visual_changes[:4]),
        },
    }
    return json.dumps(detail, ensure_ascii=False, sort_keys=True)


def _read_step_screenshot(
    deps: JudgeRunDeps,
    *,
    step_index: int | None,
    annotated: bool,
) -> str | ToolReturn:
    if not _consume_budget(deps, "read_step_screenshot"):
        return "tool budget exhausted; make the best judgment from the current evidence"
    refs = deps.annotated_screenshot_refs_by_step() if annotated else deps.raw_screenshot_refs_by_step()
    if step_index is None:
        step_index = max(refs.keys()) if refs else None
    if step_index is None:
        return "no screenshots available"
    screenshot_ref = refs.get(step_index)
    if screenshot_ref is None:
        return f"unknown step index: {step_index}"
    kind = "annotated" if annotated else "raw"
    image = load_screenshot_binary_image(
        screenshot_ref.path,
        identifier=f"judge_tool_step_{step_index:04d}_{kind}",
        vl_max_side=deps.vl_max_side,
    )
    if image is None:
        return f"{kind} screenshot unavailable for step index: {step_index}"
    return ToolReturn(
        return_value=f"{kind} screenshot loaded for step {step_index}",
        content=[
            (
                f"{kind.title()} screenshot for step={step_index}; "
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
def _consume_budget(deps: JudgeRunDeps, tool_name: str) -> bool:
    if deps.tool_budget <= 0:
        return False
    deps.tool_budget -= 1
    deps.tool_calls.append(tool_name)
    return True
