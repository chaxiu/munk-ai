from __future__ import annotations

import json
from typing import Any, cast

from munk.agent_base.action import Action
from munk.agent_base.base import ScreenState
from munk.agent_base.platform_profile import get_runner_profile
from munk.agent_base.web_platform_context import (
    format_web_dom_summary,
    format_web_focused_element,
    format_web_page_meta,
)
from munk.shared_tools import register_knowledge_tools
from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

from munk.services.events import (
    RunnerContractMissEvent,
    RunnerDecisionCompletedEvent,
    RunnerToolCalledEvent,
)
from munk_runner_local.brain.history import build_memory_history_entry
from munk_runner_local.brain.pydantic_runner_models import (
    ElementLocatorArgs,
    ListClickableElementsToolArgs,
    ReadMemoryToolArgs,
    RunnerStepDeps,
    RunnerToolTraceEntry,
    SaveMemoryToolArgs,
)
from munk_runner_local.brain.pydantic_runner_output_models import (
    ClickActionSubmission,
    InputActionSubmission,
    LocatorWaitActionSubmission,
    LongPressActionSubmission,
    RunnerActionOutput,
    ScrollActionSubmission,
    ScrollUntilVisibleActionSubmission,
    SimpleActionSubmission,
    SwipeActionSubmission,
    WaitActionSubmission,
)
from munk_runner_local.brain.pydantic_runner_prompt import build_runner_seed_context
from munk_runner_local.brain.runner_view import (
    build_target_detail_text,
    build_targets_list_text,
    build_targets_text,
    resolve_action_target,
)

TERMINAL_TOOL_NAMES = (
    "click",
    "long_press",
    "clear_and_input",
    "input_text",
    "scroll",
    "swipe",
    "dismiss_soft_keyboard",
    "wait_for_element",
    "wait_until_gone",
    "scroll_until_visible",
    "back",
    "home",
    "wait",
    "redetect",
    "stop",
)
DEFAULT_TARGET_PART_LIMIT = 40
MAX_TARGET_PART_LIMIT = 200


def build_screen_summary_text(screen: ScreenState) -> str:
    tree_summary = screen.screen_frame.tree_summary if screen.screen_frame is not None else "none"
    return "\n".join(
        [
            f"target_identity={screen.entry_identity or 'unknown'}",
            f"surface_identity={screen.surface_identity or 'unknown'}",
            f"screen_size={screen.screen_size[0]}x{screen.screen_size[1]}",
            f"elements={len(screen.elements)}",
            f"tree={tree_summary}",
        ]
    )


def build_clickable_elements_text(
    screen: ScreenState,
    max_elements: int,
    *,
    source: str = "all",
) -> str:
    return build_targets_list_text(screen, max_elements=max_elements, source=cast(Any, source))


def build_targets_seed_text(
    screen: ScreenState,
    max_elements: int,
    prompt_max_elements: int,
) -> str:
    return build_targets_text(
        screen,
        max_elements=max_elements,
        prompt_max_elements=prompt_max_elements,
    )


def register_runner_tools(
    agent: Agent[RunnerStepDeps, RunnerActionOutput], *, platform: str | None = None
) -> None:
    register_common_runner_tools(agent)
    register_knowledge_tools(
        agent,
        provider_getter=lambda deps: deps.knowledge_tools,
        recorder=lambda deps, tool_name, arguments, payload: _record_read_tool(deps, tool_name, arguments, payload),
        include_submit_candidate=False,
    )
    register_platform_runner_tools(agent, platform=platform)


def register_common_runner_tools(agent: Agent[RunnerStepDeps, RunnerActionOutput]) -> None:
    @agent.tool
    def read_case_objective(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read the current case objective and execution hint."""
        return _record_read_tool(ctx.deps, "read_case_objective", {}, ctx.deps.case_brief)

    @agent.tool
    def read_screen_summary(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read a concise summary of the current screen when the initial prompt context is insufficient."""
        summary = build_screen_summary_text(ctx.deps.screen)
        return _record_read_tool(ctx.deps, "read_screen_summary", {}, summary)

    @agent.tool
    def list_clickable_elements(
        ctx: PydanticRunContext[RunnerStepDeps],
        max: int | None = None,
        source: str = "all",
    ) -> str:
        """Read the numbered clickable elements again when the initial prompt context is insufficient."""
        args = ListClickableElementsToolArgs(max=max, source=source)
        part_limit = _resolve_target_part_limit(ctx.deps, override=args.max, remember=bool(args.max is not None))
        payload = build_clickable_elements_text(ctx.deps.screen, part_limit, source=args.source)
        arguments: dict[str, object] = {"source": args.source}
        if args.max is not None:
            arguments["max"] = part_limit
        return _record_read_tool(ctx.deps, "list_clickable_elements", arguments, payload)

    @agent.tool
    def inspect_element(ctx: PydanticRunContext[RunnerStepDeps], target_id: int, max: int | None = None) -> str:
        """Read details for one numbered clickable element."""
        part_limit = _resolve_target_part_limit(ctx.deps, override=max, remember=bool(max is not None))
        detail = build_target_detail_text(
            ctx.deps.screen,
            target_id=target_id,
            max_elements=part_limit,
        )
        arguments: dict[str, object] = {"target_id": target_id}
        if max is not None:
            arguments["max"] = part_limit
        return _record_read_tool(ctx.deps, "inspect_element", arguments, detail)

    @agent.tool
    def read_last_action_outcome(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read the structured outcome from the previous runner step."""
        observation = ctx.deps.screen.last_action_observation
        payload = observation.summary if observation is not None else "none"
        return _record_read_tool(ctx.deps, "read_last_action_outcome", {}, payload)

    @agent.tool
    def save_memory(
        ctx: PydanticRunContext[RunnerStepDeps],
        key: str,
        value: object,
        summary: str,
    ) -> str:
        """Save a reusable fact for later runner steps. Pass arrays/objects as structured JSON values, not quoted strings."""
        args = SaveMemoryToolArgs(key=key, value=cast(Any, value), summary=summary)
        entry, created = ctx.deps.memory_store.save(
            key=args.key,
            value=args.value,
            summary=args.summary,
            step_index=ctx.deps.step_index,
        )
        ctx.deps.history_entries.append(
            build_memory_history_entry(
                operation="save" if created else "update",
                key=entry.key,
                summary=entry.summary,
            )
        )
        _write_runner_memory_artifact(ctx.deps)
        result = f"{'saved' if created else 'updated'} memory key={entry.key}"
        return _record_read_tool(
            ctx.deps,
            "save_memory",
            {"key": entry.key, "summary": entry.summary},
            result,
        )

    @agent.tool
    def read_memory(ctx: PydanticRunContext[RunnerStepDeps], key: str | None = None) -> str:
        """Read saved runner memory summaries or one saved entry when later steps need the fact again."""
        args = ReadMemoryToolArgs(key=key)
        if args.key is None:
            payload = {"entries": ctx.deps.memory_store.summary_items(limit=20)}
            return _record_read_tool(
                ctx.deps,
                "read_memory",
                {},
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
        entry = ctx.deps.memory_store.read_one(args.key)
        if entry is None:
            return _record_read_tool(ctx.deps, "read_memory", {"key": args.key}, f"unknown memory key: {args.key}")
        payload: dict[str, object] = {
            "key": entry.key,
            "summary": entry.summary,
            "value": entry.value,
            "updated_step_index": entry.updated_step_index,
            "timestamp": entry.timestamp,
        }
        return _record_read_tool(
            ctx.deps,
            "read_memory",
            {"key": args.key},
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        )


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
        return _record_read_tool(ctx.deps, "read_page_meta", {}, payload)


def _register_read_dom_summary(agent: Agent[RunnerStepDeps, RunnerActionOutput]) -> None:
    @agent.tool
    def read_dom_summary(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read a concise DOM summary for the current Web page."""
        payload = format_web_dom_summary(ctx.deps.screen.platform_context)
        return _record_read_tool(ctx.deps, "read_dom_summary", {}, payload)


def _register_read_focused_element(agent: Agent[RunnerStepDeps, RunnerActionOutput]) -> None:
    @agent.tool
    def read_focused_element(ctx: PydanticRunContext[RunnerStepDeps]) -> str:
        """Read the currently focused Web element, if any."""
        payload = format_web_focused_element(ctx.deps.screen.platform_context)
        return _record_read_tool(ctx.deps, "read_focused_element", {}, payload)


def materialize_runner_action(
    deps: RunnerStepDeps,
    submission: RunnerActionOutput,
) -> Action:
    if isinstance(submission, ClickActionSubmission):
        target = _resolve_target(deps, submission.target_id)
        action = Action.click(target.box, summary=submission.summary)
        arguments = _target_arguments(
            {
                "target_id": submission.target_id,
                "summary": submission.summary,
            },
            target,
        )
        return _record_materialized_action(deps, "click", arguments, action)

    if isinstance(submission, LongPressActionSubmission):
        target = _resolve_target(deps, submission.target_id)
        action = Action.long_press(
            target.box,
            duration=submission.duration_sec,
            summary=submission.summary,
        )
        arguments = _target_arguments(
            {
                "target_id": submission.target_id,
                "summary": submission.summary,
                "duration_sec": submission.duration_sec,
            },
            target,
        )
        return _record_materialized_action(deps, "long_press", arguments, action)

    if isinstance(submission, InputActionSubmission):
        if submission.action_type == "clear_and_input":
            target_id = submission.target_id
            dismiss_keyboard = submission.dismiss_keyboard
            if target_id is None or dismiss_keyboard is None:
                raise ValueError("clear_and_input submission is missing required input fields")
            target = _resolve_target(deps, target_id)
            action = Action.clear_and_input(
                target.box,
                submission.text,
                dismiss_keyboard=dismiss_keyboard,
                summary=submission.summary,
            )
            arguments = _target_arguments(
                {
                    "target_id": target_id,
                    "text": submission.text,
                    "summary": submission.summary,
                    "dismiss_keyboard": dismiss_keyboard,
                },
                target,
            )
            return _record_materialized_action(deps, "clear_and_input", arguments, action)

        dismiss_keyboard = submission.dismiss_keyboard
        if dismiss_keyboard is None:
            raise ValueError("input_text submission is missing dismiss_keyboard")
        action = Action.input_text(
            submission.text,
            summary=submission.summary,
            dismiss_keyboard=dismiss_keyboard,
        )
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        return _record_materialized_action(deps, "input_text", arguments, action)

    if isinstance(submission, ScrollActionSubmission):
        action = Action.scroll(
            direction=submission.direction,
            distance_px=submission.distance_px,
            summary=submission.summary,
        )
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        return _record_materialized_action(deps, "scroll", arguments, action)

    if isinstance(submission, SwipeActionSubmission):
        action = Action.swipe(
            direction=submission.direction,
            distance_px=submission.distance_px,
            summary=submission.summary,
        )
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        return _record_materialized_action(deps, "swipe", arguments, action)

    if isinstance(submission, SimpleActionSubmission):
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        if submission.action_type == "dismiss_soft_keyboard":
            action = Action.dismiss_soft_keyboard(summary=submission.summary)
            return _record_materialized_action(deps, "dismiss_soft_keyboard", arguments, action)
        if submission.action_type == "back":
            action = Action.back(summary=submission.summary)
            return _record_materialized_action(deps, "back", arguments, action)
        if submission.action_type == "home":
            action = Action.home(summary=submission.summary)
            return _record_materialized_action(deps, "home", arguments, action)
        if submission.action_type == "redetect":
            action = Action.redetect(summary=submission.summary)
            return _record_materialized_action(deps, "redetect", arguments, action)
        if submission.action_type == "stop":
            action = Action.stop(summary=submission.summary)
            return _record_materialized_action(deps, "stop", arguments, action)
        raise ValueError(f"unsupported simple runner action output: {submission.action_type}")

    if isinstance(submission, LocatorWaitActionSubmission):
        arguments = _locator_arguments(
            submission.locator,
            timeout_sec=submission.timeout_sec,
            summary=submission.summary,
        )
        if submission.action_type == "wait_for_element":
            action = Action.wait_for_element(
                submission.locator.to_locator(),
                timeout_sec=submission.timeout_sec,
                summary=submission.summary,
            )
            return _record_materialized_action(deps, "wait_for_element", arguments, action)
        action = Action.wait_until_gone(
            submission.locator.to_locator(),
            timeout_sec=submission.timeout_sec,
            summary=submission.summary,
        )
        return _record_materialized_action(deps, "wait_until_gone", arguments, action)

    if isinstance(submission, ScrollUntilVisibleActionSubmission):
        action = Action.scroll_until_visible(
            submission.locator.to_locator(),
            direction=submission.direction,
            max_attempts=submission.max_attempts,
            summary=submission.summary,
        )
        arguments = _locator_arguments(
            submission.locator,
            direction=submission.direction,
            max_attempts=submission.max_attempts,
            summary=submission.summary,
        )
        return _record_materialized_action(deps, "scroll_until_visible", arguments, action)

    if isinstance(submission, WaitActionSubmission):
        action = Action.wait(submission.duration, summary=submission.summary)
        arguments = submission.model_dump(exclude={"action_type"}, exclude_none=True)
        return _record_materialized_action(deps, "wait", arguments, action)

    raise ValueError(f"unsupported runner action output: {type(submission).__name__}")

def _record_read_tool(
    deps: RunnerStepDeps,
    tool_name: str,
    arguments: dict[str, object],
    result: str,
) -> str:
    _remember_attempt_tool(deps, tool_name)
    _append_trace(
        deps,
        RunnerToolTraceEntry(
            step_index=deps.step_index,
            tool_name=tool_name,
            arguments=arguments,
            result_summary=result,
        ),
    )
    _publish_tool_event(deps, tool_name, arguments, result)
    return result


def record_seed_step_context(
    deps: RunnerStepDeps,
    *,
    screen_summary: str,
    targets_text: str,
    seeded_element_count: int,
) -> None:
    if deps.seed_context_recorded:
        return
    payload = build_runner_seed_context(
        screen_summary=screen_summary,
        targets_text=targets_text,
    )
    arguments: dict[str, object] = {
        "max_elements": deps.max_elements,
        "seeded_element_count": seeded_element_count,
        "tree_available": deps.screen.screen_frame.tree_available if deps.screen.screen_frame is not None else False,
    }
    _append_trace(
        deps,
        RunnerToolTraceEntry(
            step_index=deps.step_index,
            tool_name="seed_step_context",
            arguments=arguments,
            result_summary=payload,
        ),
    )
    _publish_tool_event(deps, "seed_step_context", arguments, payload)
    deps.seed_context_recorded = True


def record_contract_miss(
    deps: RunnerStepDeps,
    *,
    output_excerpt: str,
    will_retry: bool,
    seeded_element_count: int,
) -> None:
    arguments: dict[str, object] = {
        "attempt": deps.attempt_index,
        "tool_names": list(deps.attempt_tool_names),
        "will_retry": will_retry,
        "seeded_element_count": seeded_element_count,
    }
    _append_trace(
        deps,
        RunnerToolTraceEntry(
            step_index=deps.step_index,
            tool_name="contract_miss",
            arguments=arguments,
            result_summary=output_excerpt,
        ),
    )
    _publish_contract_miss_event(
        deps,
        output_excerpt=output_excerpt,
        will_retry=will_retry,
        seeded_element_count=seeded_element_count,
    )


def _record_materialized_action(
    deps: RunnerStepDeps,
    tool_name: str,
    arguments: dict[str, object],
    action: Action,
) -> Action:
    _remember_attempt_tool(deps, tool_name)
    result_summary = f"proposed {action.type.value}: {action.summary or action.type.value}"
    _append_trace(
        deps,
        RunnerToolTraceEntry(
            step_index=deps.step_index,
            tool_name=tool_name,
            arguments=arguments,
            result_summary=result_summary,
        ),
    )
    _publish_tool_event(deps, tool_name, arguments, result_summary)
    _publish_decision_event(deps, action)
    return action


def _resolve_target_part_limit(
    deps: RunnerStepDeps,
    *,
    override: int | None = None,
    remember: bool = False,
) -> int:
    if override is None:
        return deps.target_part_limit_override or DEFAULT_TARGET_PART_LIMIT
    part_limit = _validate_target_part_limit(override)
    if remember:
        deps.target_part_limit_override = part_limit
    return part_limit


def _validate_target_part_limit(value: int) -> int:
    if value <= 0:
        raise ValueError("max must be positive")
    return min(value, MAX_TARGET_PART_LIMIT)


def _resolve_target(deps: RunnerStepDeps, target_id: int):  # noqa: ANN202
    return resolve_action_target(
        deps.screen,
        target_id=target_id,
        max_elements=_resolve_target_part_limit(deps),
    )


def _append_trace(deps: RunnerStepDeps, entry: RunnerToolTraceEntry) -> None:
    if deps.trace_path is None:
        return
    deps.trace_path.parent.mkdir(parents=True, exist_ok=True)
    with deps.trace_path.open("a", encoding="utf-8") as f:
        f.write(entry.model_dump_json())
        f.write("\n")


def _write_runner_memory_artifact(deps: RunnerStepDeps) -> None:
    if deps.runner_memory_path is None:
        return
    deps.runner_memory_path.write_text(
        json.dumps(deps.memory_store.artifact_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _locator_arguments(locator: ElementLocatorArgs, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"locator": locator.model_dump(exclude_none=True)}
    payload.update(extra)
    return payload


def _target_arguments(arguments: dict[str, object], target: object) -> dict[str, object]:
    payload = dict(arguments)
    payload["target_part"] = getattr(target, "part", None)
    payload["target_source"] = getattr(target, "source", None)
    payload["target_box"] = getattr(target, "box", None)
    if getattr(target, "linked_tree_node_id", None):
        payload["linked_tree_node_id"] = getattr(target, "linked_tree_node_id")
    if getattr(target, "stable_key", None):
        payload["target_stable_key"] = getattr(target, "stable_key")
    if getattr(target, "resource_id", None):
        payload["target_resource_id"] = getattr(target, "resource_id")
    if getattr(target, "reason", None):
        payload["target_reason"] = getattr(target, "reason")
    return payload


def _remember_attempt_tool(deps: RunnerStepDeps, tool_name: str) -> None:
    deps.attempt_tool_names.append(tool_name)


def _publish_tool_event(
    deps: RunnerStepDeps,
    tool_name: str,
    arguments: dict[str, object],
    result_summary: str,
) -> None:
    if deps.event_sink is None:
        return
    deps.event_sink(
        RunnerToolCalledEvent(
            message=f"runner tool called: {tool_name}",
            data={
                "step": deps.step_index,
                "tool_name": tool_name,
                "arguments": arguments,
                "result_summary": result_summary,
            },
        )
    )


def _publish_contract_miss_event(
    deps: RunnerStepDeps,
    *,
    output_excerpt: str,
    will_retry: bool,
    seeded_element_count: int,
) -> None:
    if deps.event_sink is None:
        return
    deps.event_sink(
        RunnerContractMissEvent(
            message="runner contract miss",
            data={
                "step": deps.step_index,
                "attempt": deps.attempt_index,
                "tool_names": list(deps.attempt_tool_names),
                "result_summary": output_excerpt,
                "will_retry": will_retry,
                "seeded_element_count": seeded_element_count,
            },
        )
    )


def _publish_decision_event(deps: RunnerStepDeps, action: Action) -> None:
    if deps.event_sink is None:
        return
    deps.event_sink(
        RunnerDecisionCompletedEvent(
            message=f"runner decision completed: {action.type.value}",
            data={
                "step": deps.step_index,
                "action": action.type.value,
                "summary": action.summary,
            },
        )
    )
