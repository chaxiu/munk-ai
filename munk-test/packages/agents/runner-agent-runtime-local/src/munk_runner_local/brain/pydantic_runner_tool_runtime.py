from __future__ import annotations

import json
from typing import cast

from munk.agent_base.action import Action
from pydantic_ai.messages import ToolReturn

from munk.services.events import (
    RunnerContractMissEvent,
    RunnerDecisionCompletedEvent,
    RunnerToolCalledEvent,
    build_runner_contract_miss_event_payload,
    build_runner_decision_completed_event_payload,
    build_runner_tool_called_event_payload,
)
from munk_runner_local.brain.history import build_memory_history_entry
from munk_runner_local.brain.pydantic_runner_models import (
    RunnerIssueRecord,
    RunnerStepDeps,
    RunnerToolTraceEntry,
)
from munk_runner_local.brain.pydantic_runner_prompt import build_runner_seed_context
from munk_runner_local.image_payloads import load_screenshot_binary_image


def record_read_tool(
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


def read_step_screenshot(
    deps: RunnerStepDeps,
    *,
    step_index: int | None,
    annotated: bool,
) -> str | ToolReturn:
    resolved_step = deps.step_index if step_index is None else step_index
    arguments: dict[str, object] = {"annotated": annotated}
    if step_index is not None:
        arguments["step_index"] = step_index
    if resolved_step is None or resolved_step < 0:
        result = f"unknown step index: {resolved_step}"
        _record_image_tool(deps, "read_step_screenshot", arguments, result)
        return result

    kind = "annotated" if annotated else "raw"
    root = deps.annotated_dir if annotated else deps.raw_dir
    path = root / f"step_{resolved_step:04d}.png"
    if not path.exists():
        result = f"{kind} screenshot unavailable for step index: {resolved_step}"
        _record_image_tool(deps, "read_step_screenshot", arguments, result)
        return result

    image = load_screenshot_binary_image(
        path,
        identifier=f"runner_tool_step_{resolved_step:04d}_{kind}",
        vl_max_side=deps.vl_max_side,
        vl_image_format=deps.vl_image_format,
        vl_fallback_image_format=deps.vl_fallback_image_format,
        vl_webp_quality=deps.vl_webp_quality,
        vl_jpeg_quality=deps.vl_jpeg_quality,
    )
    if image is None:
        result = f"{kind} screenshot unavailable for step index: {resolved_step}"
        _record_image_tool(deps, "read_step_screenshot", arguments, result)
        return result

    result = f"{kind} screenshot loaded for step {resolved_step}"
    _record_image_tool(deps, "read_step_screenshot", arguments, result)
    return ToolReturn(
        return_value=result,
        content=[
            (
                f"{kind.title()} screenshot for step={resolved_step}; "
                "this image was captured for the saved runner step, not as a live screenshot"
            ),
            image,
        ],
    )


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


def record_materialized_action(
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


def write_runner_memory_artifact(deps: RunnerStepDeps) -> None:
    if deps.runner_memory_path is None:
        return
    deps.runner_memory_path.write_text(
        json.dumps(deps.memory_store.artifact_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_runner_issues(deps: RunnerStepDeps) -> list[RunnerIssueRecord]:
    if deps.runner_issues_path is None or not deps.runner_issues_path.exists():
        return []
    try:
        payload = json.loads(deps.runner_issues_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    payload_dict = cast(dict[str, object], payload)
    raw_issues_obj: object = payload_dict.get("issues")
    if not isinstance(raw_issues_obj, list):
        return []
    records: list[RunnerIssueRecord] = []
    for item in cast(list[object], raw_issues_obj):
        if not isinstance(item, dict):
            continue
        records.append(RunnerIssueRecord.model_validate(item))
    return records


def write_runner_issues_artifact(
    deps: RunnerStepDeps,
    issues: list[RunnerIssueRecord],
) -> None:
    if deps.runner_issues_path is None:
        return
    payload = {
        "issues": [item.model_dump(mode="json") for item in issues],
    }
    deps.runner_issues_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def save_memory_result(
    deps: RunnerStepDeps,
    *,
    key: str,
    value: str,
    summary: str,
) -> tuple[dict[str, object], str]:
    entry, created = deps.memory_store.save(
        key=key,
        value=value,
        summary=summary,
        step_index=deps.step_index,
    )
    deps.history_entries.append(
        build_memory_history_entry(
            operation="save" if created else "update",
            key=entry.key,
            summary=entry.summary,
        )
    )
    write_runner_memory_artifact(deps)
    return {"key": entry.key, "summary": entry.summary}, f"{'saved' if created else 'updated'} memory key={entry.key}"


def record_issue_result(
    deps: RunnerStepDeps,
    issue: RunnerIssueRecord,
    issues: list[RunnerIssueRecord],
) -> tuple[dict[str, object], str]:
    issues.append(issue)
    write_runner_issues_artifact(deps, issues)
    return (
        {"severity": issue.severity, "step_index": issue.step_index},
        f"reported issue: severity={issue.severity}; summary={issue.summary}",
    )


def _record_image_tool(
    deps: RunnerStepDeps,
    tool_name: str,
    arguments: dict[str, object],
    result_summary: str,
) -> None:
    _remember_attempt_tool(deps, tool_name)
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


def _append_trace(deps: RunnerStepDeps, entry: RunnerToolTraceEntry) -> None:
    if deps.trace_path is None:
        return
    deps.trace_path.parent.mkdir(parents=True, exist_ok=True)
    with deps.trace_path.open("a", encoding="utf-8") as file:
        file.write(entry.model_dump_json())
        file.write("\n")


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
            data=build_runner_tool_called_event_payload(
                step=deps.step_index,
                tool_name=tool_name,
                arguments=arguments,
                result_summary=result_summary,
            ),
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
            data=build_runner_contract_miss_event_payload(
                step=deps.step_index,
                attempt=deps.attempt_index,
                tool_names=list(deps.attempt_tool_names),
                result_summary=output_excerpt,
                will_retry=will_retry,
                seeded_element_count=seeded_element_count,
            ),
        )
    )


def _publish_decision_event(deps: RunnerStepDeps, action: Action) -> None:
    if deps.event_sink is None:
        return
    deps.event_sink(
        RunnerDecisionCompletedEvent(
            message=f"runner decision completed: {action.type.value}",
            data=build_runner_decision_completed_event_payload(
                step=deps.step_index,
                action=action.type.value,
                summary=action.summary,
            ),
        )
    )
